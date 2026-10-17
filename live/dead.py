"""Prove a container that exits at once ends `up`'s wait (0006 design D6).

e.g. `RUNPOD_API_KEY=<key> python live/dead.py` prints the price, boots the dead
image, deletes what `up` left, says how `up` exited and why, shows that no pod is
left, and exits 0 when `check` passes. RunPod may restart the container, so the
reason can be the wait's deadline (0010 design D10). It refuses, with no `up` and
no `down`, when this checkout already records a pod: `down` would delete it.
"""

import re
import subprocess
import sys
import time
from pathlib import Path

from gpunit.state import State
from live.window import LIVE, gpunit, hangups_interrupt, price, report, run, waited

SPEC = str(LIVE / "gpunit.dead.toml")
_REFUSED = re.compile(r"^\S+ refused: (.*)$")


def reason(lines: list[str]) -> str:
    """Return the text of the last refusal, empty when there is none.

    e.g. ["2026-10-17T09:00:00Z refused: the pod exited"] → "the pod exited"
    """
    said = [match[1] for line in lines if (match := _REFUSED.match(line))]
    return said[-1] if said else ""


def check(code: int, lines: list[str], down: int) -> list[str]:
    """Return what the run failed to show; empty when `up` exited 1 saying why.

    `down` is `gpunit down`'s code: a failed one may leave the pod billing.
    """
    failures = []
    if code != 1:
        failures.append(f"up exited {code}, not 1")
    if not reason(lines):
        failures.append("no line says why up refused")
    if down != 0:
        failures.append(f"gpunit down exited {down}: a pod may be left billing")
    return failures


def recorded(cwd: Path) -> list[Path]:
    """Return the files by which `cwd`'s `.gpunit/` records a pod; empty for none.

    e.g. a checkout holding `make live`'s session → [<cwd>/.gpunit/pod]
    """
    state = State(cwd)
    return [path for path in (state.pod, state.pending) if path.exists()]


def main() -> int:
    """Boot the dead image, delete its pod, say how `up` ended; 0 if `check` passes.

    1 at once when the checkout records a pod: `up` would refuse on it, and the
    `down` after it would delete a pod another session owns.
    """
    if held := recorded(Path.cwd()):
        for path in held:
            print(
                f"refused: {path} records a pod; end that session with gpunit down",
                file=sys.stderr,
            )
        return 1
    if code := price(SPEC):
        return code
    start = time.monotonic()
    lines = []
    with hangups_interrupt():
        up = subprocess.Popen(
            gpunit("up", "--spec", SPEC),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert up.stdout is not None
        try:
            try:
                for line in up.stdout:
                    print(line, end="", flush=True)
                    lines.append(line.rstrip("\n"))
                code = up.wait()
            except KeyboardInterrupt:
                # `up` has no SIGINT teardown: wait it out, as it may write its record.
                waited(up)
                raise
        finally:
            # The dead image never starts boot.py, so no ceiling stops its pod: a lost
            # create, a failed teardown or a Ctrl-C would leave it billing.
            down = run(gpunit("down", "--spec", SPEC))
    print(f"up exited {code} after {int(time.monotonic() - start)}s")
    print(f"reason: {reason(lines)}", flush=True)
    # Either way: it shows that no pod is left.
    run(gpunit("status", "--spec", SPEC))
    return report(check(code, lines, down))


if __name__ == "__main__":
    sys.exit(main())
