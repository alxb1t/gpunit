"""Run one command against a session that lives only as long as the command does."""

import os
import shlex
import signal
import socket
import subprocess
from types import FrameType

from gpunit import log, session
from gpunit.provider import Lost, Provider
from gpunit.spec import Spec
from gpunit.state import Record, State

LOST_EXIT = 3
SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
TUNNEL_POLL_S = 1.0


class _Interrupted(Exception):
    """A signal arrived while the session was opening."""


class _Children:
    """The command and the tunnel, and the first signal that arrived."""

    def __init__(self) -> None:
        """Start with neither child and no signal."""
        self.command: subprocess.Popen[bytes] | None = None
        self.tunnel: subprocess.Popen[bytes] | None = None
        self.signal: int | None = None
        self.opening = True

    def handle(self, number: int, frame: FrameType | None) -> None:
        """Stop the command on the first signal; ignore every later one."""
        if self.signal is not None:
            return
        self.signal = number
        if self.command is not None:
            self.command.terminate()
        elif self.opening:
            raise _Interrupted


def run(spec: Spec, provider: Provider, state: State, command: list[str]) -> int:
    """Open the session, run `command` with it, tear it down; return the exit code.

    e.g. the command's code; 1 when the teardown failed, even after a signal; 3 after
    a lost create; 128 + the signal's number after a signal and a teardown.
    """
    _refuse_busy_ports(spec)
    children = _Children()
    previous = {number: signal.signal(number, children.handle) for number in SIGNALS}
    try:
        return _run(spec, provider, state, command, children)
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


def _run(
    spec: Spec,
    provider: Provider,
    state: State,
    command: list[str],
    children: _Children,
) -> int:
    code, teardown, torn_down = 1, True, False
    # One handler for the whole run: a signal raised while opening, even just after
    # `up` returned, still reaches the teardown below.
    try:
        record = session.up(spec, provider, state)
        children.opening = False
        if children.signal is None:
            code = _supervise(spec, state, record, command, children)
    except log.Refusal:
        # `up` tore down whatever it had made; a refusal before the create made nothing.
        teardown = False
        raise
    except Lost:
        code = LOST_EXIT
    except _Interrupted:
        pass
    finally:
        children.opening = False
        if teardown:
            if children.tunnel is not None:
                _kill(children.tunnel)
            torn_down = session.down(spec, provider, state) == 0
    # A failed teardown outranks the signal: 128 + n says the pod is gone.
    if not torn_down:
        return LOST_EXIT if code == LOST_EXIT else 1
    if children.signal is not None:
        return 128 + children.signal
    return code


def _supervise(
    spec: Spec, state: State, record: Record, command: list[str], children: _Children
) -> int:
    if spec.ports:
        children.tunnel = _tunnel(spec, state, record)
    env = os.environ | {
        "GPUNIT_HOST": str(record.host),
        "GPUNIT_SSH": shlex.join(session.ssh_command(state, record)),
    }
    env |= {f"GPUNIT_PORT_{port.remote}": str(port.local) for port in spec.ports}
    try:
        children.command = subprocess.Popen(command, env=env)
    except OSError as fault:
        log.say(f"the command could not start: {fault}")
        return 127
    if children.signal is not None:  # arrived before the command existed
        children.command.terminate()
    while True:
        try:
            return children.command.wait(timeout=TUNNEL_POLL_S)
        except subprocess.TimeoutExpired:
            pass
        if children.tunnel is not None and children.tunnel.poll() is not None:
            log.say(f"the tunnel exited ({children.tunnel.returncode}); reopening it")
            children.tunnel = _tunnel(spec, state, record)


def _tunnel(spec: Spec, state: State, record: Record) -> subprocess.Popen[bytes]:
    ssh = session.ssh_command(state, record)
    forwards = [f"-L{port.local}:localhost:{port.remote}" for port in spec.ports]
    options = ["-N", "-o", "ExitOnForwardFailure=yes", "-o", "BatchMode=yes"]
    # stdout belongs to the command alone.
    return subprocess.Popen(
        [ssh[0], *options, *forwards, *ssh[1:]],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )


def _kill(child: subprocess.Popen[bytes]) -> None:
    child.terminate()
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait()


def _refuse_busy_ports(spec: Spec) -> None:
    for port in spec.ports:
        try:
            with socket.create_connection(("127.0.0.1", port.local), timeout=0.5):
                pass
        except OSError:
            continue
        log.refuse(
            f"local port {port.local} already answers; free it, or set its local side"
        )
