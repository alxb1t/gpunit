"""Load the bundled model table, and turn a row into the `Spec` it is served on."""

import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from gpunit import log
from gpunit.spec import DIGEST, Port, Spec

TABLE = Path(__file__).with_name("models.toml")
PORT = 8000
# The bound on each wait: a cold host pulls vLLM's image before it maps port 22.
WAIT_S = 1200
_REVISION = re.compile(r"[0-9a-f]{40}")

# The key, then the TOML type it holds.
_FIELDS: dict[str, type] = {
    "repo": str,
    "revision": str,
    "served": str,
    "args": list,
    "vram_gb": int,
    "gpus": list,
    "disk_gb": int,
}


@dataclass(frozen=True)
class Row:
    """One model: where its weights are, how vLLM serves it, and what it runs on."""

    name: str
    image: str
    repo: str
    revision: str
    served: str
    args: tuple[str, ...]
    vram_gb: int
    gpus: tuple[str, ...]
    disk_gb: int

    def spec(
        self,
        ceiling_s: int,
        volume: str | None,
        max_hourly: float | None,
        key: str,
    ) -> Spec:
        """Return the session's spec: the row's cards and image, its model in `env`."""
        return Spec(
            project=f"serve-{self.name}",
            image=self.image,
            gpus=self.gpus,
            vram_gb=self.vram_gb,
            ceiling_s=ceiling_s,
            disk_gb=self.disk_gb,
            volume=volume,
            ports=(Port(remote=PORT, local=PORT),),
            timeout_s=WAIT_S,
            max_hourly=max_hourly,
            env={
                "SERVE_REPO": self.repo,
                "SERVE_REVISION": self.revision,
                "SERVE_NAME": self.served,
                # `sh` word-splits it in the image's CMD; `load` refuses a space inside.
                "SERVE_ARGS": " ".join(self.args),
                "VLLM_API_KEY": key,
            },
        )


@dataclass(frozen=True)
class Table:
    """The image every row serves on, and the rows by name."""

    image: str
    models: Mapping[str, Row]


def load(path: Path = TABLE) -> Table:
    """Return the table at `path`; refuse, naming the row and field, on any fault."""
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as fault:
        log.refuse(f"{path}: {fault}")
    image = raw.get("image")
    if not isinstance(image, str) or not DIGEST.search(image):
        log.refuse(f"{path}: 'image' must end in @sha256:<64 hex>, not a tag")
    models = raw.get("models")
    if not isinstance(models, dict) or not models:
        log.refuse(f"{path}: 'models' must hold at least one row")
    return Table(
        image=image,
        models={name: _row(path, name, image, row) for name, row in models.items()},
    )


def _row(path: Path, name: str, image: str, raw: object) -> Row:
    where = f"{path}: models.{name}"
    if not isinstance(raw, dict):
        log.refuse(f"{where} must be a table")
    for key, kind in _FIELDS.items():
        if key not in raw:
            log.refuse(f"{where}: {key!r} is required")
        # bool is an int subclass in Python; `true` is never a count.
        if isinstance(raw[key], bool) or not isinstance(raw[key], kind):
            log.refuse(f"{where}: {key!r} must be {kind.__name__}")
    if not _REVISION.fullmatch(raw["revision"]):
        log.refuse(f"{where}: 'revision' must be a 40-hex commit, not a branch or tag")
    return Row(
        name=name,
        image=image,
        repo=raw["repo"],
        revision=raw["revision"],
        served=raw["served"],
        args=_args(where, raw["args"]),
        vram_gb=raw["vram_gb"],
        gpus=_strings(where, "gpus", raw["gpus"]),
        disk_gb=raw["disk_gb"],
    )


def _strings(where: str, key: str, items: list[object]) -> tuple[str, ...]:
    names = tuple(item for item in items if isinstance(item, str))
    if not names or len(names) != len(items):
        log.refuse(f"{where}: {key!r} must be a non-empty list of strings")
    return names


def _args(where: str, items: list[object]) -> tuple[str, ...]:
    args = _strings(where, "args", items)
    if any(" " in arg for arg in args):
        log.refuse(f"{where}: 'args' holds an argument with a space, which sh splits")
    return args
