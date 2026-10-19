"""Load the bundled model table and the user file, and turn a row into its `Spec`."""

import os
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path

from gpunit import log
from gpunit.spec import DIGEST, Port, Spec, strings

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
    # The user file's path for a user row.
    source: str = "bundled"

    def spec(
        self,
        ceiling_s: int,
        volume: str | None,
        max_hourly: float | None,
        key: str,
        local_port: int,
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
            ports=(Port(remote=PORT, local=local_port),),
            timeout_s=WAIT_S,
            max_hourly=max_hourly,
            env={
                "SERVE_REPO": self.repo,
                "SERVE_REVISION": self.revision,
                "SERVE_NAME": self.served,
                # `serve/launch.py` splits it on spaces; `load` refuses a space inside.
                "SERVE_ARGS": " ".join(self.args),
                "VLLM_API_KEY": key,
            },
        )


@dataclass(frozen=True)
class Table:
    """The image every row serves on, the rows by name, and the user file read."""

    image: str
    models: Mapping[str, Row]
    user: Path | None = None
    replaced: tuple[str, ...] = ()


def load(path: Path = TABLE) -> Table:
    """Return the table at `path`; refuse, naming the row and field, on any fault."""
    raw = _read(path)
    image = raw.get("image")
    if not isinstance(image, str) or not DIGEST.search(image):
        log.refuse(f"{path}: 'image' must end in @sha256:<64 hex>, not a tag")
    return Table(image=image, models=_rows(path, image, raw))


def user_file(given: Path | None) -> Path | None:
    """Return the user file to read: `given`, `GPUNIT_MODELS`, or the XDG default.

    e.g. None, no GPUNIT_MODELS, no XDG_CONFIG_HOME → ~/.config/gpunit/models.toml
    """
    if given is not None:
        return given
    named = os.environ.get("GPUNIT_MODELS")
    if named:
        return Path(named)
    # A relative XDG_CONFIG_HOME is ignored, as the XDG base directory spec says.
    base = os.environ.get("XDG_CONFIG_HOME", "")
    config = Path(base) if os.path.isabs(base) else Path.home() / ".config"
    default = config / "gpunit" / "models.toml"
    return default if default.is_file() else None


def rows(given: Path | None = None) -> Table:
    """Return the bundled rows and the user file's; a user row replaces its namesake."""
    # The module's `load`, looked up at the call: live/serve_dead.py patches it.
    bundled = load()
    path = user_file(given)
    if path is None:
        return bundled
    raw = _read(path)
    extra = sorted(raw.keys() - {"models"})
    if extra:
        log.refuse(
            f"{path}: unknown key {extra[0]!r}; a user file holds [models.<name>] rows"
            " alone, served on the bundled image"
        )
    own = {
        name: replace(row, source=str(path))
        for name, row in _rows(path, bundled.image, raw).items()
    }
    return Table(
        image=bundled.image,
        models={**bundled.models, **own},
        user=path,
        replaced=tuple(sorted(own.keys() & bundled.models.keys())),
    )


def _read(path: Path) -> dict[str, object]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as fault:
        log.refuse(f"{path}: {fault}")


def _rows(path: Path, image: str, raw: dict[str, object]) -> dict[str, Row]:
    models = raw.get("models")
    if not isinstance(models, dict) or not models:
        log.refuse(f"{path}: 'models' must hold at least one row")
    return {name: _row(path, name, image, row) for name, row in models.items()}


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
        gpus=strings(where, "gpus", raw["gpus"]),
        disk_gb=raw["disk_gb"],
    )


# The flags `serve/launch.py` and the pod's environment set: the pin, the name, the
# loopback bind and the key. 0014·S2.
_LAUNCHERS = frozenset(
    {
        "--revision",
        "--code-revision",
        "--tokenizer-revision",
        "--served-model-name",
        "--host",
        "--port",
        "--api-key",
    }
)


def _args(where: str, items: list[object]) -> tuple[str, ...]:
    args = strings(where, "args", items)
    if any(" " in arg for arg in args):
        log.refuse(f"{where}: 'args' holds an argument with a space, which sh splits")
    # Refused before a pod is rented, whatever the launcher does: decision D40.
    if "--enable-log-requests" in args:
        log.refuse(
            f"{where}: 'args' holds --enable-log-requests; request logging stays off"
        )
    # vLLM reads `_` as `-` and keeps a flag's last value, so a row's own would win.
    for arg in args:
        flag = arg.split("=", 1)[0].replace("_", "-")
        if flag in _LAUNCHERS:
            log.refuse(f"{where}: 'args' holds {flag}; the launcher sets it")
    return args
