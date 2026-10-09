"""Open a GPU session from Python: one `with` block, torn down on every way out."""

import os
import signal
import socket
import subprocess
import threading
import time
from collections.abc import Callable, Generator, Mapping, Sequence
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field
from pathlib import Path
from types import FrameType

from gpunit import lifecycle, log
from gpunit.provider import Lost, Provider
from gpunit.runpod import RunPod
from gpunit.spec import Spec, load_spec
from gpunit.state import Record, State

SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
TUNNEL_POLL_S = 1.0
# A tunnel that cannot bind dies at once; each reopening waits longer (0002 design D8).
REOPEN_FIRST_S = 1.0
REOPEN_CAP_S = 30.0

Refused = log.Refusal


class TeardownFailed(Exception):
    """The teardown failed: the pod may still bill, and `.gpunit/pod` is kept."""


class Interrupted(KeyboardInterrupt):
    """A signal ended the block; `signal` is its number."""

    def __init__(self, signal: int) -> None:
        """Name the signal that arrived."""
        super().__init__(signal)
        self.signal = signal


@dataclass(frozen=True)
class Session:
    """The open session: where the pod is, and how to reach it."""

    host: str
    pod_id: str
    image: str
    ssh: tuple[str, ...]
    _ports: Mapping[int, int] = field(repr=False)

    def port(self, remote: int) -> int:
        """Return the local port `remote` is forwarded to; refuse one not forwarded."""
        if remote not in self._ports:
            log.refuse(f"port {remote} is not in the spec's ports")
        return self._ports[remote]


@contextmanager
def session(
    spec: str | Path | Spec,
    *,
    environ: Mapping[str, str] | None = None,
    cwd: Path | None = None,
    say: Callable[[str], None] | None = None,
) -> Generator[Session, None, None]:
    """Open a session on `spec` for the block's life; tear it down when it ends.

    Raise `Refused`, `Lost`, `TeardownFailed` or `Interrupted` (0004 design D2).
    """
    with _saying(say):
        loaded = spec if isinstance(spec, Spec) else load_spec(Path(spec))
        provider = RunPod(environ if environ is not None else os.environ)
    with _open(loaded, provider, State(cwd or Path.cwd()), say) as opened:
        yield opened


@contextmanager
def _open(
    spec: Spec,
    provider: Provider,
    state: State,
    say: Callable[[str], None] | None,
) -> Generator[Session, None, None]:
    with _saying(say):
        # `signal.signal` raises off the main thread.
        if threading.current_thread() is not threading.main_thread():
            log.refuse("a session opens on the main thread, which owns the signals")
        _refuse_busy_ports(spec)
        signals = _Signals()
        teardown, lost = True, False
        tunnel: _Tunnel | None = None
        ended: BaseException | None = None
        try:
            try:
                record = lifecycle.up(spec, provider, state)
            except log.Refusal:
                # `up` tore down what it made; a refusal before the create made none.
                teardown = False
                raise
            except Lost:
                lost = True
                raise
            opened = _session(spec, state, record)
            if spec.ports:
                tunnel = _Tunnel(_tunnel_argv(spec, opened.ssh))
            yield opened
        except BaseException as fault:
            ended = fault
            raise
        finally:
            # First, so no signal lands between the block's end and the delete.
            signals.shield()
            try:
                if tunnel is not None:
                    tunnel.stop()
                # The sweep deletes every listed pod: before this session's create,
                # those are not ours, and an earlier session's record or marker does
                # not make them so.
                if teardown and (lost or state.began):
                    if lifecycle.down(spec, provider, state) != 0:
                        raise TeardownFailed(
                            "the teardown failed; run gpunit down"
                        ) from ended
                elif teardown:
                    log.say("no create began; nothing to tear down")
            finally:
                signals.restore()


def _session(spec: Spec, state: State, record: Record) -> Session:
    return Session(
        host=str(record.host),
        pod_id=record.id,
        image=record.image,
        ssh=tuple(lifecycle.ssh_command(state, record)),
        _ports={port.remote: port.local for port in spec.ports},
    )


@contextmanager
def _saying(say: Callable[[str], None] | None) -> Generator[None, None, None]:
    with log.redirect(say) if say is not None else nullcontext():
        yield


class _Signals:
    """SIGINT, SIGTERM and SIGHUP raise `Interrupted` once, until the teardown."""

    def __init__(self) -> None:
        """Save the caller's handlers and set ours."""
        self._fired = False
        self._saved = {
            number: signal.signal(number, self._handle) for number in SIGNALS
        }

    def _handle(self, number: int, frame: FrameType | None) -> None:
        if self._fired:
            return
        self._fired = True
        raise Interrupted(number)

    def shield(self) -> None:
        """Ignore all three, so no signal cuts the teardown short."""
        for number in SIGNALS:
            signal.signal(number, signal.SIG_IGN)

    def restore(self) -> None:
        """Set the caller's handlers back."""
        for number, handler in self._saved.items():
            signal.signal(number, handler)


class _Tunnel:
    """The `ssh -N -L` child, watched by a thread that reopens it when it exits."""

    def __init__(self, argv: list[str]) -> None:
        """Open the tunnel and start watching it."""
        self._argv = argv
        self._child = self._open()
        self._stopped = threading.Event()
        self._thread = threading.Thread(target=self._watch, daemon=True)
        self._thread.start()

    def _watch(self) -> None:
        backoff = _Backoff(time.monotonic())
        while not self._stopped.wait(TUNNEL_POLL_S):
            if self._child.poll() is None:
                continue
            now = time.monotonic()
            wait = backoff.exited(now)
            if wait is not None:
                returncode = self._child.returncode
                log.say(f"the tunnel exited ({returncode}); reopening it in {wait:g}s")
            if backoff.due(now):
                self._child = self._open()
                backoff.opened(now)

    def _open(self) -> subprocess.Popen[bytes]:
        # stdout belongs to the command alone.
        return subprocess.Popen(
            self._argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL
        )

    def stop(self) -> None:
        """Stop watching, then end the child the watcher left."""
        self._stopped.set()
        self._thread.join()
        _kill(self._child)


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


def _tunnel_argv(spec: Spec, ssh: Sequence[str]) -> list[str]:
    forwards = [f"-L{port.local}:localhost:{port.remote}" for port in spec.ports]
    options = ["-N", "-o", "ExitOnForwardFailure=yes", "-o", "BatchMode=yes"]
    return [ssh[0], *options, *forwards, *ssh[1:]]


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
