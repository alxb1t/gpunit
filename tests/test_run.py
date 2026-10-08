import os
import signal
import socket
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from gpunit import run
from gpunit.provider import Lost
from tests.fakes import FakeProvider
from tests.helpers import NO_REQUESTS, VALID, gpunit, write_spec


@pytest.fixture
def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture
def listening() -> Iterator[int]:
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        yield server.getsockname()[1]


def with_port(cwd: Path, local: int) -> None:
    write_spec(cwd, VALID + f"ports = [{{ remote = 8188, local = {local} }}]\n")


class InterruptingProvider(FakeProvider):
    """Send this process the signal again from inside the teardown's delete."""

    def __init__(self, number: int) -> None:
        super().__init__()
        self.number = number

    def delete(self, pod_id: str) -> int:
        os.kill(os.getpid(), self.number)
        return super().delete(pod_id)


@pytest.mark.spec("run:handover:env")
def test_the_environment_names_the_session(
    cwd: Path, free_port: int, capfd: pytest.CaptureFixture[str]
) -> None:
    with_port(cwd, free_port)

    assert gpunit(["run", "--", "env"], provider=FakeProvider()) == 0
    env = dict(line.split("=", 1) for line in capfd.readouterr().out.splitlines())
    assert env["GPUNIT_HOST"] == "203.0.113.7"
    assert env["GPUNIT_PORT_8188"] == str(free_port)
    assert env["GPUNIT_SSH"].startswith("ssh -F none -o IdentitiesOnly=yes -i ")
    assert env["GPUNIT_SSH"].endswith(" root@203.0.113.7 -p 40022")


@pytest.mark.spec("cli:exits:stdout-is-the-commands")
def test_stdout_carries_only_the_commands_output(
    cwd: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    assert gpunit(["run", "--", "echo", "hello"], provider=FakeProvider()) == 0
    out, err = capfd.readouterr()
    assert out == "hello\n"
    assert "session up" in err


@pytest.mark.spec("run:teardown:on-exit")
def test_the_commands_exit_tears_down(cwd: Path) -> None:
    provider = FakeProvider()

    assert gpunit(["run", "--", "true"], provider=provider) == 0
    assert provider.named("delete") == [("pod-1",)]
    assert not (cwd / ".gpunit" / "pod").exists()


@pytest.mark.spec("run:teardown:on-exit")
def test_a_lost_create_tears_down_and_exits_3(cwd: Path) -> None:
    provider = FakeProvider(
        creates=[Lost("create got no answer")], listings=[[], [("pod-1", "RUNNING")]]
    )

    assert gpunit(["run", "--", "true"], provider=provider) == 3
    assert provider.named("delete") == [("pod-1",)]
    assert not (cwd / ".gpunit" / "pending").exists()


@pytest.mark.spec("run:teardown:code-passed")
def test_the_commands_failure_is_passed_through(cwd: Path) -> None:
    provider = FakeProvider()

    assert gpunit(["run", "--", "sh", "-c", "exit 7"], provider=provider) == 7
    assert provider.named("delete") == [("pod-1",)]


@pytest.mark.spec("run:teardown:signalled-command")
def test_a_command_killed_by_a_signal_exits_128_plus_n(cwd: Path) -> None:
    provider = FakeProvider()

    assert gpunit(["run", "--", "bash", "-c", "kill -9 $$"], provider=provider) == 137
    assert provider.named("delete") == [("pod-1",)]


@pytest.mark.spec("run:teardown:interrupt")
@pytest.mark.parametrize(
    ("number", "code"),
    [(signal.SIGINT, 130), (signal.SIGTERM, 143), (signal.SIGHUP, 129)],
    ids=["SIGINT", "SIGTERM", "SIGHUP"],
)
def test_an_interrupt_tears_down_once(
    number: signal.Signals, code: int, cwd: Path
) -> None:
    provider = InterruptingProvider(number)
    before = signal.getsignal(number)
    command = [
        "bash",
        "-c",
        f"kill -{number.name.removeprefix('SIG')} $PPID; exec sleep 30",
    ]

    assert gpunit(["run", "--", *command], provider=provider) == code
    assert provider.named("delete") == [("pod-1",)]
    assert not (cwd / ".gpunit" / "pod").exists()
    assert signal.getsignal(number) == before


@pytest.mark.spec("run:teardown:failure-is-1")
def test_a_failed_teardown_is_exit_1(cwd: Path) -> None:
    provider = FakeProvider(deletes={"pod-1": 404})

    assert gpunit(["run", "--", "true"], provider=provider) == 1
    assert (cwd / ".gpunit" / "pod").exists()


@pytest.mark.spec("run:teardown:failure-is-1")
def test_an_interrupt_with_a_failed_teardown_is_exit_1(cwd: Path) -> None:
    # 130 would read as "interrupted and torn down" while the pod may still bill.
    provider = FakeProvider(deletes={"pod-1": 404})
    command = ["bash", "-c", "kill -INT $PPID; exec sleep 30"]

    assert gpunit(["run", "--", *command], provider=provider) == 1
    assert provider.named("delete") == [("pod-1",)]
    assert (cwd / ".gpunit" / "pod").exists()


@pytest.mark.spec("run:tunnel:reopened")
@pytest.mark.spec("session:ssh:own-config-only")
def test_a_dead_tunnel_is_reopened(
    cwd: Path,
    free_port: int,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    with_port(cwd, free_port)
    tunnels = cwd / "tunnels.log"
    monkeypatch.setenv("GPUNIT_TEST_SSH_LOG", str(tunnels))
    monkeypatch.setenv("GPUNIT_TEST_SSH_EXIT", "1")
    monkeypatch.setattr(run, "TUNNEL_POLL_S", 0.1)
    monkeypatch.setattr(run, "REOPEN_FIRST_S", 0.1)

    # Runs until the tunnel has been opened twice.
    reopened = f'until [ "$(wc -l < "{tunnels}")" -ge 2 ]; do sleep 0.05; done'
    command = ["bash", "-c", reopened]

    assert gpunit(["run", "--", *command], provider=FakeProvider()) == 0
    opened = tunnels.read_text(encoding="utf-8").splitlines()
    assert len(opened) >= 2
    assert f"-L{free_port}:localhost:8188" in opened[0]
    assert "ExitOnForwardFailure=yes" in opened[0]
    assert "-F none" in opened[0]
    assert "IdentitiesOnly=yes" in opened[0]
    assert "reopening it in 0.1s" in capfd.readouterr().err


@pytest.mark.spec("run:tunnel:backoff")
def test_a_tunnel_that_keeps_dying_backs_off() -> None:
    backoff = run._Backoff(now=0.0)
    now, waits = 0.0, []
    for _ in range(7):
        wait = backoff.exited(now)
        assert wait is not None and backoff.exited(now) is None
        waits.append(wait)
        assert not backoff.due(now + waits[-1] - 0.01)
        now += waits[-1]
        assert backoff.due(now)
        backoff.opened(now)

    assert waits == [1, 2, 4, 8, 16, 30, 30]
    assert backoff.exited(now + 30) == 1


@pytest.mark.spec("run:ports:busy-refuses")
def test_a_busy_port_refuses_before_any_request(
    cwd: Path, listening: int, capfd: pytest.CaptureFixture[str]
) -> None:
    with_port(cwd, listening)

    assert gpunit(["run", "--", "true"], provider=NO_REQUESTS) == 1
    assert f"local port {listening} already answers" in capfd.readouterr().err


@pytest.mark.spec("session:key:fresh-per-session")
@pytest.mark.parametrize(("ignored", "warned"), [(False, True), (True, False)])
def test_up_warns_when_the_key_directory_is_not_ignored(
    ignored: bool, warned: bool, cwd: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    subprocess.run(["git", "init", "-q"], cwd=cwd, check=True)
    if ignored:
        (cwd / ".gitignore").write_text(".gpunit/\n", encoding="utf-8")

    assert gpunit(["up"], provider=FakeProvider()) == 0
    assert ("is not gitignored" in capfd.readouterr().err) is warned
