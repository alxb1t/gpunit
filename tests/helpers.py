"""Write a spec, a tree or stubs, and run the CLI in-process, for the tests."""

from collections.abc import Mapping
from pathlib import Path
from typing import NoReturn, cast

import pytest

from gpunit import cli, log
from gpunit.provider import Provider
from gpunit.state import State, Window

IMAGE = "ghcr.io/alxb1t/isekai@sha256:" + "a" * 64

VALID = f"""\
project = "isekai"
image = "{IMAGE}"
gpus = ["RTX 4090", "RTX A6000"]
vram_gb = 24
ceiling = "45m"
disk_gb = 50
"""

# The valid spec, with a window volume of 60 GB for 4h.
WINDOW = VALID + 'volume_gb = 60\nvolume_ceiling = "4h"\n'


class NoRequests:
    """A provider that fails the test on any use."""

    def __getattr__(self, name: str) -> NoReturn:
        raise AssertionError(f"a request was made: {name}")


# The one provider that does not satisfy the protocol by its methods; cast here alone.
NO_REQUESTS = cast(Provider, NoRequests())


def write_spec(cwd: Path, text: str = VALID) -> Path:
    """Write `gpunit.toml` into `cwd` and return its path."""
    path = cwd / "gpunit.toml"
    path.write_text(text, encoding="utf-8")
    return path


def open_window(
    cwd: Path, ends_in_s: int, volume_id: str = "v1", datacenter: str = "EU-RO-1"
) -> State:
    """Record a 60 GB window volume in `cwd`, ending `ends_in_s` from now."""
    state = State(cwd)
    state.write_window(Window(volume_id, datacenter, 60, log.utc(ends_in_s)))
    return state


def with_port(cwd: Path, local: int) -> None:
    """Write the valid spec into `cwd`, forwarding remote 8188 to `local`."""
    write_spec(cwd, VALID + f"ports = [{{ remote = 8188, local = {local} }}]\n")


def tree(root: Path, files: Mapping[str, str]) -> Path:
    """Write each file under `root`, by its relative path, and return `root`."""
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def install_stubs(bin_dir: Path, scripts: Mapping[str, str]) -> Path:
    """Write each script into `bin_dir` as an executable of its name; return the dir."""
    bin_dir.mkdir(exist_ok=True)
    for name, script in scripts.items():
        (bin_dir / name).write_text(script, encoding="utf-8")
        (bin_dir / name).chmod(0o755)
    return bin_dir


def gpunit(argv: list[str], provider: Provider | None = None) -> int | str | None:
    """Run the CLI and return its exit code."""
    with pytest.raises(SystemExit) as exited:
        cli.main(argv, provider=provider)
    return exited.value.code
