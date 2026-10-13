from pathlib import Path

import pytest

from gpunit import log
from gpunit.serve import table
from gpunit.spec import DIGEST, Port

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
    args = list(row.args)
    assert args[args.index("--tool-call-parser") + 1] == "qwen3_coder"
    assert args[args.index("--reasoning-parser") + 1] == "qwen3"
    assert "--language-model-only" in args
    # Its Mamba cache holds 192 sequences on 48 GB: vLLM's default 256 fails to start.
    assert int(args[args.index("--max-num-seqs") + 1]) <= 192


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
