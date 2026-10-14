"""Prove a pod that dies while the model loads ends `serve`'s wait (0009 design D7).

e.g. `RUNPOD_API_KEY=<key> python live/serve_dead.py` serves `qwen3-4b` with an argument
vLLM refuses, prints gpunit's lines, and exits 0 only when `check` finds no failure.
"""

import dataclasses
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from gpunit import log
from gpunit.runpod import RunPod
from gpunit.serve import session, table

MODEL = "qwen3-4b"
CEILING_S = 600
# vLLM's argument parser refuses it and exits 2, as a crash in the wait does.
BAD_ARG = "--no-such-flag"
REFUSED = "refused: the pod stopped while the model loaded"
DELETE_S = 15
_DELETED = re.compile(r" pod \S+ deleted$")


def check(lines: list[str], code: int) -> list[str]:
    """Return what the run failed to show; empty when it proved the scenario.

    e.g. (a run's lines, 0) → ["the exit code is 0, not 1", …]
    """
    failures = []
    if code != 1:
        failures.append(f"the exit code is {code}, not 1")
    refused = next((line for line in lines if REFUSED in line), None)
    if refused is None:
        failures.append(f"no line holds {REFUSED!r}")
    said = [line for line in lines if " pod: " in line]
    for needle in (BAD_ARG.lstrip("-"), "the command exited 2"):
        if not any(needle in line for line in said):
            failures.append(f"no pod: line holds {needle!r}")
    deleted = next((line for line in lines if _DELETED.search(line)), None)
    if deleted is None:
        failures.append("no line says the pod was deleted")
    elif refused is not None:
        gap = (_time(deleted) - _time(refused)).total_seconds()
        if not 0 <= gap <= DELETE_S:
            failures.append(f"the delete came {gap:.0f}s after the refusal, not 0-15s")
    return failures


def _time(line: str) -> datetime:
    return datetime.strptime(line.split(" ", 1)[0], "%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    """Serve the broken row, print gpunit's lines, and return 0 when `check` passes."""
    lines: list[str] = []

    def sink(line: str) -> None:
        print(line, file=sys.stderr, flush=True)
        lines.append(line)

    load = table.load

    def broken(path: Path = table.TABLE) -> table.Table:
        loaded = load(path)
        row = loaded.models[MODEL]
        bad = dataclasses.replace(row, args=(*row.args, BAD_ARG))
        return dataclasses.replace(loaded, models={**loaded.models, MODEL: bad})

    # The shipped table, one argument added: the crash needs no row of its own.
    setattr(table, "load", broken)
    with log.redirect(sink):
        code = session.serve(
            MODEL,
            CEILING_S,
            api=True,
            volume=None,
            max_hourly=None,
            yes=True,
            think=False,
            provider=RunPod(os.environ),
        )
    failures = check(lines, code)
    for failure in failures:
        print(f"check failed: {failure}", file=sys.stderr)
    if not failures:
        print("check passed: the dead pod ended the wait and was deleted", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
