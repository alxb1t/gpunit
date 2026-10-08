"""A `Provider` and an HTTP opener that answer from a script and record every call."""

import io
import json
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from email.message import Message
from pathlib import Path
from typing import TypeVar

from gpunit.provider import GpuInfo, PodInfo, VolumeInfo
from gpunit.spec import Spec
from gpunit.state import Record
from tests.helpers import IMAGE

T = TypeVar("T")

FIXTURES = Path(__file__).parent / "fixtures"
RUNNING = PodInfo(status="RUNNING", host="203.0.113.7", port=40022)
RECORD = Record("pod-1", IMAGE, RUNNING.host, RUNNING.port, "2026-10-07T00:00:00Z")
CARD = GpuInfo(vram_gb=24, hourly=0.69)
# What the stub `ssh-keygen -lf` answers for the scanned key (tests/conftest.py).
SERVED = "SHA256:served"
KEY_LINE = f"gpunit host key: {SERVED}"


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
        logs: Sequence[list[str]] = ([KEY_LINE],),
        listings: Sequence[list[tuple[str, str]] | Exception] = ([],),
        deletes: Mapping[str, int] | None = None,
    ) -> None:
        """Script the answers; a card or volume not named answers `CARD` or fails."""
        self.gpus = dict(gpus or {})
        self.volumes = dict(volumes or {})
        self.creates = list(creates)
        self.gets = list(gets)
        self.logs = [list(lines) for lines in logs]
        self.listings = list(listings)
        self.deletes = dict(deletes or {})
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
        return _raise_or(self.volumes[volume_id])

    def create(self, spec: Spec, gpu: str, pubkey: str, ceiling_s: int) -> str:
        """Answer the next create in the script."""
        self.calls.append(("create", (spec, gpu, pubkey, ceiling_s)))
        return _raise_or(_next(self.creates))

    def get(self, pod_id: str) -> PodInfo | None:
        """Answer the next poll in the script."""
        self.calls.append(("get", (pod_id,)))
        return _next(self.gets)

    def log(self, pod_id: str, *, tail: int) -> list[str]:
        """Answer the next log read in the script."""
        self.calls.append(("log", (pod_id, tail)))
        return list(_next(self.logs))

    def list(self, project: str, image: str) -> list[tuple[str, str]]:
        """Answer the next listing in the script."""
        self.calls.append(("list", (project, image)))
        return list(_raise_or(_next(self.listings)))

    def delete(self, pod_id: str) -> int:
        """Answer the pod's scripted status, or 204."""
        self.calls.append(("delete", (pod_id,)))
        return self.deletes.get(pod_id, 204)

    def stop(self, pod_id: str) -> int:
        """Answer 200."""
        self.calls.append(("stop", (pod_id,)))
        return 200


def _next(script: list[T]) -> T:
    return script.pop(0) if len(script) > 1 else script[0]


def _raise_or(answer: T | Exception) -> T:
    if isinstance(answer, Exception):
        raise answer
    return answer


def fixture(name: str) -> bytes:
    """Return the body of `tests/fixtures/<name>`."""
    return (FIXTURES / name).read_bytes()


def page(pods: list[dict[str, str]], cursor: str | None) -> bytes:
    """Return one page of RunPod's pod listing; `cursor` None is the last page."""
    more = {"nextCursor": cursor, "hasNextPage": cursor is not None}
    return json.dumps({"pods": pods, "pagination": more}).encode()


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
