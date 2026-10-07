from pathlib import Path

import pytest

from gpunit import session
from gpunit.log import Refusal
from gpunit.state import Record, State
from tests.helpers import IMAGE


@pytest.mark.spec("session:ssh:uses-record")
def test_ssh_uses_the_record(tmp_path: Path) -> None:
    state = State(tmp_path)
    state.write(Record("pod-1", IMAGE, "203.0.113.7", 40022, "2026-10-07T00:00:00Z"))
    execs: list[tuple[str, list[str]]] = []

    session.ssh(state, execvp=lambda file, argv: execs.append((file, argv)))

    [(file, argv)] = execs
    assert file == "ssh"
    assert argv[-3:] == ["root@203.0.113.7", "-p", "40022"]
    joined = " ".join(argv)
    for part in (".gpunit/key", ".gpunit/known_hosts", "StrictHostKeyChecking=yes"):
        assert part in joined

    state.clear_session()
    with pytest.raises(Refusal, match="no session is recorded"):
        session.ssh(state, execvp=lambda file, argv: execs.append((file, argv)))
