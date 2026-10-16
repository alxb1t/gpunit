"""Serve a row on a gpunit session: agree the price, open, wait for the model."""

import http.client
import os
import secrets
import socket
import sys
import urllib.request
from collections.abc import Callable
from dataclasses import replace
from decimal import ROUND_UP, Decimal
from pathlib import Path
from typing import NoReturn

from gpunit import library, lifecycle, log, volume
from gpunit.provider import Lost, Provider, Unknown
from gpunit.run import outcome
from gpunit.serve import chat, table
from gpunit.spec import Spec
from gpunit.state import State, home_state

WAIT_S = table.WAIT_S
POLL_S = 5
PROGRESS_S = 30
REQUEST_S = 5
LOG_TAIL = 50
HOLD_S = 30
# Two missed polls: a pod the ceiling stopped answers nothing again.
QUIET_S = 60
KEEP_TAIL = 30


def home(name: str) -> Path:
    """Return the directory a model's session files live under, from any directory.

    e.g. "qwen3-4b" → ~/.local/state/gpunit/serve/qwen3-4b
    """
    return home_state() / "serve" / name


def serve(
    name: str,
    ceiling_s: int,
    *,
    api: bool,
    volume: str | None,
    max_hourly: float | None,
    yes: bool,
    think: bool,
    provider: Provider,
    ask: Callable[[str], str] = input,
    read: Callable[[str], str] | None = None,
    opener: urllib.request.OpenerDirector | None = None,
) -> int:
    """Serve `name` until the session ends; return the exit code `gpunit run` would."""
    row = table.load().models[name]
    key = secrets.token_urlsafe(32)
    spec = row.spec(ceiling_s, volume, max_hourly, key, _free_port())
    if volume is None and State(home(name)).window() is not None:
        # `up` mounts the recorded window volume: 0010 design D6, D8.
        spec = replace(spec, volume_gb=row.disk_gb)
    # No proxy: the endpoint is the tunnel's loopback side.
    opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def body() -> int:
        _agree(spec, provider, yes, ask)
        place = home(name)
        place.mkdir(mode=0o700, parents=True, exist_ok=True)
        state = State(place)
        kept: _Kept | None = None
        try:
            with library._open(spec, provider, state, None) as opened:
                # After `up`'s guards: a run refused before its create keeps the
                # last session's file.
                kept = _Kept(place / "pod.log")
                record = state.read()
                created = record.created if record else None
                base = f"http://127.0.0.1:{opened.port(table.PORT)}/v1"
                _wait(base, key, opened.pod_id, provider, opener, created, kept)
                log.say(f"{row.served} answers on {base}")
                if api:
                    _hold(base, key, opened.pod_id, provider, opener, created, kept)
                else:
                    chat.run(base, key, row.served, think, read, opener=opener)
        finally:
            # A pod was created and refused before the session opened: the last
            # session's file is not its log.
            if kept is None and state.began:
                (place / "pod.log").unlink(missing_ok=True)
        return 0

    return outcome(body)


def down(name: str, provider: Provider) -> int:
    """Tear down the session `serve` left for `name`; return 0, or 1 on a fault."""
    spec = table.load().models[name].spec(0, None, None, "", table.PORT)
    return lifecycle.down(spec, provider, State(home(name)))


def volume_up(name: str, ceiling_s: int, *, yes: bool, provider: Provider) -> int:
    """Make or extend the window volume `serve` mounts for `name`, of its row's disk."""
    place = home(name)
    place.mkdir(mode=0o700, parents=True, exist_ok=True)
    return volume.up(_window_spec(name, ceiling_s), provider, State(place), yes=yes)


def volume_down(name: str, provider: Provider) -> int:
    """Delete the window volume `volume_up` made for `name`; return 0, or 1."""
    return volume.down(_window_spec(name, 0), provider, State(home(name)))


def _window_spec(name: str, ceiling_s: int) -> Spec:
    row = table.load().models[name]
    spec = row.spec(0, None, None, "", table.PORT)
    return replace(spec, volume_gb=row.disk_gb, volume_ceiling_s=ceiling_s)


def most_cost(hourly: Decimal, spec: Spec) -> Decimal:
    """Return the most `spec` can cost at `hourly` dollars an hour, up to the cent.

    e.g. $0.69/h, a 1800s ceiling and a 1200s wait → Decimal("0.58")
    """
    # Up to the cent: the figure agreed is never under the most it can cost. The pod
    # bills while it pulls, and boot arms the ceiling only after: count the SSH wait.
    billed_s = spec.ceiling_s + spec.timeout_s
    return (hourly * billed_s / 3600).quantize(Decimal("0.01"), ROUND_UP)


def _free_port() -> int:
    # Picked before the price, so a busy local port is never refused after a yes.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _agree(
    spec: Spec, provider: Provider, yes: bool, ask: Callable[[str], str]
) -> None:
    prices: list[Decimal] = []
    for card in spec.gpus:
        try:
            info = provider.gpu(card)
        except Unknown:
            log.refuse(f"the table names {card!r}, which the catalogue does not know")
        except Lost as fault:
            log.refuse(f"the catalogue could not be read for {card!r}: {fault}")
        if info.vram_gb < spec.vram_gb:
            continue
        if spec.max_hourly is not None and info.hourly > spec.max_hourly:
            continue
        log.say(f"price: {card} ${info.hourly}/h")
        prices.append(Decimal(str(info.hourly)))
    if not prices:
        log.refuse("no card in the table meets its vram_gb and max_hourly")
    most = most_cost(max(prices), spec)
    log.say(
        f"at most ${most} for {spec.ceiling_s}s and a {spec.timeout_s}s wait for SSH"
    )
    if yes:
        return
    try:
        answer = ask(f"rent {spec.project} for at most ${most}? [y/N] ")
    except EOFError:
        answer = ""
    except KeyboardInterrupt:
        # Ends the prompt's line, so the next line opens at its start.
        print(file=sys.stderr, flush=True)
        log.say("not rented")
        raise
    if answer.strip().lower() not in ("y", "yes"):
        log.refuse("not rented")


class _Kept:
    """The pod's log on the laptop: the longest read since the create."""

    def __init__(self, path: Path) -> None:
        """Hold nothing: remove the last session's file at `path`."""
        self.path = path
        self._count = 0
        path.unlink(missing_ok=True)

    def take(self, lines: list[str]) -> None:
        """Write `lines` when they are at least as many as held; else keep the file."""
        # A read cut by its time bound is shorter, and holds less: 0009 design D2.
        if not lines or len(lines) < self._count:
            return
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as kept:
            kept.writelines(f"{line}\n" for line in lines)
        self._count = len(lines)

    def tail(self, n: int) -> list[str]:
        """Return the file's last `n` lines; none when nothing was kept."""
        if not self.path.exists():
            return []
        return self.path.read_text(encoding="utf-8").splitlines()[-n:]


def _wait(
    base: str,
    key: str,
    pod_id: str,
    provider: Provider,
    opener: urllib.request.OpenerDirector,
    created: str | None,
    kept: _Kept,
) -> None:
    clock = lifecycle.CLOCK
    start = clock.monotonic()
    progress = start + PROGRESS_S
    dead = lifecycle.DeadPod()
    while not _answers(base, key, opener):
        now = clock.monotonic()
        if now - start >= WAIT_S:
            log.refuse(f"the model did not load within {WAIT_S}s")
        if now >= progress:
            lines = provider.log(pod_id, tail=LOG_TAIL, since=created)
            kept.take(lines)
            if lines:
                log.say(f"loading: {lines[-1]}")
            progress = now + PROGRESS_S
        if dead.seen(provider.get(pod_id)):
            _stopped(kept, "the pod stopped while the model loaded")
        clock.sleep(POLL_S)


def _hold(
    base: str,
    key: str,
    pod_id: str,
    provider: Provider,
    opener: urllib.request.OpenerDirector,
    created: str | None,
    kept: _Kept,
) -> None:
    print(f"OPENAI_BASE_URL={base}", flush=True)
    print(f"OPENAI_API_KEY={key}", flush=True)
    log.say("serving until interrupted or the ceiling; Ctrl-C ends the session")
    clock = lifecycle.CLOCK
    answered = clock.monotonic()
    dead = lifecycle.DeadPod()
    while True:
        clock.sleep(HOLD_S)
        now = clock.monotonic()
        kept.take(provider.log(pod_id, tail=LOG_TAIL, since=created))
        if dead.seen(provider.get(pod_id)):
            _stopped(kept, "the pod stopped while serving")
        if _answers(base, key, opener):
            answered = now
        elif now - answered >= QUIET_S:
            # A crash in the hold ends here: boot's grace keeps the pod RUNNING.
            _stopped(kept, f"the model has not answered for {QUIET_S}s")


def _stopped(kept: _Kept, reason: str) -> NoReturn:
    # The pod's own log is gone once it stops; the kept copy says why it did.
    for line in kept.tail(KEEP_TAIL):
        log.say(f"pod: {line}")
    log.say(f"the pod's log is kept at {kept.path}")
    log.refuse(reason)


def _answers(base: str, key: str, opener: urllib.request.OpenerDirector) -> bool:
    request = urllib.request.Request(
        f"{base}/models", headers={"Authorization": f"Bearer {key}"}
    )
    # Refused, reset or 503 while vLLM pulls, downloads and loads: all "not yet".
    try:
        with opener.open(request, timeout=REQUEST_S) as answer:
            return answer.status == 200
    except (OSError, http.client.HTTPException):
        return False
