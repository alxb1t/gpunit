"""Write gpunit's own lines to stderr, each opening with the UTC time."""

import sys
import time
from typing import NoReturn


class Refusal(Exception):
    """A verb refused; `cli` turns it into exit 1."""


def say(text: str) -> None:
    """Write one line, `<UTC> <text>`, to stderr."""
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print(f"{stamp} {text}", file=sys.stderr, flush=True)


def refuse(text: str) -> NoReturn:
    """Write `<UTC> refused: <text>` to stderr and raise `Refusal`."""
    say(f"refused: {text}")
    raise Refusal(text)
