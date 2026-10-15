"""The seam between the session and a GPU cloud: what is asked, and what answers."""

import re
from dataclasses import dataclass
from typing import Protocol

from gpunit.spec import Spec

# Only a whole line counts, so nothing logged later can echo a key line in. The nonce
# is the session's, so a command's echo cannot match it: 0009 design D3.
_HOST_KEY = re.compile(r"^gpunit host key ([0-9a-f]{32}): (SHA256:[A-Za-z0-9+/]+)\s*$")
# What a boot.sh older than v0.6.0 prints: the key line with no nonce.
_OLD_KEY = re.compile(r"^gpunit host key: SHA256:[A-Za-z0-9+/]+\s*$")
# Boot says this after its key line, before the command starts; see 0006 design D1.
_BOOT_STEP = re.compile(r"^\S+ step: the command\s*$")


def pod_name(project: str) -> str:
    """Return the name every pod of `project` carries.

    e.g. "isekai" → "gpunit-isekai"
    """
    return f"gpunit-{project}"


# The statuses a delete succeeds with; `down` and `RunPod.delete` read the same set.
DELETED = (200, 204)


def fingerprint(lines: list[str], nonce: str) -> str | None:
    """Return the last fingerprint printed with `nonce` before boot's command, or None.

    e.g. ["gpunit host key <nonce>: SHA256:abc", "<UTC> step: the command"]
        → "SHA256:abc"
    """
    # The last boot wins: a restarted container prints a new key.
    pending = accepted = None
    for line in lines:
        if (match := _HOST_KEY.match(line)) and match[1] == nonce:
            pending = match[2]
        elif _BOOT_STEP.match(line):
            accepted = pending
    return accepted


def old_boot(lines: list[str]) -> bool:
    """Return True when a key line with no nonce has boot's step line after it.

    e.g. ["gpunit host key: SHA256:abc", "<UTC> step: the command"] → True
    """
    keyed = False
    for line in lines:
        if _OLD_KEY.match(line):
            keyed = True
        elif keyed and _BOOT_STEP.match(line):
            return True
    return False


@dataclass(frozen=True)
class GpuInfo:
    """A card in the catalogue: its memory and its hourly price."""

    vram_gb: int
    hourly: float


@dataclass(frozen=True)
class VolumeInfo:
    """A network volume: the data centre it pins and its size."""

    datacenter: str
    size_gb: int


@dataclass(frozen=True)
class PodInfo:
    """A pod's status, and its public SSH address once mapped."""

    status: str
    host: str | None
    port: int | None


@dataclass(frozen=True)
class PodCost:
    """What the provider charged for one pod over the bucket starting at `start`."""

    pod_id: str
    start: str
    amount: float


@dataclass(frozen=True)
class VolumeCost:
    """What the provider charged for one network volume over one bucket."""

    volume_id: str
    start: str
    amount: float


class Lost(Exception):
    """The provider's answer did not arrive; a create may have made a pod."""


class Refused(Exception):
    """The provider refused the request (a 400): capacity, or a rule broken."""


class Unknown(Exception):
    """The provider does not know the name asked for (a 404)."""


class NoImage(Exception):
    """A pod of the project's name carries no image, so it cannot be told ours."""


class Provider(Protocol):
    """What the session asks of a GPU cloud."""

    def gpu(self, name: str) -> GpuInfo:
        """Return the card's catalogue entry; raise `Unknown` on a 404, else `Lost`."""
        ...

    def volume(self, volume_id: str) -> VolumeInfo:
        """Return the volume; raise `Unknown` on a 404, else `Lost`."""
        ...

    def create(
        self, spec: Spec, gpu: str, pubkey: str, ceiling_s: int, *, nonce: str
    ) -> str:
        """Return the new pod's id; raise `Refused` on a 400, else `Lost`."""
        ...

    def get(self, pod_id: str) -> PodInfo | None:
        """Return the pod, or None on any failed read."""
        ...

    def log(self, pod_id: str, *, tail: int, since: str | None = None) -> list[str]:
        """Return the container log's last `tail` lines; empty on a failed read.

        With `since`, an RFC 3339 time, return the lines from then on instead.
        """
        ...

    def pod_billing(self, start: str, end: str) -> list[PodCost]:
        """Return each pod's charge per UTC day in `[start, end)`; raise `Lost`."""
        ...

    def volume_billing(self, start: str, end: str) -> list[VolumeCost]:
        """Return each volume's charge per UTC day in `[start, end)`; raise `Lost`."""
        ...

    def list(self, project: str, image: str) -> list[tuple[str, str]]:
        """Return (id, status) of each live project pod; raise `Lost` or `NoImage`."""
        ...

    def delete(self, pod_id: str) -> int:
        """Delete the pod and return the HTTP status; 0 when no answer came."""
        ...

    def stop(self, pod_id: str) -> int:
        """Stop the pod and return the HTTP status; 0 when no answer came."""
        ...
