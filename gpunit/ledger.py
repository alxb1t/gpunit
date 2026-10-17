"""Name each pod and window volume gpunit learns of, so billing finds its project."""

import json
import os
from collections.abc import Iterator
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import TypeVar

from gpunit import log
from gpunit.state import home_state

T = TypeVar("T", "Entry", "VolumeEntry", "Deleted")


@dataclass(frozen=True)
class Entry:
    """One ledger line; `card` is None for a pod the sweep found."""

    id: str
    project: str
    card: str | None
    image: str
    at: str


@dataclass(frozen=True)
class VolumeEntry:
    """One window volume's line; `ends` is its UTC end when the line was written."""

    id: str
    project: str
    kind: str
    ends: str
    at: str


@dataclass(frozen=True)
class Deleted:
    """A volume's delete, once it answered 204; `kind` is "deleted"."""

    id: str
    kind: str
    at: str


def path() -> Path:
    """Return the ledger file, under the home directory of whoever runs gpunit."""
    return home_state() / "ledger.jsonl"


def record(project: str, pod_id: str, card: str | None, image: str) -> None:
    """Append the pod's line; with no home or on an `OSError`, warn, never raise."""
    _append(asdict(Entry(pod_id, project, card, image, log.utc())))


def record_volume(project: str, volume_id: str, ends: str) -> None:
    """Append the window volume's line; with no home or on an `OSError`, warn."""
    _append(asdict(VolumeEntry(volume_id, project, "volume", ends, log.utc())))


def record_deleted(volume_id: str) -> None:
    """Append the line of a volume's delete; with no home or on an `OSError`, warn."""
    _append(asdict(Deleted(volume_id, "deleted", log.utc())))


def _append(line: dict[str, object]) -> None:
    try:
        file = path()
        file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(file, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as out:
            out.write(json.dumps(line) + "\n")
    except (OSError, RuntimeError) as fault:
        log.say(f"warning: the ledger could not be written: {fault}")


def read() -> dict[str, Entry]:
    """Return each pod id's entry, the first line for an id winning.

    A missing ledger is empty; a line that is not JSON, lacks a key, or holds a
    field that is not a string (`card` may be null) is skipped. A ledger that
    cannot be read refuses.
    """
    entries: dict[str, Entry] = {}
    for entry in _parsed(Entry):
        texts = (entry.id, entry.project, entry.image, entry.at)
        if all(isinstance(text, str) for text in texts) and isinstance(
            entry.card, str | None
        ):
            entries.setdefault(entry.id, entry)
    return entries


def volumes() -> dict[str, VolumeEntry]:
    """Return each window volume's entry, the last line for an id winning.

    A line that is not a volume's, or holds a field that is not a string, is
    skipped; a ledger that cannot be read refuses.
    """
    keys = [field.name for field in fields(VolumeEntry)]
    entries: dict[str, VolumeEntry] = {}
    for entry in _parsed(VolumeEntry):
        if entry.kind == "volume" and all(
            isinstance(getattr(entry, key), str) for key in keys
        ):
            entries[entry.id] = entry
    return entries


def deleted() -> set[str]:
    """Return the ids of every volume the ledger records as deleted.

    A ledger that cannot be read refuses.
    """
    return {
        entry.id
        for entry in _parsed(Deleted)
        if entry.kind == "deleted" and isinstance(entry.id, str)
    }


def _parsed(kind: type[T]) -> Iterator[T]:
    """Yield a `kind` for each line holding its every key; skip the rest."""
    keys = [field.name for field in fields(kind)]
    for line in _lines():
        try:
            raw = json.loads(line)
            yield kind(**{key: raw[key] for key in keys})
        except (ValueError, TypeError, KeyError):
            continue


def _lines() -> list[str]:
    try:
        return path().read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    except (OSError, UnicodeDecodeError, RuntimeError) as fault:
        log.refuse(f"the ledger could not be read: {fault}")
