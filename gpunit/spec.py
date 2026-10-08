"""Load `gpunit.toml` into a `Spec`, refusing what no session may be opened on."""

import difflib
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from gpunit import log

DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")
_DURATION = re.compile(r"([1-9][0-9]*)([smh])")
_UNIT_S = {"s": 1, "m": 60, "h": 3600}
DEFAULT_TIMEOUT_S = 420

# The key, then the TOML types it accepts.
_REQUIRED: dict[str, tuple[type, ...]] = {
    "project": (str,),
    "image": (str,),
    "gpus": (list,),
    "vram_gb": (int,),
    "ceiling": (str,),
    "disk_gb": (int,),
}
_OPTIONAL: dict[str, tuple[type, ...]] = {
    "volume": (str,),
    "ports": (list,),
    "ram_gb": (int,),
    "cuda": (str,),
    "max_hourly": (int, float),
    "timeout": (int,),
    "env": (dict,),
}
_TYPES = _REQUIRED | _OPTIONAL


@dataclass(frozen=True)
class Port:
    """One forwarded port: `remote` on the pod, `local` on this machine."""

    remote: int
    local: int


@dataclass(frozen=True)
class Spec:
    """What a consumer declares about its GPU session."""

    project: str
    image: str
    gpus: tuple[str, ...]
    vram_gb: int
    ceiling_s: int
    disk_gb: int
    volume: str | None = None
    ports: tuple[Port, ...] = ()
    ram_gb: int | None = None
    cuda: str | None = None
    max_hourly: float | None = None
    timeout_s: int = DEFAULT_TIMEOUT_S
    env: Mapping[str, str] = field(default_factory=dict)


def parse_ceiling(text: str) -> int:
    """Return a duration's seconds, the unit required; raise `ValueError` otherwise.

    e.g. "45m" → 2700
    """
    match = _DURATION.fullmatch(text)
    if match is None:
        raise ValueError(text)
    return int(match[1]) * _UNIT_S[match[2]]


def load_spec(path: Path) -> Spec:
    """Return the spec at `path`; refuse, naming the field, on any fault."""
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as fault:
        log.refuse(f"{path}: {fault}")
    for key in raw:
        if key not in _TYPES:
            near = difflib.get_close_matches(key, list(_TYPES), n=1)
            hint = f"; did you mean {near[0]!r}?" if near else ""
            log.refuse(f"{path}: unknown key {key!r}{hint}")
    for key in _REQUIRED:
        if key not in raw:
            log.refuse(f"{path}: {key!r} is required")
    for key, value in raw.items():
        _check_type(path, key, value, _TYPES[key])

    if not DIGEST.search(raw["image"]):
        log.refuse(f"{path}: 'image' must end in @sha256:<64 hex>, not a tag")
    try:
        ceiling_s = parse_ceiling(raw["ceiling"])
    except ValueError:
        log.refuse(
            f"{path}: 'ceiling' must be a duration with a unit, as 600s, 45m or 4h"
        )
    return Spec(
        project=raw["project"],
        image=raw["image"],
        gpus=_gpus(path, raw["gpus"]),
        vram_gb=raw["vram_gb"],
        ceiling_s=ceiling_s,
        disk_gb=raw["disk_gb"],
        volume=raw.get("volume"),
        ports=tuple(_port(path, item) for item in raw.get("ports", [])),
        ram_gb=raw.get("ram_gb"),
        cuda=raw.get("cuda"),
        max_hourly=raw.get("max_hourly"),
        timeout_s=raw.get("timeout", DEFAULT_TIMEOUT_S),
        env=_env(path, raw.get("env", {})),
    )


def _check_type(path: Path, key: str, value: object, kinds: tuple[type, ...]) -> None:
    # bool is an int subclass in Python; `true` is never a count.
    if isinstance(value, bool) or not isinstance(value, kinds):
        names = " or ".join(kind.__name__ for kind in kinds)
        log.refuse(f"{path}: {key!r} must be {names}, not {type(value).__name__}")


def _gpus(path: Path, items: list[object]) -> tuple[str, ...]:
    names = tuple(item for item in items if isinstance(item, str))
    if not names or len(names) != len(items):
        log.refuse(f"{path}: 'gpus' must be a non-empty list of strings")
    return names


def _port(path: Path, item: object) -> Port:
    port = _port_type(path, item)
    for side in (port.remote, port.local):
        if not 1 <= side <= 65535:
            log.refuse(f"{path}: 'ports' holds {side}, outside 1-65535")
    return port


def _port_type(path: Path, item: object) -> Port:
    if isinstance(item, int) and not isinstance(item, bool):
        return Port(remote=item, local=item)
    if isinstance(item, dict) and set(item) <= {"remote", "local"} and "remote" in item:
        remote, local = item["remote"], item.get("local", item["remote"])
        if all(isinstance(n, int) and not isinstance(n, bool) for n in (remote, local)):
            return Port(remote=remote, local=local)
    log.refuse(
        f"{path}: 'ports' holds an int or {{ remote, local }} table, not {item!r}"
    )


def _env(path: Path, table: dict[str, object]) -> dict[str, str]:
    for key, value in table.items():
        if not isinstance(value, str):
            log.refuse(f"{path}: env {key!r} must be str, not {type(value).__name__}")
    return {key: value for key, value in table.items() if isinstance(value, str)}
