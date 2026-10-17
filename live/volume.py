"""Prove a window volume carries a file from one pod to the next (0010 design D10).

e.g. `RUNPOD_API_KEY=<key> python live/volume.py` prints the price, rents a 10 GB
volume, writes the UTC time to it from one pod, reads it back from a second, and
deletes it.
"""

import subprocess
import sys
from pathlib import Path

from live.window import gpunit, run, window

LIVE = Path(__file__).parent
SPEC = str(LIVE / "gpunit.volume.toml")
PROOF = "/runpod-volume/proof"
# `$GPUNIT_SSH` is expanded by the shell `gpunit run` starts, not here.
WRITE = f'$GPUNIT_SSH "date -u +%FT%TZ | tee {PROOF}"'
READ = f"$GPUNIT_SSH cat {PROOF}"


def check(wrote: str, read: str) -> list[str]:
    """Return what the run failed to show; empty when the second pod read the first's.

    e.g. ("2026-10-17T09:00:00Z", "") → ["the second pod read '', not …"]
    """
    if not wrote:
        return ["the first pod wrote nothing"]
    if read != wrote:
        return [f"the second pod read {read!r}, not {wrote!r}"]
    return []


def _said(command: str) -> tuple[int, str]:
    """Run `command` on a pod of the spec; return its code and its stdout, stripped."""
    done = subprocess.run(
        gpunit("run", "--spec", SPEC, "--", "sh", "-c", command),
        stdout=subprocess.PIPE,
        text=True,
    )
    return done.returncode, done.stdout.rstrip("\n")


def body() -> int:
    """Write the proof from one pod, read it from a second; return 0 when they match."""
    code, wrote = _said(WRITE)
    if code:
        return code
    code, read = _said(READ)
    if code:
        return code
    print(f"wrote: {wrote}")
    print(f"read: {read}", flush=True)
    failures = check(wrote, read)
    for failure in failures:
        print(f"check failed: {failure}", file=sys.stderr)
    return 1 if failures else 0


def main() -> int:
    """Print the price, prove the window, then show that no pod is left."""
    code = run([sys.executable, str(LIVE / "price.py"), SPEC])
    if code:
        return code
    code = window(
        gpunit("volume", "up", "--spec", SPEC, "--yes"),
        gpunit("volume", "down", "--spec", SPEC),
        body,
    )
    if code:
        return code
    return run(gpunit("status", "--spec", SPEC))


if __name__ == "__main__":
    sys.exit(main())
