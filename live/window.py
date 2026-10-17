"""Hold a window volume around a live run, and delete it however the run ends.

e.g. `window(gpunit("volume", "up", …), gpunit("volume", "down", …), body, run)`
runs `up`, then `body`, then `down`; why each live run holds one: 0010 design D10.
"""

import subprocess
import sys
from collections.abc import Callable


def gpunit(*args: str) -> list[str]:
    """Return the argv that runs gpunit with `args` under this Python."""
    return [sys.executable, "-m", "gpunit", *args]


def run(argv: list[str]) -> int:
    """Run `argv`, its output on this terminal, and return its exit code."""
    return subprocess.run(argv).returncode


def window(
    up: list[str],
    down: list[str],
    body: Callable[[], int],
    run: Callable[[list[str]], int] = run,
) -> int:
    """Run `up`, `body` once `up` exits 0, then `down`; return the first failure's code.

    A failed `down` makes the result 1; an exception in `body` still reaches `down`.
    """
    code = 1
    try:
        code = run(up)
        if code == 0:
            code = body()
    finally:
        # The volume bills until its delete: a failed one must fail the run.
        if run(down) != 0:
            code = 1
    return code
