import json
from pathlib import Path

import pytest

from gpunit import log
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
