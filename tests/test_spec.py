from pathlib import Path

import pytest

from gpunit.spec import Port, load_spec
from tests.helpers import NO_REQUESTS, VALID, gpunit, write_spec


def _without(key: str) -> str:
    return "".join(
        line for line in VALID.splitlines(keepends=True) if not line.startswith(key)
    )


@pytest.mark.spec("spec:file:missing-field-named")
def test_a_missing_required_field_is_named(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    write_spec(tmp_path, _without("gpus ="))

    assert gpunit(["up"], provider=NO_REQUESTS) == 1
    assert "'gpus' is required" in capsys.readouterr().err


@pytest.mark.spec("spec:file:unknown-key-refused")
def test_an_unknown_key_is_refused_naming_the_nearest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    write_spec(tmp_path, _without("gpus =") + 'gpu = "RTX 4090"\n')

    assert gpunit(["up"], provider=NO_REQUESTS) == 1
    assert "unknown key 'gpu'; did you mean 'gpus'?" in capsys.readouterr().err


@pytest.mark.spec("spec:file:ports-default-local")
def test_a_port_forwards_to_the_same_local_port(tmp_path: Path) -> None:
    spec = load_spec(write_spec(tmp_path, VALID + "ports = [8188]\n"))

    assert spec.ports == (Port(remote=8188, local=8188),)


@pytest.mark.spec("spec:file:ports-local-override")
def test_a_ports_local_side_is_overridden(tmp_path: Path) -> None:
    spec = load_spec(
        write_spec(tmp_path, VALID + "ports = [{ remote = 8188, local = 18188 }]\n")
    )

    assert spec.ports == (Port(remote=8188, local=18188),)


@pytest.mark.spec("spec:image:tag-refused")
@pytest.mark.parametrize(
    "image",
    ["ghcr.io/alxb1t/isekai:latest", "ghcr.io/alxb1t/isekai@sha256:" + "A" * 64],
)
def test_an_image_without_a_digest_is_refused(
    image: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    write_spec(tmp_path, _without("image =") + f'image = "{image}"\n')

    assert gpunit(["up"], provider=NO_REQUESTS) == 1
    assert "@sha256:<64 hex>" in capsys.readouterr().err


@pytest.mark.spec("spec:ceiling:required")
@pytest.mark.parametrize("ceiling", [None, '"45"', '"0m"'])
def test_no_ceiling_no_pod(
    ceiling: str | None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    text = _without("ceiling =") + ("" if ceiling is None else f"ceiling = {ceiling}\n")
    write_spec(tmp_path, text)

    assert gpunit(["up"], provider=NO_REQUESTS) == 1
    assert "'ceiling'" in capsys.readouterr().err


@pytest.mark.spec("spec:file:port-out-of-range")
@pytest.mark.parametrize(
    "ports", ["[70000]", "[{ remote = 8188, local = 0 }]"], ids=["remote", "local"]
)
def test_a_port_out_of_range_is_refused(
    ports: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    write_spec(tmp_path, VALID + f"ports = {ports}\n")

    assert gpunit(["up"], provider=NO_REQUESTS) == 1
    err = capsys.readouterr().err
    assert "'ports'" in err
    assert "outside 1-65535" in err


@pytest.mark.spec("spec:file:port-out-of-range")
def test_the_range_ends_are_ports(tmp_path: Path) -> None:
    spec = load_spec(
        write_spec(tmp_path, VALID + "ports = [{ remote = 65535, local = 1 }]\n")
    )

    assert spec.ports == (Port(remote=65535, local=1),)


@pytest.mark.spec("spec:file:env-gpunit-refused")
@pytest.mark.parametrize(
    ("key", "refused"),
    [("GPUNIT_VOLUME_PATH", True), ("VOLUME_PATH", False)],
    ids=["gpunit", "twin-other"],
)
def test_a_gpunit_variable_in_env_is_refused(
    key: str,
    refused: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    path = write_spec(tmp_path, VALID + f'[env]\n{key} = "/data"\n')

    if refused:
        assert gpunit(["up"], provider=NO_REQUESTS) == 1
        assert f"env {key!r}" in capsys.readouterr().err
    else:
        assert load_spec(path).env == {key: "/data"}


@pytest.mark.spec("spec:file:volume-keys")
def test_the_window_volumes_keys_load(tmp_path: Path) -> None:
    window = 'volume_gb = 60\nvolume_ceiling = "4h"\nvolume_datacenter = "EU-RO-1"\n'
    spec = load_spec(write_spec(tmp_path, VALID + window))

    assert (spec.volume_gb, spec.volume_ceiling_s, spec.volume_datacenter) == (
        60,
        14400,
        "EU-RO-1",
    )
    assert spec.volume is None


@pytest.mark.spec("spec:file:volume-gb-needs-ceiling")
@pytest.mark.parametrize(
    ("keys", "named"),
    [
        ("volume_gb = 60\n", "'volume_gb' needs 'volume_ceiling'"),
        ('volume_ceiling = "4h"\n', "'volume_ceiling' needs 'volume_gb'"),
        ('volume_datacenter = "EU-RO-1"\n', "'volume_datacenter' needs 'volume_gb'"),
        ('volume_gb = 60\nvolume_ceiling = "4"\n', "'volume_ceiling' must be"),
    ],
    ids=["no-ceiling", "ceiling-alone", "datacenter-alone", "bad-ceiling"],
)
def test_a_window_key_without_its_pair_is_refused(
    keys: str,
    named: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    write_spec(tmp_path, VALID + keys)

    assert gpunit(["up"], provider=NO_REQUESTS) == 1
    assert named in capsys.readouterr().err


@pytest.mark.spec("spec:file:volume-and-volume-gb-refused")
def test_a_kept_volume_and_a_window_volume_are_refused_together(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    write_spec(
        tmp_path, VALID + 'volume = "v1"\nvolume_gb = 60\nvolume_ceiling = "4h"\n'
    )

    assert gpunit(["up"], provider=NO_REQUESTS) == 1
    assert "'volume' and 'volume_gb' cannot both be set" in capsys.readouterr().err


@pytest.mark.spec("spec:file:volume-gb-out-of-range")
@pytest.mark.parametrize(
    ("size", "refused"),
    [(5, True), (5000, True), (9, True), (4001, True), (10, False), (4000, False)],
)
def test_a_volume_size_out_of_range_is_refused(
    size: int,
    refused: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    path = write_spec(tmp_path, VALID + f'volume_gb = {size}\nvolume_ceiling = "4h"\n')

    if refused:
        assert gpunit(["up"], provider=NO_REQUESTS) == 1
        assert "'volume_gb' must be from 10 to 4000" in capsys.readouterr().err
    else:
        assert load_spec(path).volume_gb == size
