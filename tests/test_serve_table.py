from pathlib import Path

import pytest

from gpunit import log
from gpunit.serve import table
from gpunit.spec import DIGEST, Port
from tests.fakes import FakeProvider
from tests.helpers import NO_REQUESTS, gpunit

PINNED = "1cfa9a7208912126459214e8b04321603b3df60c"
LARGER_PINNED = "017b9c7af6b5689d5dd426a76e0bc077eb5ca20a"


def _bundled_with(old: str, new: str, tmp_path: Path) -> Path:
    text = table.TABLE.read_text(encoding="utf-8")
    assert old in text
    path = tmp_path / "models.toml"
    path.write_text(text.replace(old, new), encoding="utf-8")
    return path


@pytest.mark.spec("serve:table:loads")
def test_the_bundled_table_holds_both_rows_at_pinned_revisions() -> None:
    loaded = table.load()

    assert sorted(loaded.models) == ["qwen3-4b", "qwen3.8-27b"]
    assert loaded.models["qwen3-4b"].repo == "Qwen/Qwen3-4B"
    assert loaded.models["qwen3-4b"].revision == PINNED
    assert loaded.models["qwen3.8-27b"].repo == "Qwen/Qwen3.8-27B-FP8"
    assert loaded.models["qwen3.8-27b"].revision == LARGER_PINNED
    assert DIGEST.search(loaded.image)
    assert all(row.image == loaded.image for row in loaded.models.values())


@pytest.mark.spec("serve:table:larger-row")
def test_the_larger_row_asks_for_a_48_gb_card_and_its_familys_parser() -> None:
    row = table.load().models["qwen3.8-27b"]

    assert row.vram_gb == 48
    assert row.gpus == (
        "NVIDIA A40",
        "NVIDIA RTX A6000",
        "NVIDIA L40",
        "NVIDIA RTX 6000 Ada Generation",
        "NVIDIA L40S",
    )
    flags = dict(zip(row.args, row.args[1:]))
    assert flags["--tool-call-parser"] == "qwen3_coder"
    assert flags["--reasoning-parser"] == "qwen3"
    assert "--language-model-only" in row.args
    # Its Mamba cache holds 192 sequences on 48 GB: vLLM's default 256 fails to start.
    assert int(flags["--max-num-seqs"]) <= 192


@pytest.mark.spec("serve:table:request-logging-off")
def test_no_row_logs_requests() -> None:
    rows = table.load().models.values()

    on = {"--enable-log-requests", "--enable-log-outputs"}
    assert not any(on & set(row.args) for row in rows)


@pytest.mark.spec("serve:table:revision-pinned")
@pytest.mark.parametrize("revision", ["main", PINNED], ids=["moving", "twin-pinned"])
def test_a_moving_revision_is_refused_naming_the_row(
    revision: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _bundled_with(PINNED, revision, tmp_path)
    if revision == PINNED:
        # The twin: the same table with the 40-hex revision loads.
        assert table.load(path).models["qwen3-4b"].revision == PINNED
        return

    with pytest.raises(log.Refusal):
        table.load(path)
    err = capsys.readouterr().err
    assert "models.qwen3-4b" in err
    assert "'revision'" in err


@pytest.mark.spec("serve:table:revision-pinned")
@pytest.mark.parametrize(
    ("old", "new", "named"),
    [
        ("disk_gb = 40\n", "", "'disk_gb' is required"),
        ("@sha256:", ":", "'image'"),
        ('"16384"', '"16384 tokens"', "a space"),
    ],
    ids=["missing-field", "tagged-image", "spaced-arg"],
)
def test_a_faulty_table_is_refused_naming_the_field(
    old: str, new: str, named: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(log.Refusal):
        table.load(_bundled_with(old, new, tmp_path))
    assert named in capsys.readouterr().err


@pytest.mark.spec("serve:table:row-makes-the-spec")
def test_a_row_becomes_the_sessions_spec() -> None:
    loaded = table.load()
    row = loaded.models["qwen3-4b"]

    spec = row.spec(7200, None, None, "k" * 43, 49152)

    assert spec.project == "serve-qwen3-4b"
    assert spec.image == loaded.image
    assert spec.gpus == row.gpus
    assert spec.vram_gb == 24
    assert spec.disk_gb == 40
    assert spec.ports == (Port(remote=8000, local=49152),)
    assert spec.ceiling_s == 7200
    # A cold host pulls vLLM's image before it maps port 22: the SSH wait covers it.
    assert spec.timeout_s == 1200
    assert spec.env == {
        "SERVE_REPO": "Qwen/Qwen3-4B",
        "SERVE_REVISION": PINNED,
        "SERVE_NAME": "qwen3-4b",
        "SERVE_ARGS": "--max-model-len 16384 --enable-auto-tool-choice "
        "--tool-call-parser hermes --reasoning-parser qwen3",
        "VLLM_API_KEY": "k" * 43,
    }
    assert not any(name.startswith("GPUNIT_") for name in spec.env)


GRANITE = """\
[models."granite-4.0-micro"]
repo = "ibm-granite/granite-4.0-micro"
revision = "56111ae135df9c53a78c99028e7bc24035a9e979"
served = "granite-4.0-micro"
args = ["--max-model-len", "16384", "--enable-auto-tool-choice", "--tool-call-parser",
        "hermes"]
vram_gb = 24
gpus = ["NVIDIA RTX A5000", "NVIDIA GeForce RTX 4090", "NVIDIA L4"]
disk_gb = 40
"""


def _user_file(path: Path, name: str = "granite-4.0-micro") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(GRANITE.replace("granite-4.0-micro", name), encoding="utf-8")
    return path


def _user_rows(given: Path | None = None) -> list[str]:
    return sorted(set(table.rows(given).models) - set(table.load().models))


@pytest.mark.spec("serve:rows:models-flag-first")
@pytest.mark.parametrize("flag", [True, False], ids=["given", "twin-not-given"])
def test_the_given_file_comes_first(
    flag: bool, tmp_path: Path, isolated_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    given = _user_file(tmp_path / "given.toml", "given")
    monkeypatch.setenv("GPUNIT_MODELS", str(_user_file(tmp_path / "env.toml", "env")))
    _user_file(isolated_home / ".config" / "gpunit" / "models.toml", "default")

    assert _user_rows(given if flag else None) == (["given"] if flag else ["env"])


@pytest.mark.spec("serve:rows:env-before-xdg")
@pytest.mark.parametrize("value", ["set", "", None], ids=["set", "empty", "unset"])
def test_the_environment_comes_before_the_default(
    value: str | None,
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _user_file(isolated_home / ".config" / "gpunit" / "models.toml", "default")
    if value == "set":
        monkeypatch.setenv(
            "GPUNIT_MODELS", str(_user_file(tmp_path / "env.toml", "env"))
        )
    elif value == "":
        monkeypatch.setenv("GPUNIT_MODELS", "")

    assert _user_rows() == (["env"] if value == "set" else ["default"])


@pytest.mark.spec("serve:rows:xdg-default")
@pytest.mark.parametrize(
    "xdg",
    ["absolute", "relative", "empty", None],
    ids=["absolute", "relative", "empty", "unset"],
)
def test_the_default_follows_xdg(
    xdg: str | None,
    tmp_path: Path,
    isolated_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _user_file(tmp_path / "cfg" / "gpunit" / "models.toml", "xdg")
    _user_file(tmp_path / "rel" / "gpunit" / "models.toml", "relative")
    _user_file(isolated_home / ".config" / "gpunit" / "models.toml", "home")
    monkeypatch.chdir(tmp_path)
    if xdg == "absolute":
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    elif xdg == "relative":
        # The XDG base directory spec: a relative path is ignored.
        monkeypatch.setenv("XDG_CONFIG_HOME", "rel")
    elif xdg == "empty":
        monkeypatch.setenv("XDG_CONFIG_HOME", "")

    assert _user_rows() == (["xdg"] if xdg == "absolute" else ["home"])


@pytest.mark.spec("serve:rows:no-file-bundled-only")
def test_no_user_file_leaves_the_bundled_rows_alone(
    capsys: pytest.CaptureFixture[str],
) -> None:
    found = table.rows()

    assert found == table.load()
    assert found.user is None
    assert found.replaced == ()
    assert all(row.source == "bundled" for row in found.models.values())
    assert capsys.readouterr().err == ""


@pytest.mark.spec("serve:rows:named-file-missing-refused")
@pytest.mark.parametrize("there", [False, True], ids=["missing", "twin-there"])
def test_a_named_file_that_cannot_be_read_is_refused(
    there: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "rows.toml"
    if there:
        _user_file(path)
    monkeypatch.setenv("GPUNIT_MODELS", str(path))
    monkeypatch.chdir(tmp_path)
    argv = ["down", "--serve", "qwen3-4b"]

    if there:
        assert gpunit(argv, provider=FakeProvider()) == 0
        return
    assert gpunit(argv, provider=NO_REQUESTS) == 1
    assert f"refused: {path}: " in capsys.readouterr().err


@pytest.mark.spec("serve:rows:merged")
def test_the_user_rows_join_the_bundled_rows(tmp_path: Path) -> None:
    path = _user_file(tmp_path / "rows.toml")

    found = table.rows(path)

    assert sorted(found.models) == ["granite-4.0-micro", "qwen3-4b", "qwen3.8-27b"]
    assert all(row.image == found.image for row in found.models.values())
    assert found.image == table.load().image
    assert found.models["granite-4.0-micro"].source == str(path)
    assert found.models["qwen3-4b"].source == "bundled"
    assert found.user == path
    assert found.replaced == ()


@pytest.mark.spec("serve:rows:image-refused")
@pytest.mark.parametrize("top", ["image", None], ids=["image", "twin-rows-alone"])
def test_a_user_file_naming_an_image_is_refused(
    top: str | None, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _user_file(tmp_path / "rows.toml")
    if top is not None:
        line = f'{top} = "ghcr.io/ada/vllm@sha256:{"b" * 64}"\n'
        path.write_text(line + path.read_text(encoding="utf-8"), encoding="utf-8")

    if top is None:
        assert "granite-4.0-micro" in table.rows(path).models
        return
    with pytest.raises(log.Refusal):
        table.rows(path)
    err = capsys.readouterr().err
    assert f"{path}: unknown key 'image'" in err


@pytest.mark.spec("serve:rows:checked-as-bundled")
@pytest.mark.parametrize(
    ("old", "new", "named", "row"),
    [
        ('"56111ae135df9c53a78c99028e7bc24035a9e979"', '"main"', "'revision'", True),
        ("disk_gb = 40\n", "", "'disk_gb' is required", True),
        ('"16384"', '"16384 tokens"', "a space", True),
        (GRANITE, "", "'models' must hold at least one row", False),
    ],
    ids=["moving-revision", "missing-field", "spaced-arg", "empty-file"],
)
def test_a_user_row_is_checked_as_a_bundled_row_is(
    old: str,
    new: str,
    named: str,
    row: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _user_file(tmp_path / "rows.toml")
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")
    monkeypatch.setenv("GPUNIT_MODELS", str(path))
    monkeypatch.chdir(tmp_path)

    assert gpunit(["down", "--serve", "qwen3-4b"], provider=NO_REQUESTS) == 1
    err = capsys.readouterr().err
    assert f"refused: {path}: " in err
    assert named in err
    assert ("models.granite-4.0-micro" in err) is row


@pytest.mark.spec("serve:rows:checked-as-bundled")
@pytest.mark.parametrize(
    ("args", "named"),
    [
        ('"--revision", "main"', "--revision"),
        ('"--revision=main"', "--revision"),
        ('"--code_revision", "main"', "--code-revision"),
        ('"--tokenizer-revision=main"', "--tokenizer-revision"),
        ('"--served-model-name", "x"', "--served-model-name"),
        ('"--host", "0.0.0.0"', "--host"),
        ('"--port=8001"', "--port"),
        ('"--api-key", "k"', "--api-key"),
        ('"--max-num-seqs", "8"', None),
    ],
    ids=[
        "revision",
        "revision-joined",
        "code-revision-underscored",
        "tokenizer-revision",
        "served-name",
        "host",
        "port",
        "api-key",
        "twin-own-flag",
    ],
)
def test_a_row_resetting_the_launchers_flags_is_refused(
    args: str, named: str | None, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _user_file(tmp_path / "rows.toml")
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace('"hermes"]', f'"hermes", {args}]'), encoding="utf-8")

    if named is None:
        assert "--max-num-seqs" in table.rows(path).models["granite-4.0-micro"].args
        return
    with pytest.raises(log.Refusal):
        table.rows(path)
    err = capsys.readouterr().err
    assert f"{path}: models.granite-4.0-micro: 'args' holds {named}" in err


@pytest.mark.spec("serve:rows:logging-on-refused")
@pytest.mark.parametrize(
    ("flag", "refused"),
    [
        ("--enable-log-requests", True),
        ("--no-enable-log-requests", False),
        ("--enable-log-requests=yes", False),
    ],
    ids=["on", "twin-off", "twin-not-the-flag"],
)
def test_a_row_turning_request_logging_on_is_refused(
    flag: str, refused: bool, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _user_file(tmp_path / "rows.toml")
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace('"hermes"]', f'"hermes", "{flag}"]'), encoding="utf-8")

    if not refused:
        assert flag in table.rows(path).models["granite-4.0-micro"].args
        return
    with pytest.raises(log.Refusal):
        table.rows(path)
    err = capsys.readouterr().err
    assert (
        f"{path}: models.granite-4.0-micro: 'args' holds --enable-log-requests" in err
    )


@pytest.mark.spec("serve:rows:logging-on-refused")
def test_a_bundled_row_turning_request_logging_on_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _bundled_with('"16384"', '"16384", "--enable-log-requests"', tmp_path)

    with pytest.raises(log.Refusal):
        table.load(path)
    assert (
        "models.qwen3-4b: 'args' holds --enable-log-requests" in capsys.readouterr().err
    )
