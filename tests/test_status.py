import fcntl
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from gpunit import ledger, log, spend
from gpunit.provider import Lost, PodInfo, Unknown, VolumeCost
from gpunit.state import State, Window
from tests.fakes import RECORD, FakeProvider
from tests.helpers import IMAGE, NO_REQUESTS, gpunit


@pytest.mark.spec("cli:status:json")
def test_status_as_json(cwd: Path, capsys: pytest.CaptureFixture[str]) -> None:
    State(cwd).write(RECORD)

    assert gpunit(["status", "--json"], provider=FakeProvider()) == 0
    assert json.loads(capsys.readouterr().out) == {
        "id": "pod-1",
        "image": IMAGE,
        "host": "203.0.113.7",
        "port": 40022,
        "status": "RUNNING",
    }


@pytest.mark.spec("cli:status:no-record")
def test_no_record(cwd: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert gpunit(["status"], provider=NO_REQUESTS) == 0
    assert capsys.readouterr().out == "no session is recorded\n"


@pytest.mark.spec("cli:status:gone-clears")
@pytest.mark.spec("cli:status:listed-keeps-record")
@pytest.mark.spec("session:down:gone-clears-its-own")
@pytest.mark.parametrize(
    ("pods", "account_pods", "cleared", "held"),
    [
        ({"pod-1": Unknown("RunPod does not know pod 'pod-1'")}, [], True, False),
        (
            {"pod-1": Unknown("RunPod does not know pod 'pod-1'")},
            ["pod-1"],
            False,
            False,
        ),
        (
            {"pod-1": Unknown("RunPod does not know pod 'pod-1'")},
            Lost("pod listing returned HTTP 403"),
            False,
            False,
        ),
        ({}, [], False, False),
        ({"pod-1": Unknown("RunPod does not know pod 'pod-1'")}, [], False, True),
    ],
    ids=["gone", "still-listed", "listing-lost", "read-lost", "held"],
)
def test_status_clears_a_gone_pod(
    pods: dict[str, PodInfo | Exception],
    account_pods: list[str] | Exception,
    cleared: bool,
    held: bool,
    cwd: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state = State(cwd)
    state.write(RECORD)
    provider = FakeProvider(gets=[None], pods=pods, account_pods=account_pods)

    argv = ["status", "--json"] if cleared or held else ["status"]
    if held:
        holder = os.open(state.lock, os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(holder, fcntl.LOCK_EX)
    try:
        assert gpunit(argv, provider=provider) == 0
    finally:
        if held:
            os.close(holder)
    captured = capsys.readouterr()
    assert (State(cwd).read() is None) is cleared
    assert ("pod pod-1 is gone; its record is cleared" in captured.err) is cleared
    if held:
        assert json.loads(captured.out)["status"] == "UNKNOWN"
    else:
        assert (
            (captured.out == "null\n")
            if cleared
            else ("status=UNKNOWN" in captured.out)
        )


@pytest.mark.spec("volume:status:named")
@pytest.mark.parametrize("as_json", [False, True], ids=["words", "json-unchanged"])
def test_the_volume_line(
    as_json: bool, cwd: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    state = State(cwd)
    state.write(RECORD)
    ends = log.utc(3600)
    state.write_window(Window("v1", "EU-RO-1", 60, ends))

    argv = ["status", "--json"] if as_json else ["status"]
    assert gpunit(argv, provider=FakeProvider()) == 0
    out = capsys.readouterr().out.splitlines()
    if as_json:
        assert len(out) == 1
        assert json.loads(out[0])["id"] == "pod-1"
    else:
        assert out[1] == f"volume=v1 datacenter=EU-RO-1 ends={ends}"


@pytest.mark.spec("volume:status:named")
def test_the_volume_line_needs_no_session_and_no_key(
    cwd: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    State(cwd).write_window(Window("v1", "EU-RO-1", 60, "2999-01-01T14:30:00Z"))

    assert gpunit(["status"], provider=NO_REQUESTS) == 0
    assert capsys.readouterr().out.splitlines() == [
        "no session is recorded",
        "volume=v1 datacenter=EU-RO-1 ends=2999-01-01T14:30:00Z",
    ]


@pytest.mark.spec("volume:ceiling:overdue-deleted")
@pytest.mark.parametrize("code", [204, 409], ids=["deleted", "delete-refused"])
def test_an_overdue_volume_is_deleted_first(
    code: int, cwd: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    state = State(cwd)
    state.write_window(Window("v1", "EU-RO-1", 60, log.utc(-60)))
    provider = FakeProvider(volume_deletes={"v1": code})

    assert gpunit(["status"], provider=provider) == 0
    assert provider.named("delete_volume") == [("v1",)]
    captured = capsys.readouterr()
    assert "volume v1 passed its ceiling" in captured.err
    if code == 204:
        assert state.window() is None
        assert captured.out == "no session is recorded\n"
    else:
        assert state.window() is not None
        assert "ends=overdue" in captured.out


@pytest.mark.spec("volume:gone:sweep-clears")
@pytest.mark.parametrize(
    ("listed", "cleared"), [([], True), (["v1"], False)], ids=["gone", "twin-listed"]
)
def test_the_sweep_clears_a_gone_volume(
    listed: list[str],
    cleared: bool,
    cwd: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state = State(cwd)
    ends = log.utc(-60)
    state.write_window(Window("v1", "EU-RO-1", 60, ends))
    ledger.record_volume("isekai", "v1", ends)
    state.mark_volume_pending()
    provider = FakeProvider(
        volumes={"v1": Unknown("RunPod does not know volume 'v1'")},
        volume_deletes={"v1": 404},
        account_volumes=listed,
    )

    assert gpunit(["status"], provider=provider) == 0
    assert (state.window() is None) is cleared
    assert (not state.volume_pending.exists()) is cleared
    err = capsys.readouterr().err
    assert ("and is gone; the record is cleared" in err) is cleared
    # Gone is the key's account's view: another account's key misjudges a volume
    # that still bills, so the ledger records no delete and `spend` names it.
    assert ledger.deleted() == set()
    tomorrow = datetime.now(UTC) + timedelta(days=1)
    monkeypatch.setattr(spend, "utc_now", lambda: tomorrow)
    billed = VolumeCost("v1", f"{tomorrow.date().isoformat()}T00:00:00Z", 0.01)
    assert gpunit(["spend"], provider=FakeProvider(volume_costs=[billed])) == 0
    assert (
        "volume v1 (isekai) passed its ceiling and still bills"
        in capsys.readouterr().err
    )
