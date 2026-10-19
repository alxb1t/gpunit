"""The live scripts' shared steps: gpunit's argv, the price, the verdict, the window.

e.g. `window(gpunit("volume", "up", …), gpunit("volume", "down", …), body, run)`
runs `up`, then `body`, then `down`; why each live run holds one: decision D6.
"""

import contextlib
import signal
import subprocess
import sys
from collections.abc import Callable, Generator
from pathlib import Path

LIVE = Path(__file__).parent
# A row's window outlasts each session in it: at most 30m and the 1200s wait for SSH.
SERVE_VOLUME_CEILING = "1h"


def gpunit(*args: str) -> list[str]:
    """Return the argv that runs gpunit with `args` under this Python."""
    return [sys.executable, "-m", "gpunit", *args]


def waited(child: subprocess.Popen[str]) -> int:
    """Wait for `child` to exit through every Ctrl-C; then re-raise the first one.

    The terminal sends gpunit the SIGINT too, and gpunit tears its own pod or volume
    down on it: `subprocess.run` would SIGKILL it 0.25s into that teardown.
    """
    interrupted: KeyboardInterrupt | None = None
    while True:
        try:
            code = child.wait()
            break
        except KeyboardInterrupt as error:
            interrupted = interrupted or error
    if interrupted is not None:
        raise interrupted
    return code


@contextlib.contextmanager
def hangups_interrupt() -> Generator[None]:
    """Make a SIGHUP or SIGTERM a Ctrl-C while held, so each `finally` still runs.

    Python's default for both ends the process at once, where a closed terminal or a
    kill would skip the teardown; the handlers before are put back on the way out.
    """
    hangups = (signal.SIGHUP, signal.SIGTERM)
    before = {s: signal.signal(s, signal.default_int_handler) for s in hangups}
    try:
        yield
    finally:
        for signum, handler in before.items():
            signal.signal(signum, handler)


def call(
    argv: list[str], input: str | None = None, capture: bool = False
) -> tuple[int, str]:
    """Run `argv` to its exit, fed `input`; return its code and its stdout if `capture`.

    A Ctrl-C never kills the child: it is waited on, then the Ctrl-C is re-raised.
    e.g. `call(gpunit("status"))` → (0, "")
    """
    child = subprocess.Popen(
        argv,
        stdin=None if input is None else subprocess.PIPE,
        stdout=subprocess.PIPE if capture else None,
        text=True,
    )
    try:
        out, _ = child.communicate(input)
    except KeyboardInterrupt:
        waited(child)
        raise
    return child.returncode, out or ""


def run(argv: list[str]) -> int:
    """Run `argv`, its output on this terminal, and return its exit code."""
    return call(argv)[0]


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

    A failed `down` makes the result 1; an exception in `body`, a SIGHUP or a SIGTERM
    still reaches `down`.
    """
    with hangups_interrupt():
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
