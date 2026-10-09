from pathlib import Path

import pytest

from gpunit import lifecycle
from gpunit.log import Refusal
from gpunit.state import State
from tests.fakes import RECORD
from tests.helpers import gpunit


@pytest.fixture
def state(tmp_path: Path) -> State:
    recorded = State(tmp_path)
    recorded.write(RECORD)
    return recorded


@pytest.mark.spec("session:ssh:uses-record")
def test_ssh_uses_the_record(state: State) -> None:
    execs: list[tuple[str, list[str]]] = []

    lifecycle.ssh(state, execvp=lambda file, argv: execs.append((file, argv)))

    [(file, argv)] = execs
    assert file == "ssh"
    assert argv[-3:] == ["root@203.0.113.7", "-p", "40022"]
    joined = " ".join(argv)
    for part in (".gpunit/key", ".gpunit/known_hosts", "StrictHostKeyChecking=yes"):
        assert part in joined

    state.clear_session()
    with pytest.raises(Refusal, match="no session is recorded"):
        lifecycle.ssh(state, execvp=lambda file, argv: execs.append((file, argv)))


@pytest.mark.spec("session:ssh:own-config-only")
def test_ssh_reads_no_config_and_offers_the_session_key_alone(state: State) -> None:
    execs: list[list[str]] = []

    lifecycle.ssh(state, execvp=lambda file, argv: execs.append(argv))

    [argv] = execs
    assert argv[1:5] == ["-F", "none", "-o", "IdentitiesOnly=yes"]


@pytest.mark.spec("session:ssh:no-ssh-refuses")
def test_no_ssh_refuses(state: State, capsys: pytest.CaptureFixture[str]) -> None:
    def missing(file: str, argv: list[str]) -> None:
        raise FileNotFoundError(2, "No such file or directory", file)

    with pytest.raises(Refusal, match="ssh could not be run"):
        lifecycle.ssh(state, execvp=missing)
    [line] = capsys.readouterr().err.splitlines()
    assert "'ssh'" in line


@pytest.mark.spec("session:ssh:no-ssh-refuses")
def test_gpunit_ssh_without_ssh_exits_1(
    cwd: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    State(cwd).write(RECORD)
    # An empty PATH: the exec finds no `ssh`, so it can never replace this process.
    empty = cwd / "empty"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))

    assert gpunit(["ssh"]) == 1
    [line] = capsys.readouterr().err.splitlines()
    assert "ssh could not be run" in line
