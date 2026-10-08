"""Run one command against a session that lives only as long as the command does."""

import os
import shlex
import signal
import socket
import subprocess
import time
from types import FrameType

from gpunit import log, session
from gpunit.provider import Lost, Provider
from gpunit.spec import Spec
from gpunit.state import Record, State

LOST_EXIT = 3
SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
TUNNEL_POLL_S = 1.0
# A tunnel that cannot bind dies at once; each reopening waits longer (0002 design D8).
REOPEN_FIRST_S = 1.0
REOPEN_CAP_S = 30.0


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


class _Backoff:
    """When a dead tunnel may reopen: the wait doubles, and resets after one lived."""

    def __init__(self, now: float) -> None:
        """Start with the first wait, the tunnel opened at `now`."""
        self.wait = REOPEN_FIRST_S
        self.opened_at = now
        self.reopen_at: float | None = None

    def exited(self, now: float) -> float | None:
        """Schedule a dead tunnel's reopening once; return its wait, else None."""
        if self.reopen_at is not None:
            return None
        if now - self.opened_at >= REOPEN_CAP_S:
            self.wait = REOPEN_FIRST_S
        wait = self.wait
        self.reopen_at = now + wait
        self.wait = min(wait * 2, REOPEN_CAP_S)
        return wait

    def due(self, now: float) -> bool:
        """Return whether the scheduled reopening is due at `now`."""
        return self.reopen_at is not None and now >= self.reopen_at

    def opened(self, now: float) -> None:
        """Record a tunnel reopened at `now`."""
        self.opened_at = now
        self.reopen_at = None


def run(spec: Spec, provider: Provider, state: State, command: list[str]) -> int:
    """Open the session, run `command` with it, tear it down; return the exit code.

    e.g. the command's code, 128 + n when a signal n killed it; 1 when the teardown
    failed, even after a signal; 3 after a lost create; 128 + the signal's number
    after a signal and a teardown.
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
    code, teardown, failed, lost = 1, True, False, False
    # A record or marker already here is an earlier session's: `up` refuses beside it.
    earlier = state.pod.exists() or state.pending.exists()
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
        code, lost = LOST_EXIT, True
    except _Interrupted:
        pass
    finally:
        children.opening = False
        # The sweep deletes every listed pod: before a create, those are not ours.
        began = not earlier and (state.pod.exists() or state.pending.exists())
        if teardown and (lost or began):
            if children.tunnel is not None:
                _kill(children.tunnel)
            failed = session.down(spec, provider, state) != 0
        elif teardown:
            log.say("no create began; nothing to tear down")
    # A failed teardown outranks the signal: 128 + n says the pod is gone.
    if failed:
        return LOST_EXIT if code == LOST_EXIT else 1
    if children.signal is not None:
        return 128 + children.signal
    return code


def _supervise(
    spec: Spec, state: State, record: Record, command: list[str], children: _Children
) -> int:
    if spec.ports:
        children.tunnel = _tunnel(spec, state, record)
    backoff = _Backoff(time.monotonic())
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
            code = children.command.wait(timeout=TUNNEL_POLL_S)
            # Popen reads a death by signal n as -n; a shell says 128 + n.
            return 128 - code if code < 0 else code
        except subprocess.TimeoutExpired:
            pass
        if children.tunnel is None or children.tunnel.poll() is None:
            continue
        now = time.monotonic()
        wait = backoff.exited(now)
        if wait is not None:
            returncode = children.tunnel.returncode
            log.say(f"the tunnel exited ({returncode}); reopening it in {wait:g}s")
        if backoff.due(now):
            children.tunnel = _tunnel(spec, state, record)
            backoff.opened(now)


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
