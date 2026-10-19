"""The seam between the session and a GPU cloud: what is asked, and what answers."""

from dataclasses import dataclass
from typing import Protocol

from gpunit.spec import Spec


def pod_name(project: str) -> str:
    """Return the name every pod of `project` carries.

    e.g. "isekai" → "gpunit-isekai"
    """
    return f"gpunit-{project}"


# The statuses a delete succeeds with; `down` and `RunPod.delete` read the same set.
DELETED = (200, 204)


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
    """A pod's status, its public SSH address once mapped, and its data centre."""

    status: str
    host: str | None
    port: int | None
    datacenter: str | None = None


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


class Unplaceable(Exception):
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
        """Return the new pod's id; raise `Unplaceable` on a 400, else `Lost`."""
        ...

    def get(self, pod_id: str) -> PodInfo | None:
        """Return the pod, or None on any failed read."""
        ...

    def log(self, pod_id: str, *, tail: int, since: str | None = None) -> list[str]:
        """Return the container log's last `tail` lines; empty on a failed read.

        With `since`, an RFC 3339 time, return the lines from then on instead, among
        the provider's longest tail: RunPod's last 5000, so a line before them is lost.
        """
        ...

    def pod_billing(self, start: str, end: str) -> list[PodCost]:
        """Return each pod's charge per UTC day in `[start, end)`; raise `Lost`."""
        ...

    def volume_billing(self, start: str, end: str) -> list[VolumeCost]:
        """Return each volume's charge per UTC day in `[start, end)`; raise `Lost`."""
        ...

    def delete(self, pod_id: str) -> int:
        """Delete the pod and return the HTTP status; 0 when no answer came."""
        ...

    def stop(self, pod_id: str) -> int:
        """Stop the pod and return the HTTP status; 0 when no answer came."""
        ...

    def stock(self, card: str) -> list[tuple[str, str]]:
        """Return (data centre, availability) where the card is in stock.

        Raise `Unknown` on a 404, else `Lost`. e.g. [("EU-RO-1", "HIGH")]
        """
        ...

    def volume_datacenters(self) -> set[str]:
        """Return the data centres offering standard volumes; raise `Lost`."""
        ...

    def create_volume(self, name: str, size_gb: int, datacenter: str) -> str:
        """Return the volume's id; raise `Unplaceable` on a 400 or 422, else `Lost`."""
        ...

    def volumes(self, name: str) -> list[str]:
        """Return the ids of the volumes named `name`; raise `Lost`."""
        ...

    def delete_volume(self, volume_id: str) -> int:
        """Delete the volume and return the HTTP status; 0 when no answer came."""
        ...

    def list(self, project: str, image: str) -> list[tuple[str, str]]:
        """Return (id, status) of each live project pod; raise `Lost` or `NoImage`."""
        ...
