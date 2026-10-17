"""Prove a container that exits at once ends `up`'s wait (0006 design D6).

e.g. `RUNPOD_API_KEY=<key> python live/dead.py` prints the price, boots the dead
image, says how `up` exited and why, shows that no pod is left, and exits 0 when
`check` passes. RunPod may restart the container, so the reason can be the wait's
deadline (0010 design D10).
"""

import re
import subprocess
import sys
import time

from live.window import LIVE, gpunit, price, report, run

SPEC = str(LIVE / "gpunit.dead.toml")
_REFUSED = re.compile(r"^\S+ refused: (.*)$")


def reason(lines: list[str]) -> str:
    """Return the text of the last refusal, empty when there is none.

    e.g. ["2026-10-17T09:00:00Z refused: the pod exited"] → "the pod exited"
    """
    said = [match[1] for line in lines if (match := _REFUSED.match(line))]
    return said[-1] if said else ""


def check(code: int, lines: list[str]) -> list[str]:
    """Return what the run failed to show; empty when `up` exited 1 saying why."""
    failures = []
    if code != 1:
        failures.append(f"up exited {code}, not 1")
    if not reason(lines):
        failures.append("no line says why up refused")
    return failures


def main() -> int:
    """Boot the dead image, say how `up` ended, and return 0 when `check` passes."""
    if code := price(SPEC):
        return code
    start = time.monotonic()
    up = subprocess.Popen(
        gpunit("up", "--spec", SPEC),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert up.stdout is not None
    lines = []
    for line in up.stdout:
        print(line, end="", flush=True)
        lines.append(line.rstrip("\n"))
    code = up.wait()
    print(f"up exited {code} after {int(time.monotonic() - start)}s")
    print(f"reason: {reason(lines)}", flush=True)
    # Either way: it shows that no pod is left.
    run(gpunit("status", "--spec", SPEC))
    return report(check(code, lines))


if __name__ == "__main__":
    sys.exit(main())
