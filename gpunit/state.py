"""Read and write the session's files under `.gpunit/` in the working directory."""

import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

DIR = ".gpunit"


@dataclass(frozen=True)
class Record:
    """The recorded pod; `host` and `port` are None until the wait answers them."""

    id: str
    image: str
    host: str | None
    port: int | None
    created: str


class State:
    """The `.gpunit/` files: `pod`, `pending`, `known_hosts`, `key`, `key.pub`."""

    def __init__(self, cwd: Path) -> None:
        """Point at `<cwd>/.gpunit/`; nothing is created until written."""
        self.dir = cwd / DIR
        self.pod = self.dir / "pod"
        self.pending = self.dir / "pending"
        self.known_hosts = self.dir / "known_hosts"
        self.key = self.dir / "key"
        self.key_pub = self.dir / "key.pub"
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
        self._mkdir()
        partial = self.pod.with_name("pod.partial")
        partial.write_text(json.dumps(asdict(record)) + "\n", encoding="utf-8")
        os.replace(partial, self.pod)

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
