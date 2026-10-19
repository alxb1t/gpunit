"""Write gpunit's own lines, each opening with the UTC time, to stderr or a sink."""

import functools
import os
import sys
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import NoReturn


class Refusal(Exception):
    """A verb refused; `cli` turns it into exit 1."""


def utc(after_s: int = 0) -> str:
    """Return the UTC time `after_s` seconds from now, e.g. "2026-10-07T15:32:09Z"."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + after_s))


def _stderr(line: str) -> None:
    # A dead pipe or a closed stream ends no teardown (decision D4).
    try:
        print(line, file=sys.stderr, flush=True)
    except BrokenPipeError:
        # The line stays buffered, and the interpreter's last flush would fail on it
        # and exit 120: point the stream's descriptor at the null device instead.
        # A stream with no descriptor, or no null device to open, is only swallowed.
        try:
            null = os.open(os.devnull, os.O_WRONLY)
            try:
                os.dup2(null, sys.stderr.fileno())
            finally:
                os.close(null)
        except (OSError, ValueError, AttributeError):
            pass
    except ValueError:
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


_CONTROL = dict.fromkeys([*range(0x20), *range(0x7F, 0xA0)])


def clean(text: str, keep: str = "") -> str:
    r"""Return `text` without C0, DEL or C1 but `keep`, so it cannot steer the terminal.

    e.g. "\x1b]0;owned\x07loading\x1b[2J 50%" → "]0;ownedloading[2J 50%"
    """
    return text.translate(_drop(keep))


# Cached: the chat cleans each streamed part with the same `keep`.
@functools.cache
def _drop(keep: str) -> dict[int, None]:
    return {c: None for c in _CONTROL if chr(c) not in keep}


def say(text: str) -> None:
    """Write one line, `<UTC> <text>`, to the sink."""
    _sink(f"{utc()} {text}")


def refuse(text: str) -> NoReturn:
    """Write `<UTC> refused: <text>` to the sink and raise `Refusal`."""
    say(f"refused: {text}")
    raise Refusal(text)
