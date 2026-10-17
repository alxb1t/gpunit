"""The live scripts' shared steps: gpunit's argv, the price, the verdict, the window.

e.g. `window(gpunit("volume", "up", …), gpunit("volume", "down", …), body, run)`
runs `up`, then `body`, then `down`; why each live run holds one: 0010 design D10.
"""

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

LIVE = Path(__file__).parent
# A row's window outlasts each session in it: at most 30m and the 1200s wait for SSH.
SERVE_VOLUME_CEILING = "1h"


def gpunit(*args: str) -> list[str]:
    """Return the argv that runs gpunit with `args` under this Python."""
    return [sys.executable, "-m", "gpunit", *args]


def run(argv: list[str]) -> int:
    """Run `argv`, its output on this terminal, and return its exit code."""
    return subprocess.run(argv).returncode


def price(spec: str) -> int:
    """Print each card's hourly price and the most the run can cost; return the code."""
    return run([sys.executable, str(LIVE / "price.py"), spec])


def report(failures: list[str]) -> int:
    """Print each of `check`'s failures to stderr; return 1 when there are any."""
    for failure in failures:
        print(f"check failed: {failure}", file=sys.stderr)
    return 1 if failures else 0


def serve_volume_up(model: str) -> list[str]:
    """Return the argv that opens, or extends, the row's window volume."""
    return gpunit(
        "volume", "up", "--serve", model, "--ceiling", SERVE_VOLUME_CEILING, "--yes"
    )


def window(
    up: list[str],
    down: list[str],
    body: Callable[[], int],
    run: Callable[[list[str]], int] = run,
) -> int:
    """Run `up`, `body` once `up` exits 0, then `down`; return the first failure's code.

    A failed `down` makes the result 1; an exception in `body` still reaches `down`.
    """
    try:
        code = run(up)
        if code == 0:
            code = body()
    finally:
        # The volume bills until its delete: a failed one must fail the run.
        if run(down) != 0:
            code = 1
    return code


def serve_window(model: str, body: Callable[[], int]) -> int:
    """Run `body` inside the row's window volume, deleted however it ends."""
    return window(
        serve_volume_up(model), gpunit("volume", "down", "--serve", model), body
    )
