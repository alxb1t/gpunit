"""Write gpunit's own lines to stderr, each opening with the UTC time."""

import sys
import time
from typing import NoReturn


class Refusal(Exception):
    """A verb refused; `cli` turns it into exit 1."""


def utc() -> str:
    """Return the UTC time now, e.g. "2026-10-07T15:32:09Z"."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def say(text: str) -> None:
    """Write one line, `<UTC> <text>`, to stderr."""
    print(f"{utc()} {text}", file=sys.stderr, flush=True)


def refuse(text: str) -> NoReturn:
    """Write `<UTC> refused: <text>` to stderr and raise `Refusal`."""
    say(f"refused: {text}")
    raise Refusal(text)
