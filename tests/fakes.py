"""A `Provider` and an HTTP opener that answer from a script and record every call."""

import io
import json
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from email.message import Message
from pathlib import Path
from typing import TypeVar

from gpunit.provider import GpuInfo, PodCost, PodInfo, VolumeCost, VolumeInfo
from gpunit.spec import Spec
from gpunit.state import Record
from tests.helpers import IMAGE

T = TypeVar("T")

FIXTURES = Path(__file__).parent / "fixtures"
RUNNING = PodInfo(
    status="RUNNING", host="203.0.113.7", port=40022, datacenter="EU-RO-1"
)
RECORD = Record("pod-1", IMAGE, RUNNING.host, RUNNING.port, "2026-10-07T00:00:00Z")
CARD = GpuInfo(vram_gb=24, hourly=0.69)
# What the stub `ssh-keygen -lf` answers for the scanned key (tests/conftest.py).
SERVED = "SHA256:served"
# The session's nonce in every test that does not draw its own (tests/conftest.py).
NONCE = "0123456789abcdef0123456789abcdef"
KEY_LINE = f"gpunit host key {NONCE}: {SERVED}"
# Boot prints it once the key line is out, just before the command starts.
STEP_LINE = "2026-10-07T00:00:05Z step: the command"
BOOT_LOG = [KEY_LINE, STEP_LINE]
# Boot's first line: a read that opens with it holds the log from its start.
CEILING_LINE = "2026-10-07T00:00:00Z step: the ceiling, 3600s"


class TtyInput(io.StringIO):
    """A stdin that holds `text` and says it is a terminal."""

    def isatty(self) -> bool:
        """Return True: a person is at the keyboard."""
        return True


class FakeClock:
    """A clock whose sleeps advance it at once."""

    def __init__(self) -> None:
        """Start at 0."""
        self.now = 0.0

    def monotonic(self) -> float:
        """Return the time slept so far."""
        return self.now

    def sleep(self, seconds: float) -> None:
        """Advance the clock."""
        self.now += seconds


class FakeProvider:
    """Answer each call from its script; an `Exception` in a script is raised.

    The sequence scripts are read in order, their last answer repeating.
    """

    def __init__(
        self,
        *,
        gpus: Mapping[str, GpuInfo | Exception] | None = None,
        volumes: Mapping[str, VolumeInfo | Exception] | None = None,
        creates: Sequence[str | Exception] = ("pod-1",),
        gets: Sequence[PodInfo | None] = (RUNNING,),
        logs: Sequence[list[str]] = (BOOT_LOG,),
        since_logs: Sequence[list[str]] = ([],),
        listings: Sequence[list[tuple[str, str]] | Exception] = ([],),
        deletes: Mapping[str, int] | None = None,
        pod_costs: Sequence[PodCost] | Exception = (),
        volume_costs: Sequence[VolumeCost] | Exception = (),
        stocks: Mapping[str, list[tuple[str, str]] | Exception] | None = None,
        volume_datacenters: AbstractSet[str] | Exception = frozenset({"EU-RO-1"}),
        volume_creates: Sequence[str | Exception] = ("vol-1",),
        volume_listings: Sequence[list[str] | Exception] = ([],),
        volume_deletes: Mapping[str, int] | None = None,
    ) -> None:
        """Script the answers; a card or volume not named answers `CARD` or fails.

        A card with no stock scripted is in stock in `EU-RO-1` alone.
        """
        self.gpus = dict(gpus or {})
        self.volume_infos = dict(volumes or {})
        self.creates = list(creates)
        self.gets = list(gets)
        self.logs = [list(lines) for lines in logs]
        self.since_logs = [list(lines) for lines in since_logs]
        self.listings = list(listings)
        self.deletes = dict(deletes or {})
        self.pod_costs = pod_costs
        self.volume_costs = volume_costs
        self.stocks = dict(stocks or {})
        self.standard = volume_datacenters
        self.volume_creates = list(volume_creates)
        self.volume_listings = list(volume_listings)
        self.volume_deletes = dict(volume_deletes or {})
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def named(self, verb: str) -> list[tuple[object, ...]]:
        """Return the arguments of each call to `verb`, in order."""
        return [args for name, args in self.calls if name == verb]

    def gpu(self, name: str) -> GpuInfo:
        """Answer the card's script, or `CARD`."""
        self.calls.append(("gpu", (name,)))
        return _raise_or(self.gpus.get(name, CARD))

    def volume(self, volume_id: str) -> VolumeInfo:
        """Answer the volume's script; an unscripted volume fails the test."""
        self.calls.append(("volume", (volume_id,)))
        return _raise_or(self.volume_infos[volume_id])

    def create(
        self, spec: Spec, gpu: str, pubkey: str, ceiling_s: int, *, nonce: str
    ) -> str:
        """Answer the next create in the script."""
        self.calls.append(("create", (spec, gpu, pubkey, ceiling_s, nonce)))
        return _raise_or(_next(self.creates))

    def get(self, pod_id: str) -> PodInfo | None:
        """Answer the next poll in the script."""
        self.calls.append(("get", (pod_id,)))
        return _next(self.gets)

    def log(self, pod_id: str, *, tail: int, since: str | None = None) -> list[str]:
        """Answer the next log read in its script: `since_logs` for a `since` read.

        A `since` read is a later read of the same tail, from then on: no test scripts
        it a line a tail read at the same poll has lost (decision D22).
        """
        self.calls.append(("log", (pod_id, tail, since)))
        return list(_next(self.logs if since is None else self.since_logs))

    def pod_billing(self, start: str, end: str) -> list[PodCost]:
        """Answer the scripted costs whose bucket starts in the window asked."""
        self.calls.append(("pod_billing", (start, end)))
        return _in_window(_raise_or(self.pod_costs), start, end)

    def volume_billing(self, start: str, end: str) -> list[VolumeCost]:
        """Answer the scripted costs whose bucket starts in the window asked."""
        self.calls.append(("volume_billing", (start, end)))
        return _in_window(_raise_or(self.volume_costs), start, end)

    def delete(self, pod_id: str) -> int:
        """Answer the pod's scripted status, or 204."""
        self.calls.append(("delete", (pod_id,)))
        return self.deletes.get(pod_id, 204)

    def stop(self, pod_id: str) -> int:
        """Answer 200."""
        self.calls.append(("stop", (pod_id,)))
        return 200

    def stock(self, card: str) -> list[tuple[str, str]]:
        """Answer the card's script, or `EU-RO-1` at `HIGH`."""
        self.calls.append(("stock", (card,)))
        return list(_raise_or(self.stocks.get(card, [("EU-RO-1", "HIGH")])))

    def volume_datacenters(self) -> set[str]:
        """Answer the scripted data centres."""
        self.calls.append(("volume_datacenters", ()))
        return set(_raise_or(self.standard))

    def create_volume(self, name: str, size_gb: int, datacenter: str) -> str:
        """Answer the next volume create in the script."""
        self.calls.append(("create_volume", (name, size_gb, datacenter)))
        return _raise_or(_next(self.volume_creates))

    def volumes(self, name: str) -> list[str]:
        """Answer the next volume listing in the script."""
        self.calls.append(("volumes", (name,)))
        return list(_raise_or(_next(self.volume_listings)))

    def delete_volume(self, volume_id: str) -> int:
        """Answer the volume's scripted status, or 204."""
        self.calls.append(("delete_volume", (volume_id,)))
        return self.volume_deletes.get(volume_id, 204)

    def list(self, project: str, image: str) -> list[tuple[str, str]]:
        """Answer the next listing in the script."""
        self.calls.append(("list", (project, image)))
        return list(_raise_or(_next(self.listings)))


C = TypeVar("C", PodCost, VolumeCost)


def _in_window(costs: Sequence[C], start: str, end: str) -> list[C]:
    # RFC 3339 times in one form, Z, order as strings do.
    return [cost for cost in costs if start <= cost.start < end]


def _next(script: list[T]) -> T:
    return script.pop(0) if len(script) > 1 else script[0]


def _raise_or(answer: T | Exception) -> T:
    if isinstance(answer, Exception):
        raise answer
    return answer


def fixture(name: str) -> bytes:
    """Return the body of `tests/fixtures/<name>`."""
    return (FIXTURES / name).read_bytes()


def log_stream(*lines: str) -> bytes:
    """Return a body of RunPod's container log stream holding `lines`."""
    return "".join(f"data: {json.dumps({'line': line})}\n" for line in lines).encode()


def page(items: list[dict[str, str]], cursor: str | None, key: str = "pods") -> bytes:
    """Return one page of a RunPod listing; `cursor` None is the last page."""
    more = {"nextCursor": cursor, "hasNextPage": cursor is not None}
    return json.dumps({key: items, "pagination": more}).encode()


class _Response(io.BytesIO):
    def __init__(self, status: int, body: bytes) -> None:
        super().__init__(body)
        self.status = status


class _Quiet(_Response):
    def readline(self, size: int | None = -1) -> bytes:
        line = super().readline(size)
        if not line:
            raise TimeoutError("the stream went quiet")
        return line


def quiet(body: bytes) -> _Response:
    """Return a 200 stream that sends `body`, then times out as a quiet socket does."""
    return _Quiet(200, body)


Answer = tuple[int, bytes] | Exception | _Response


class FakeOpener(urllib.request.OpenerDirector):
    """Answer each request from the script, as urllib would: a 4xx/5xx is raised."""

    def __init__(self, *answers: Answer) -> None:
        super().__init__()
        self.answers = list(answers)
        self.requests: list[urllib.request.Request] = []
        self.timeouts: list[float] = []

    def open(
        self,
        fullurl: str | urllib.request.Request,
        data: object = None,
        timeout: float | None = None,
    ) -> _Response:
        assert isinstance(fullurl, urllib.request.Request)
        assert timeout is not None
        self.requests.append(fullurl)
        self.timeouts.append(timeout)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        if isinstance(answer, _Response):
            return answer
        status, body = answer
        if status >= 400:
            raise urllib.error.HTTPError(
                fullurl.full_url, status, "", Message(), io.BytesIO(body)
            )
        return _Response(status, body)

    def sent(self, index: int = -1) -> dict[str, object]:
        data = self.requests[index].data
        assert isinstance(data, bytes)
        return json.loads(data)


def session_opener() -> FakeOpener:
    """Return an opener scripted for one whole session on RunPod: up, then down."""
    return FakeOpener(
        (200, page([], None)),
        (200, fixture("gpu.json")),
        (200, fixture("gpu.json")),
        (201, fixture("pod_created.json")),
        (200, fixture("pod_running.json")),
        quiet(log_stream(*BOOT_LOG)),
        (204, b""),
        (200, page([], None)),
    )
