"""Read and write the session's files under `.gpunit/`, and name gpunit's home state."""

import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from gpunit import log

DIR = ".gpunit"


def home_state() -> Path:
    """Return gpunit's directory under the home of whoever runs it, from any directory.

    e.g. HOME=/home/ada → /home/ada/.local/state/gpunit
    """
    return Path.home() / ".local" / "state" / "gpunit"


@dataclass(frozen=True)
class Record:
    """The recorded pod; `host` and `port` are None until the wait answers them."""

    id: str
    image: str
    host: str | None
    port: int | None
    created: str


@dataclass(frozen=True)
class Window:
    """The recorded window volume; `ends` is UTC, e.g. "2026-10-15T14:30:00Z"."""

    id: str
    datacenter: str
    size_gb: int
    ends: str

    def ends_within(self, seconds: int) -> bool:
        """Return True when the window ends `seconds` from now or sooner."""
        # One UTC form, Z: these times order as strings do.
        return log.utc(seconds) >= self.ends


class State:
    """The `.gpunit/` files: the pod's, the keypair's and the window volume's."""

    def __init__(self, cwd: Path) -> None:
        """Point at `<cwd>/.gpunit/`; nothing is created until written."""
        self.dir = cwd / DIR
        self.pod = self.dir / "pod"
        self.pending = self.dir / "pending"
        self.known_hosts = self.dir / "known_hosts"
        self.key = self.dir / "key"
        self.key_pub = self.dir / "key.pub"
        self.volume = self.dir / "volume"
        self.volume_pending = self.dir / "volume.pending"
        # Set by this process's own `mark_pending`: a create began here, whatever
        # files an earlier session left.
        self.began = False

    def read(self) -> Record | None:
        """Return the recorded pod, or None when no record exists."""
        if not self.pod.exists():
            return None
        return Record(**json.loads(self.pod.read_text(encoding="utf-8")))

    def write(self, record: Record) -> None:
        """Write the record whole, so a reader never sees half of it."""
        self._replace(self.pod, asdict(record))

    def window(self) -> Window | None:
        """Return the recorded window volume, or None when none is recorded."""
        if not self.volume.exists():
            return None
        return Window(**json.loads(self.volume.read_text(encoding="utf-8")))

    def write_window(self, window: Window) -> None:
        """Write the window whole, so a reader never sees half of it."""
        self._replace(self.volume, asdict(window))

    def clear_window(self) -> None:
        """Remove the window's record."""
        self.volume.unlink(missing_ok=True)

    def mark_volume_pending(self) -> None:
        """Create `volume.pending`: a create may have made a volume no record names."""
        self._mkdir()
        self.volume_pending.touch()

    def clear_volume_pending(self) -> None:
        """Remove `volume.pending`."""
        self.volume_pending.unlink(missing_ok=True)

    def mark_pending(self) -> None:
        """Create `pending`: a create may have made a pod no record names."""
        self._mkdir()
        self.pending.touch()
        self.began = True

    def clear_pending(self) -> None:
        """Remove `pending`."""
        self.pending.unlink(missing_ok=True)

    def write_known_hosts(self, line: str) -> None:
        """Write the verified host key line."""
        self._mkdir()
        self.known_hosts.write_text(line.rstrip("\n") + "\n", encoding="utf-8")

    def keygen(self, comment: str) -> str:
        """Make a fresh Ed25519 keypair at mode 0600 and return the public key line."""
        self._mkdir()
        for path in (self.key, self.key_pub):
            path.unlink(missing_ok=True)
        subprocess.run(
            [
                "ssh-keygen",
                "-q",
                "-t",
                "ed25519",
                "-N",
                "",
                "-f",
                str(self.key),
                "-C",
                comment,
            ],
            check=True,
            stdin=subprocess.DEVNULL,
        )
        for path in (self.key, self.key_pub):
            path.chmod(0o600)
        return self.key_pub.read_text(encoding="utf-8").strip()

    def clear_session(self) -> None:
        """Remove the record, the host key and the keypair; `pending` is the sweep's."""
        for path in (self.pod, self.known_hosts, self.key, self.key_pub):
            path.unlink(missing_ok=True)

    def _mkdir(self) -> None:
        self.dir.mkdir(mode=0o700, exist_ok=True)
        # A found directory keeps its mode through `mkdir`.
        self.dir.chmod(0o700)

    def _replace(self, path: Path, fields: dict[str, object]) -> None:
        self._mkdir()
        partial = path.with_name(f"{path.name}.partial")
        partial.write_text(json.dumps(fields) + "\n", encoding="utf-8")
        os.replace(partial, path)
