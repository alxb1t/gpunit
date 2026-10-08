import json
import re
from pathlib import Path

import pytest

from gpunit.provider import GpuInfo, Lost, Refused, Unknown, VolumeInfo
from gpunit.runpod import RunPod
from gpunit.state import State
from tests.fakes import (
    KEY_LINE,
    RUNNING,
    FakeClock,
    FakeOpener,
    FakeProvider,
    fixture,
    page,
)
from tests.helpers import IMAGE, NO_REQUESTS, VALID, gpunit, install_stubs, write_spec


def creates(provider: FakeProvider) -> list[str]:
    return [str(args[1]) for args in provider.named("create")]


@pytest.mark.spec("session:one:recorded-refuses")
def test_a_recorded_pod_refuses_up(
    cwd: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (cwd / ".gpunit").mkdir()
    (cwd / ".gpunit" / "pod").write_text("{}", encoding="utf-8")

    assert gpunit(["up"], provider=NO_REQUESTS) == 1
    assert "run gpunit down" in capsys.readouterr().err


@pytest.mark.spec("session:one:recorded-refuses")
def test_a_pending_create_refuses_up(cwd: Path) -> None:
    State(cwd).mark_pending()

    assert gpunit(["up"], provider=NO_REQUESTS) == 1


@pytest.mark.spec("session:one:listed-refuses")
def test_a_listed_pod_refuses_up(cwd: Path, capsys: pytest.CaptureFixture[str]) -> None:
    provider = FakeProvider(listings=[[("pod-9", "RUNNING")]])

    assert gpunit(["up"], provider=provider) == 1
    assert "pod-9 (RUNNING)" in capsys.readouterr().err
    assert creates(provider) == []


@pytest.mark.spec("session:one:look-alike-image-ignored")
def test_up_lists_by_the_specs_project_and_image(cwd: Path) -> None:
    provider = FakeProvider(listings=[[]])

    assert gpunit(["up"], provider=provider) == 0
    assert provider.named("list") == [("isekai", IMAGE)]


@pytest.mark.spec("session:place:unknown-card-refuses")
def test_an_unknown_card_refuses(cwd: Path, capsys: pytest.CaptureFixture[str]) -> None:
    provider = FakeProvider(gpus={"RTX A6000": Unknown("404")})

    assert gpunit(["up"], provider=provider) == 1
    assert "'RTX A6000'" in capsys.readouterr().err
    assert creates(provider) == []


@pytest.mark.spec("session:place:under-floor-skipped")
def test_a_card_under_the_floor_is_skipped(
    cwd: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = FakeProvider(gpus={"RTX 4090": GpuInfo(vram_gb=16, hourly=0.4)})

    assert gpunit(["up"], provider=provider) == 0
    assert creates(provider) == ["RTX A6000"]
    assert "skipped: RTX 4090 has 16 GB" in capsys.readouterr().err


@pytest.mark.spec("session:place:under-floor-skipped")
def test_a_card_over_max_hourly_is_skipped(cwd: Path) -> None:
    write_spec(cwd, VALID + "max_hourly = 0.5\n")
    provider = FakeProvider(gpus={"RTX A6000": GpuInfo(vram_gb=48, hourly=0.4)})

    assert gpunit(["up"], provider=provider) == 0
    assert creates(provider) == ["RTX A6000"]


@pytest.mark.spec("session:place:400-moves-on")
def test_a_400_moves_on_to_the_next_card(cwd: Path) -> None:
    provider = FakeProvider(creates=[Refused("no capacity"), "pod-2"])

    assert gpunit(["up"], provider=provider) == 0
    assert creates(provider) == ["RTX 4090", "RTX A6000"]
    record = State(cwd).read()
    assert record is not None and record.id == "pod-2"


@pytest.mark.spec("session:place:none-placed")
def test_none_placed_exits_1_with_no_record(cwd: Path) -> None:
    provider = FakeProvider(creates=[Refused("no capacity")])

    assert gpunit(["up"], provider=provider) == 1
    assert creates(provider) == ["RTX 4090", "RTX A6000"]
    assert not (cwd / ".gpunit" / "pod").exists()
    assert not (cwd / ".gpunit" / "pending").exists()


@pytest.mark.spec("session:lost:5xx-exits-3")
def test_a_5xx_create_is_lost(cwd: Path, capsys: pytest.CaptureFixture[str]) -> None:
    provider = FakeProvider(creates=[Lost("create returned HTTP 503: unavailable")])

    assert gpunit(["up"], provider=provider) == 3
    assert (cwd / ".gpunit" / "pending").exists()
    assert "run gpunit down" in capsys.readouterr().err
    assert creates(provider) == ["RTX 4090"]


@pytest.mark.spec("session:lost:transport-exits-3")
def test_a_transport_failure_is_lost(cwd: Path) -> None:
    provider = FakeProvider(creates=[Lost("create on 'RTX 4090' got no answer")])

    assert gpunit(["up"], provider=provider) == 3
    assert (cwd / ".gpunit" / "pending").exists()
    assert not (cwd / ".gpunit" / "pod").exists()


@pytest.mark.spec("session:wait:deadline-tears-down")
def test_the_deadline_tears_down(cwd: Path, clock: FakeClock) -> None:
    provider = FakeProvider(gets=[None])

    assert gpunit(["up"], provider=provider) == 1
    assert provider.named("delete") == [("pod-1",)]
    assert not (cwd / ".gpunit" / "pod").exists()
    assert clock.now >= 420


@pytest.mark.spec("session:wait:failed-poll-is-not-yet")
def test_a_failed_poll_is_not_yet(cwd: Path) -> None:
    provider = FakeProvider(gets=[None, None, RUNNING])

    assert gpunit(["up"], provider=provider) == 0
    assert len(provider.named("get")) == 3
    record = State(cwd).read()
    assert record is not None and (record.host, record.port) == ("203.0.113.7", 40022)


@pytest.mark.spec("session:volume:unreadable-refuses")
def test_an_unreadable_volume_refuses(
    cwd: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_spec(cwd, VALID + 'volume = "v1"\n')
    provider = FakeProvider(volumes={"v1": Unknown("404")})

    assert gpunit(["up"], provider=provider) == 1
    assert "volume v1" in capsys.readouterr().err
    assert creates(provider) == []


@pytest.mark.spec("session:volume:pins-datacenter")
def test_the_volume_is_read_before_any_create(cwd: Path) -> None:
    write_spec(cwd, VALID + 'volume = "v1"\n')
    provider = FakeProvider(volumes={"v1": VolumeInfo("EU-RO-1", 100)})

    assert gpunit(["up"], provider=provider) == 0
    verbs = [name for name, _ in provider.calls]
    assert verbs.index("volume") < verbs.index("create")


@pytest.mark.spec("session:key:fresh-per-session")
def test_the_keypair_is_made_and_passed(cwd: Path) -> None:
    provider = FakeProvider()

    assert gpunit(["up"], provider=provider) == 0
    key = cwd / ".gpunit" / "key"
    assert key.stat().st_mode & 0o777 == 0o600
    pubkey = (cwd / ".gpunit" / "key.pub").read_text(encoding="utf-8").strip()
    assert provider.named("create")[0][2] == pubkey


@pytest.mark.spec("session:key:fresh-per-session")
def test_no_ssh_keygen_refuses_before_any_request(
    cwd: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PATH", str(cwd / "nothing"))

    assert gpunit(["up"], provider=NO_REQUESTS) == 1
    assert "not on PATH: ssh, ssh-keygen, ssh-keyscan;" in capsys.readouterr().err


@pytest.mark.spec("session:tools:missing-refuses")
def test_no_ssh_keyscan_refuses_before_any_request(
    cwd: Path,
    ssh_bin: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    some = install_stubs(
        cwd / "bin",
        {tool: (ssh_bin / tool).read_text() for tool in ("ssh", "ssh-keygen")},
    )
    monkeypatch.setenv("PATH", str(some))

    assert gpunit(["up"], provider=NO_REQUESTS) == 1
    assert "not on PATH: ssh-keyscan; install OpenSSH" in capsys.readouterr().err


@pytest.mark.spec("cli:exits:refusal-exits-1")
def test_a_refusal_is_one_stamped_stderr_line(
    cwd: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    State(cwd).write_known_hosts("x")
    (cwd / ".gpunit" / "pod").write_text("{}", encoding="utf-8")

    assert gpunit(["up"], provider=NO_REQUESTS) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ refused: .+\n", err)


def up_over_http(cwd: Path) -> FakeOpener:
    """Run `up` on RunPod over scripted HTTP answers; return the opener."""
    write_spec(cwd, VALID + 'volume = "v1"\nports = [8188]\n')
    log = f"data: {json.dumps({'line': KEY_LINE})}\n".encode()
    opener = FakeOpener(
        (200, page([], None)),
        (200, fixture("volume.json")),
        (200, fixture("gpu.json")),
        (200, fixture("gpu.json")),
        (201, fixture("pod_created.json")),
        (200, fixture("pod_running.json")),
        (200, log),
    )
    provider = RunPod({"RUNPOD_API_KEY": "rpa_test"}, opener=opener)
    assert gpunit(["up"], provider=provider) == 0
    return opener


@pytest.mark.spec("session:volume:pins-datacenter")
def test_the_create_names_the_volumes_datacenter(cwd: Path) -> None:
    body = up_over_http(cwd).sent(4)

    assert body["dataCenterIds"] == ["EU-RO-1"]
    assert body["mounts"] == {"network": [{"volumeId": "v1", "path": "/runpod-volume"}]}


@pytest.mark.spec("session:create:secure-and-22")
def test_the_create_is_secure_and_exposes_22_only(cwd: Path) -> None:
    body = up_over_http(cwd).sent(4)

    assert body["cloud"] == "SECURE"
    assert body["ports"] == ["22/tcp"]


@pytest.mark.spec("spec:ceiling:reaches-the-pod")
def test_the_ceiling_reaches_the_pod_in_seconds(cwd: Path) -> None:
    body = up_over_http(cwd).sent(4)

    env = body["env"]
    assert isinstance(env, dict) and env["GPUNIT_CEILING"] == "2700"
