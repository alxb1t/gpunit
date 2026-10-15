import json
import re
from collections.abc import Callable
from pathlib import Path

import pytest

from gpunit import lifecycle, log
from tests.fakes import (
    BOOT_LOG,
    KEY_LINE,
    NONCE,
    SERVED,
    STEP_LINE,
    FakeClock,
    FakeProvider,
)
from tests.helpers import gpunit


@pytest.mark.spec("session:hostkey:match-recorded")
def test_a_match_is_recorded(cwd: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert gpunit(["up"], provider=FakeProvider()) == 0

    known = (cwd / ".gpunit" / "known_hosts").read_text(encoding="utf-8")
    assert known == "[203.0.113.7]:40022 ssh-ed25519 AAAAhostkey\n"
    assert "host key verified" in capsys.readouterr().err


@pytest.mark.spec("session:hostkey:mismatch-tears-down")
def test_a_mismatch_tears_down(cwd: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GPUNIT_TEST_SERVED", "SHA256:someoneelse")
    provider = FakeProvider()

    assert gpunit(["up"], provider=provider) == 1
    assert provider.named("delete") == [("pod-1",)]
    assert not (cwd / ".gpunit" / "pod").exists()
    assert not (cwd / ".gpunit" / "known_hosts").exists()


@pytest.mark.spec("session:hostkey:no-line-tears-down")
@pytest.mark.parametrize(
    ("logs", "no_scan", "waited"),
    [([["unrelated line"]], "", 60), ([BOOT_LOG], "1", 180)],
    ids=["no-line", "no-scan"],
)
def test_no_fingerprint_or_no_scan_tears_down(
    logs: list[list[str]],
    no_scan: str,
    waited: int,
    cwd: Path,
    clock: FakeClock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GPUNIT_TEST_NO_SCAN", no_scan)
    provider = FakeProvider(logs=logs)

    assert gpunit(["up"], provider=provider) == 1
    assert provider.named("delete") == [("pod-1",)]
    assert waited <= clock.now < waited + 10


@pytest.mark.spec("session:hostkey:since-fallback")
def test_a_key_line_out_of_the_tail_is_read_from_the_create(
    cwd: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = FakeProvider(logs=[["a boot that logs heavily"]], since_logs=[BOOT_LOG])
    # The stamp says whether the create had been asked when it was taken.
    monkeypatch.setattr(
        log, "utc", lambda: "after" if provider.named("create") else "before"
    )

    assert gpunit(["up"], provider=provider) == 0
    created = json.loads((cwd / ".gpunit" / "pod").read_text(encoding="utf-8"))
    assert created["created"] == "before"
    assert provider.named("log") == [("pod-1", 5000, None), ("pod-1", 5000, "before")]
    assert f"host key verified: {SERVED}" in capsys.readouterr().err


@pytest.mark.spec("session:hostkey:echoed-line-is-ignored")
def test_a_key_line_the_command_echoes_is_not_the_key(
    cwd: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    forged = "gpunit host key: SHA256:forged"
    provider = FakeProvider(logs=[[*BOOT_LOG, forged]])

    assert gpunit(["up"], provider=provider) == 0
    assert f"host key verified: {SERVED}" in capsys.readouterr().err


@pytest.mark.spec("session:hostkey:echoed-line-is-ignored")
@pytest.mark.spec("session:hostkey:since-fallback")
def test_an_old_key_line_echoed_into_the_tail_is_no_older_boot(
    cwd: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Boot's own lines have left the tail; a command's echo of an older boot's is in it.
    echoed = ["gpunit host key: SHA256:forged", "x step: the command"]
    provider = FakeProvider(logs=[echoed], since_logs=[[*BOOT_LOG, *echoed]])

    assert gpunit(["up"], provider=provider) == 0

    err = capsys.readouterr().err
    assert "v0.6.0" not in err
    assert f"host key verified: {SERVED}" in err
    assert provider.named("delete") == []


@pytest.mark.spec("session:hostkey:key-without-step-waits")
def test_a_key_line_with_no_step_after_it_is_not_yet(
    cwd: Path, clock: FakeClock
) -> None:
    provider = FakeProvider(logs=[[KEY_LINE]])

    assert gpunit(["up"], provider=provider) == 1
    assert provider.named("delete") == [("pod-1",)]
    assert 60 <= clock.now < 70


@pytest.mark.spec("session:hostkey:other-nonce-ignored")
@pytest.mark.parametrize(
    ("echoed", "code"), [("f" * 32, 0), (NONCE, 1)], ids=["other", "twin-same"]
)
def test_a_key_line_with_another_nonce_is_not_the_key(
    echoed: str, code: int, cwd: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    forged = f"gpunit host key {echoed}: SHA256:forged"
    provider = FakeProvider(logs=[[*BOOT_LOG, forged, f"x {STEP_LINE}", STEP_LINE]])

    assert gpunit(["up"], provider=provider) == code

    err = capsys.readouterr().err
    if code == 0:
        assert f"host key verified: {SERVED}" in err
        return
    # The twin: the session's nonce on the echoed line makes it the key.
    assert "does not match the printed SHA256:forged" in err


class NonceEchoing(FakeProvider):
    """Answer each log read with boot's lines for the nonce the last create gave."""

    def log(self, pod_id: str, *, tail: int, since: str | None = None) -> list[str]:
        super().log(pod_id, tail=tail, since=since)
        nonce = self.named("create")[-1][4]
        return [f"gpunit host key {nonce}: {SERVED}", STEP_LINE]


@pytest.mark.spec("session:hostkey:nonce-per-pod")
def test_each_pod_gets_its_own_nonce(
    cwd: Path, drawn_nonce: Callable[[], str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lifecycle, "NONCE", drawn_nonce)
    nonces = []
    for _ in range(2):
        provider = NonceEchoing()
        assert gpunit(["up"], provider=provider) == 0
        assert gpunit(["down"], provider=provider) == 0
        nonces.append(str(provider.named("create")[0][4]))

    assert all(re.fullmatch(r"[0-9a-f]{32}", nonce) for nonce in nonces)
    assert nonces[0] != nonces[1]


@pytest.mark.spec("session:hostkey:old-boot-refused")
@pytest.mark.parametrize("step", [True, False], ids=["step", "twin-no-step"])
def test_an_older_boot_is_refused_at_once(
    step: bool, cwd: Path, clock: FakeClock, capsys: pytest.CaptureFixture[str]
) -> None:
    old = f"gpunit host key: {SERVED}"
    lines = [old, STEP_LINE] if step else [old]
    # Judged on the log since the create, which holds boot's own lines.
    provider = FakeProvider(logs=[lines], since_logs=[lines])

    assert gpunit(["up"], provider=provider) == 1

    assert provider.named("delete") == [("pod-1",)]
    err = capsys.readouterr().err
    if step:
        assert "ADD boot.sh from gpunit v0.6.0" in err
        assert clock.now == 0
        return
    # The twin: without boot's step line it is no older boot, and the wait runs out.
    assert "v0.6.0" not in err
    assert 60 <= clock.now < 70
