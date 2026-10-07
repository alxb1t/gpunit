"""Write a spec and run the CLI in-process, for the tests."""

from pathlib import Path
from typing import NoReturn

import pytest

from gpunit import cli

IMAGE = "ghcr.io/alxb1t/isekai@sha256:" + "a" * 64

VALID = f"""\
project = "isekai"
image = "{IMAGE}"
gpus = ["RTX 4090", "RTX A6000"]
vram_gb = 24
ceiling = "45m"
disk_gb = 50
"""


class NoRequests:
    """A provider that fails the test on any use."""

    def __getattr__(self, name: str) -> NoReturn:
        raise AssertionError(f"a request was made: {name}")


def write_spec(cwd: Path, text: str = VALID) -> Path:
    """Write `gpunit.toml` into `cwd` and return its path."""
    path = cwd / "gpunit.toml"
    path.write_text(text, encoding="utf-8")
    return path


def gpunit(argv: list[str], provider: object | None = None) -> int | str | None:
    """Run the CLI and return its exit code."""
    with pytest.raises(SystemExit) as exited:
        cli.main(argv, provider=provider)
    return exited.value.code
