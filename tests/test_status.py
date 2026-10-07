import json
from pathlib import Path

import pytest

from gpunit.state import Record, State
from tests.fakes import FakeProvider
from tests.helpers import IMAGE, NoRequests, gpunit


@pytest.mark.spec("cli:status:json")
def test_status_as_json(cwd: Path, capsys: pytest.CaptureFixture[str]) -> None:
    State(cwd).write(
        Record("pod-1", IMAGE, "203.0.113.7", 40022, "2026-10-07T00:00:00Z")
    )

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
    assert gpunit(["status"], provider=NoRequests()) == 0
    assert capsys.readouterr().out == "no session is recorded\n"
