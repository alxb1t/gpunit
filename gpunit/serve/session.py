"""Serve a row on a gpunit session: agree the price, open, wait for the model."""

import http.client
import secrets
import urllib.request
from collections.abc import Callable
from decimal import ROUND_UP, Decimal
from pathlib import Path

from gpunit import library, lifecycle, log
from gpunit.provider import Lost, Provider, Unknown
from gpunit.run import outcome
from gpunit.serve import chat, table
from gpunit.spec import Spec
from gpunit.state import State

WAIT_S = 1200
POLL_S = 5
PROGRESS_S = 30
REQUEST_S = 5
LOG_TAIL = 50
HOLD_S = 30
# Two missed polls: a pod the ceiling stopped answers nothing again.
QUIET_S = 60


def home(name: str) -> Path:
    """Return the directory a model's session files live under, from any directory.

    e.g. "qwen3-4b" → ~/.local/state/gpunit/serve/qwen3-4b
    """
    return Path.home() / ".local" / "state" / "gpunit" / "serve" / name


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
    spec = row.spec(ceiling_s, volume, max_hourly, key)
    # No proxy: the endpoint is the tunnel's loopback side.
    opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def body() -> int:
        _agree(spec, provider, yes, ask)
        place = home(name)
        place.mkdir(mode=0o700, parents=True, exist_ok=True)
        with library._open(spec, provider, State(place), None) as opened:
            base = f"http://127.0.0.1:{opened.port(table.PORT)}/v1"
            _wait(base, key, opened.pod_id, provider, opener)
            log.say(f"{row.served} answers on {base}")
            if api:
                _hold(base, key, opener)
            else:
                chat.run(base, key, row.served, think, read, opener=opener)
        return 0

    return outcome(body)


def down(name: str, provider: Provider) -> int:
    """Tear down the session `serve` left for `name`; return 0, or 1 on a fault."""
    spec = table.load().models[name].spec(0, None, None, "")
    return lifecycle.down(spec, provider, State(home(name)))


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
    # Up to the cent: the figure agreed is never under the most it can cost.
    most = (max(prices) * spec.ceiling_s / 3600).quantize(Decimal("0.01"), ROUND_UP)
    log.say(f"at most ${most} for {spec.ceiling_s}s")
    if yes:
        return
    try:
        answer = ask(f"rent {spec.project} for at most ${most}? [y/N] ")
    except EOFError:
        answer = ""
    if answer.strip().lower() not in ("y", "yes"):
        log.refuse("not rented")


def _wait(
    base: str,
    key: str,
    pod_id: str,
    provider: Provider,
    opener: urllib.request.OpenerDirector,
) -> None:
    clock = lifecycle.CLOCK
    start = clock.monotonic()
    progress = start + PROGRESS_S
    while not _answers(base, key, opener):
        now = clock.monotonic()
        if now - start >= WAIT_S:
            log.refuse(f"the model did not load within {WAIT_S}s")
        if now >= progress:
            lines = provider.log(pod_id, tail=LOG_TAIL)
            if lines:
                log.say(f"loading: {lines[-1]}")
            progress = now + PROGRESS_S
        clock.sleep(POLL_S)


def _hold(base: str, key: str, opener: urllib.request.OpenerDirector) -> None:
    print(f"OPENAI_BASE_URL={base}", flush=True)
    print(f"OPENAI_API_KEY={key}", flush=True)
    log.say("serving until interrupted or the ceiling; Ctrl-C ends the session")
    clock = lifecycle.CLOCK
    answered = clock.monotonic()
    while True:
        clock.sleep(HOLD_S)
        now = clock.monotonic()
        if _answers(base, key, opener):
            answered = now
        elif now - answered >= QUIET_S:
            log.refuse(f"the model has not answered for {QUIET_S}s")


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
