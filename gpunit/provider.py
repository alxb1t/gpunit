"""The seam between the session and a GPU cloud: what is asked, and what answers."""

import re
from dataclasses import dataclass
from typing import Protocol

from gpunit.spec import Spec

# Only a whole line counts, so nothing logged later can echo a key line in.
_HOST_KEY = re.compile(r"^gpunit host key: (SHA256:[A-Za-z0-9+/]+)\s*$")


def pod_name(project: str) -> str:
    """Return the name every pod of `project` carries.

    e.g. "isekai" → "gpunit-isekai"
    """
    return f"gpunit-{project}"


# The statuses a delete succeeds with; `down` and `RunPod.delete` read the same set.
DELETED = (200, 204)


def fingerprint(lines: list[str]) -> str | None:
    """Return the last host-key fingerprint the pod's log printed, or None.

    e.g. ["gpunit host key: SHA256:abc"] → "SHA256:abc"
    """
    # The last wins: a restarted container prints a new key.
    found = [match[1] for line in lines if (match := _HOST_KEY.match(line))]
    return found[-1] if found else None


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

    def create(self, spec: Spec, gpu: str, pubkey: str, ceiling_s: int) -> str:
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

    def list(self, project: str, image: str) -> list[tuple[str, str]]:
        """Return (id, status) of each live project pod; raise `Lost` or `NoImage`."""
        ...

    def delete(self, pod_id: str) -> int:
        """Delete the pod and return the HTTP status; 0 when no answer came."""
        ...

    def stop(self, pod_id: str) -> int:
        """Stop the pod and return the HTTP status; 0 when no answer came."""
        ...
