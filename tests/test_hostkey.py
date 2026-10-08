import json
from pathlib import Path

import pytest

from gpunit import log
from tests.fakes import KEY_LINE, SERVED, FakeClock, FakeProvider
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
    [([["unrelated line"]], "", 60), ([["gpunit host key: SHA256:served"]], "1", 180)],
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
    provider = FakeProvider(
        logs=[["a boot that logs heavily"]], since_logs=[[KEY_LINE]]
    )
    # The stamp says whether the create had been asked when it was taken.
    monkeypatch.setattr(
        log, "utc", lambda: "after" if provider.named("create") else "before"
    )

    assert gpunit(["up"], provider=provider) == 0
    created = json.loads((cwd / ".gpunit" / "pod").read_text(encoding="utf-8"))
    assert created["created"] == "before"
    assert provider.named("log") == [("pod-1", 5000, None), ("pod-1", 5000, "before")]
    assert f"host key verified: {SERVED}" in capsys.readouterr().err
