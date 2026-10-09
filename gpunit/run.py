"""Run one command against a session that lives only as long as the command does."""

import os
import shlex
import signal
import subprocess
from collections.abc import Generator
from contextlib import contextmanager

from gpunit import library, log
from gpunit.provider import Lost, Provider
from gpunit.spec import Spec
from gpunit.state import State

LOST_EXIT = 3


def run(spec: Spec, provider: Provider, state: State, command: list[str]) -> int:
    """Open the session, run `command` with it, tear it down; return the exit code.

    e.g. the command's code, 128 + n when a signal n killed it; 1 when the teardown
    failed, even after a signal; 3 after a lost create; 128 + the signal's number
    after a signal and a teardown.
    """
    try:
        with library._open(spec, provider, state, None) as opened:
            return _command(spec, opened, command)
    except log.Refusal:
        return 1
    except Lost:
        return LOST_EXIT
    except library.TeardownFailed as failed:
        # A failed teardown outranks the signal: 128 + n says the pod is gone.
        return LOST_EXIT if isinstance(failed.__cause__, Lost) else 1
    except library.Interrupted as interrupted:
        return 128 + interrupted.signal


def _command(spec: Spec, opened: library.Session, command: list[str]) -> int:
    env = os.environ | {
        "GPUNIT_HOST": opened.host,
        "GPUNIT_SSH": shlex.join(opened.ssh),
    }
    env |= {
        f"GPUNIT_PORT_{port.remote}": str(opened.port(port.remote))
        for port in spec.ports
    }
    child: subprocess.Popen[bytes] | None = None
    try:
        with _held(library.SIGNALS):
            try:
                child = subprocess.Popen(command, env=env)
            except OSError as fault:
                log.say(f"the command could not start: {fault}")
                return 127
        code = child.wait()
    except library.Interrupted:
        if child is not None:
            child.terminate()
            child.wait()
        raise
    # Popen reads a death by signal n as -n; a shell says 128 + n.
    return 128 - code if code < 0 else code


@contextmanager
def _held(numbers: tuple[int, ...]) -> Generator[None, None, None]:
    """Hold the signals while the command starts, then deliver the first that came.

    A signal raising inside `Popen`, after the fork, would lose the command's handle
    and leave it running.
    """
    held: list[int] = []
    saved = {
        number: signal.signal(number, lambda number, _: held.append(number))
        for number in numbers
    }
    try:
        yield
    finally:
        for number, handler in saved.items():
            signal.signal(number, handler)
        if held:
            signal.raise_signal(held[0])
