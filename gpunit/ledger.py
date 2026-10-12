"""Name each pod gpunit learns of, so its billing finds its project after teardown."""

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from gpunit import log


@dataclass(frozen=True)
class Entry:
    """One ledger line; `card` is None for a pod the sweep found."""

    id: str
    project: str
    card: str | None
    image: str
    at: str


def path() -> Path:
    """Return the ledger file, under the home directory of whoever runs gpunit."""
    return Path.home() / ".local" / "state" / "gpunit" / "ledger.jsonl"


def record(project: str, pod_id: str, card: str | None, image: str) -> None:
    """Append the pod's line; on an `OSError` warn and return, never raise."""
    entry = Entry(pod_id, project, card, image, log.utc())
    file = path()
    try:
        file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(file, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as out:
            out.write(json.dumps(asdict(entry)) + "\n")
    except OSError as fault:
        log.say(f"warning: the ledger could not be written: {fault}")


def read() -> dict[str, Entry]:
    """Return each pod id's entry, the first line for an id winning.

    A missing ledger is empty; a line that is not JSON or lacks a key is skipped.
    """
    try:
        lines = path().read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return {}
    keys = [field.name for field in fields(Entry)]
    entries: dict[str, Entry] = {}
    for line in lines:
        try:
            raw = json.loads(line)
            entry = Entry(**{key: raw[key] for key in keys})
        except (ValueError, TypeError, KeyError):
            continue
        entries.setdefault(entry.id, entry)
    return entries
