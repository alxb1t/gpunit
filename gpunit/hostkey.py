"""The host key, proven over the authenticated log before anything connects."""

import subprocess
from collections.abc import Callable
from typing import Protocol, TypeVar

from gpunit import log
from gpunit.contract import fingerprint, old_boot
from gpunit.provider import Provider
from gpunit.state import Record, State

LOG_WAIT_S = 60
# sshd can answer after the port is mapped, so the scan waits longer than the log.
SCAN_WAIT_S = 180
LOG_TAIL = 5000

T = TypeVar("T")


class Poll(Protocol):
    """The wait `lifecycle` passes in, so its clock stays where the tests replace it."""

    def __call__(self, seconds: int, attempt: Callable[[], T | None]) -> T | None:
        """Return the first value `attempt` returns, or None once `seconds` pass."""
        ...


class _OldBoot(Exception):
    """The image's boot prints no session nonce: the poll ends at once."""


def verify(
    provider: Provider, state: State, record: Record, nonce: str, poll: Poll
) -> str | None:
    """Prove the pod's host key; write known_hosts and say so, or return why not."""

    # The fingerprint comes over the authenticated API, never over the connection
    # it vouches for; nothing connects until the two agree.
    def read() -> str | None:
        # The last LOG_TAIL lines alone: RunPod's `since` reads the same tail
        # (decision D22), so a key line a heavy boot pushes out of it is not read.
        lines = provider.log(record.id, tail=LOG_TAIL)
        if printed := fingerprint(lines, nonce):
            return printed
        # Judged on a read that holds the whole log, its first line boot's
        # `step: the ceiling`, whose key line is boot's own: a full tail can hold
        # only a command's echo of an older one.
        if len(lines) < LOG_TAIL and old_boot(lines):
            raise _OldBoot
        return None

    try:
        printed = poll(LOG_WAIT_S, read)
    except _OldBoot:
        return (
            "the image's boot.sh prints no session nonce; "
            "ADD boot.sh from gpunit v0.6.0"
        )
    if printed is None:
        return f"no host-key line within {LOG_WAIT_S}s"
    scanned = poll(SCAN_WAIT_S, lambda: _scan(str(record.host), int(record.port or 0)))
    if scanned is None:
        return f"no host-key scan answered within {SCAN_WAIT_S}s"
    served = _fingerprint_of(scanned)
    if served != printed:
        return f"the pod's host key {served} does not match the printed {printed}"
    state.write_known_hosts(scanned)
    log.say(f"host key verified: {printed}")
    return None


def _scan(host: str, port: int) -> str | None:
    """Return the pod's Ed25519 host key as a known-hosts line, or None."""
    done = subprocess.run(
        ["ssh-keyscan", "-T", "10", "-t", "ed25519", "-p", str(port), host],
        capture_output=True,
        text=True,
        check=False,
    )
    lines = [
        line for line in done.stdout.splitlines() if line and not line.startswith("#")
    ]
    return lines[0] if lines else None


def _fingerprint_of(known_hosts_line: str) -> str | None:
    done = subprocess.run(
        ["ssh-keygen", "-lf", "-"],
        input=known_hosts_line + "\n",
        capture_output=True,
        text=True,
        check=False,
    )
    fields = done.stdout.split()
    return fields[1] if done.returncode == 0 and len(fields) > 1 else None
