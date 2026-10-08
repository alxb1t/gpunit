from pathlib import Path

import pytest

from gpunit import session
from gpunit.log import Refusal
from gpunit.state import State
from tests.fakes import RECORD


@pytest.mark.spec("session:ssh:uses-record")
def test_ssh_uses_the_record(tmp_path: Path) -> None:
    state = State(tmp_path)
    state.write(RECORD)
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


@pytest.mark.spec("session:ssh:own-config-only")
def test_ssh_reads_no_config_and_offers_the_session_key_alone(tmp_path: Path) -> None:
    state = State(tmp_path)
    state.write(RECORD)
    execs: list[list[str]] = []

    session.ssh(state, execvp=lambda file, argv: execs.append(argv))

    [argv] = execs
    assert argv[1:5] == ["-F", "none", "-o", "IdentitiesOnly=yes"]


@pytest.mark.spec("session:ssh:no-ssh-refuses")
def test_no_ssh_refuses(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state = State(tmp_path)
    state.write(RECORD)

    def missing(file: str, argv: list[str]) -> None:
        raise FileNotFoundError(2, "No such file or directory", file)

    with pytest.raises(Refusal, match="ssh could not be run"):
        session.ssh(state, execvp=missing)
    [line] = capsys.readouterr().err.splitlines()
    assert "'ssh'" in line
