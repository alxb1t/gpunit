"""Write gpunit's own lines, each opening with the UTC time, to stderr or a sink."""

import sys
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import NoReturn


class Refusal(Exception):
    """A verb refused; `cli` turns it into exit 1."""


def utc() -> str:
    """Return the UTC time now, e.g. "2026-10-07T15:32:09Z"."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _stderr(line: str) -> None:
    # A dead pipe or a closed stream ends no teardown (0004 design D5).
    try:
        print(line, file=sys.stderr, flush=True)
    except (BrokenPipeError, ValueError):
        pass


_sink: Callable[[str], None] = _stderr


@contextmanager
def redirect(sink: Callable[[str], None]) -> Generator[None, None, None]:
    """Send every line to `sink` for the block's life, then restore the previous."""
    global _sink
    previous, _sink = _sink, sink
    try:
        yield
    finally:
        _sink = previous


def say(text: str) -> None:
    """Write one line, `<UTC> <text>`, to the sink."""
    _sink(f"{utc()} {text}")


def refuse(text: str) -> NoReturn:
    """Write `<UTC> refused: <text>` to the sink and raise `Refusal`."""
    say(f"refused: {text}")
    raise Refusal(text)
