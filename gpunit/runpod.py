"""RunPod's REST v2 behind the `Provider` seam, on `urllib`."""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from email.message import Message
from typing import IO, Any, TypeVar

from gpunit import __version__, log
from gpunit.provider import (
    DELETED,
    GpuInfo,
    Lost,
    NoImage,
    PodCost,
    PodInfo,
    Refused,
    Unknown,
    VolumeCost,
    VolumeInfo,
    pod_name,
)
from gpunit.spec import Spec

API = "https://api.runpod.io/v2"
# Bounded, so a stalled read cannot hold a poll past its deadline.
TIMEOUT_S = 30
# The log stream stays open: a read ends once it goes quiet, or at the cap.
LOG_READ_S = 10
LOG_IDLE_S = 3
MAX_PAGES = 100
# The most lines a log read backfills.
MAX_TAIL = 5000
VOLUME_PATH = "/runpod-volume"

T = TypeVar("T")


@dataclass(frozen=True)
class _Answer:
    status: int  # 0 when no answer came
    body: bytes

    def json(self, status: int) -> Any:  # noqa: ANN401 — any shape until read
        """Return the parsed body; raise `ValueError` unless the status is `status`."""
        if self.status != status:
            raise ValueError(self.status)
        return json.loads(self.body)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Follow no redirect: urllib would carry the key's header to the new host."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: Message,
        newurl: str,
    ) -> None:
        """Return None, so the 3xx is raised as an `HTTPError` and read as one."""
        return None


class RunPod:
    """RunPod's REST v2; the key travels only in a request header."""

    def __init__(
        self,
        environ: Mapping[str, str] = os.environ,
        opener: urllib.request.OpenerDirector | None = None,
    ) -> None:
        """Read `RUNPOD_API_KEY` from the environment; refuse when it is empty."""
        self._key = environ.get("RUNPOD_API_KEY", "")
        if not self._key:
            log.refuse("RUNPOD_API_KEY is empty; export it (gpunit reads no .env)")
        self._opener = opener or urllib.request.build_opener(_NoRedirect)
        self._datacenters: dict[str, str] = {}

    def gpu(self, name: str) -> GpuInfo:
        """Return the card's catalogue entry; raise `Unknown` on a 404, else `Lost`."""
        answer = self._call("GET", f"/catalog/gpus/{_quote(name)}")
        if answer.status == 404:
            raise Unknown(f"RunPod's catalogue does not know {name!r}")
        try:
            body = answer.json(200)
            return GpuInfo(
                vram_gb=int(body["memory"]), hourly=float(body["price"]["secure"])
            )
        except (TypeError, KeyError, ValueError):
            raise Lost(_report(f"catalogue read of {name!r}", answer)) from None

    def volume(self, volume_id: str) -> VolumeInfo:
        """Return the volume; raise `Unknown` on a 404, else `Lost`."""
        answer = self._call("GET", f"/network-volumes/{_quote(volume_id)}")
        if answer.status == 404:
            raise Unknown(f"RunPod does not know volume {volume_id!r}")
        try:
            body = answer.json(200)
            info = VolumeInfo(
                datacenter=str(body["dataCenter"]), size_gb=int(body["size"])
            )
        except (TypeError, KeyError, ValueError):
            raise Lost(_report(f"volume read of {volume_id!r}", answer)) from None
        self._datacenters[volume_id] = info.datacenter
        return info

    def create(
        self, spec: Spec, gpu: str, pubkey: str, ceiling_s: int, *, nonce: str
    ) -> str:
        """Return the new pod's id; raise `Refused` on a 400, else `Lost`."""
        card: dict[str, object] = {"id": gpu, "count": 1}
        if spec.ram_gb is not None:
            card["minRamPerGpu"] = spec.ram_gb
        if spec.cuda is not None:
            card["minCudaVersion"] = spec.cuda
        env = {
            **spec.env,
            "PUBLIC_KEY": pubkey,
            "GPUNIT_CEILING": str(ceiling_s),
            "GPUNIT_NONCE": nonce,
        }
        placement: dict[str, object] = {}
        if spec.volume is not None:
            # The protocol's create names no data centre: the volume read sets it.
            datacenter = (
                self._datacenters.get(spec.volume)
                or self.volume(spec.volume).datacenter
            )
            placement = {
                "mounts": {"network": [{"volumeId": spec.volume, "path": VOLUME_PATH}]},
                "dataCenterIds": [datacenter],
            }
            # The pod reads its volume in gpunit's words, not the provider's (0004 D7).
            env |= {"GPUNIT_VOLUME_ID": spec.volume, "GPUNIT_VOLUME_PATH": VOLUME_PATH}
        body: dict[str, object] = {
            "name": pod_name(spec.project),
            "image": spec.image,
            "gpu": card,
            "ports": ["22/tcp"],
            "disk": spec.disk_gb,
            "cloud": "SECURE",
            "env": env,
            **placement,
        }
        answer = self._call("POST", "/pods", body)
        if answer.status == 400:
            raise Refused(_report(f"create on {gpu!r}", answer))
        try:
            pod_id = answer.json(201)["id"]
        except (TypeError, KeyError, ValueError):
            pod_id = None
        if isinstance(pod_id, str) and pod_id:
            return pod_id
        raise Lost(_report(f"create on {gpu!r}", answer))

    def get(self, pod_id: str) -> PodInfo | None:
        """Return the pod, or None on any failed read."""
        answer = self._call("GET", f"/pods/{_quote(pod_id)}")
        try:
            body = answer.json(200)
            direct = (body.get("ssh") or {}).get("direct") or {}
            port = direct.get("port")
            return PodInfo(
                status=str(body["status"]),
                host=direct.get("host") or None,
                port=int(port) if port else None,
            )
        except (AttributeError, TypeError, KeyError, ValueError):
            return None

    def log(self, pod_id: str, *, tail: int, since: str | None = None) -> list[str]:
        """Return the container log's last `tail` lines; empty on a failed read.

        With `since`, an RFC 3339 time, return the lines from then on instead.
        """
        # RunPod's own `since` sends no past line, so it is the tail's: 0010 design D14.
        query = urllib.parse.urlencode(
            {"tail": tail if since is None else MAX_TAIL, "source": "container"}
        )
        request = self._request("GET", f"/pods/{_quote(pod_id)}/logs?{query}")
        events: list[tuple[str | None, str]] = []
        deadline = time.monotonic() + LOG_READ_S
        try:
            # A quiet stream raises `TimeoutError`, an `OSError`, after LOG_IDLE_S.
            with self._opener.open(request, timeout=LOG_IDLE_S) as stream:
                while time.monotonic() < deadline:
                    raw = stream.readline()
                    if not raw:
                        break
                    events.extend(_event(raw))
        except (OSError, ValueError):
            pass  # what arrived before the fault is what was read
        # To the second: `since` is stamped in seconds, `ts` in nanoseconds.
        return [
            line
            for ts, line in events
            if since is None or ts is None or ts[:19] >= since[:19]
        ]

    def pod_billing(self, start: str, end: str) -> list[PodCost]:
        """Return each pod's charge per UTC day in `[start, end)`; raise `Lost`."""
        records = self._billing("pods", "podId", start, end)
        return [PodCost(pod_id, day, amount) for pod_id, day, amount in records]

    def volume_billing(self, start: str, end: str) -> list[VolumeCost]:
        """Return each volume's charge per UTC day in `[start, end)`; raise `Lost`."""
        records = self._billing("network-volumes", "networkVolumeId", start, end)
        return [VolumeCost(volume, day, amount) for volume, day, amount in records]

    def _billing(
        self, kind: str, key: str, start: str, end: str
    ) -> list[tuple[str, str, float]]:
        query = {"bucketSize": "day", "startTime": start, "endTime": end}
        answer = self._call("GET", f"/billing/{kind}?{urllib.parse.urlencode(query)}")
        try:
            return [
                (str(record[key]), str(record["startTime"]), _amount(record))
                for record in answer.json(200)["records"]
            ]
        except (TypeError, KeyError, ValueError):
            raise Lost(_report(f"{kind} billing read", answer)) from None

    def volumes(self, name: str) -> list[str]:
        """Return the ids of the volumes named `name`; raise `Lost`."""
        return self._walk(
            "/network-volumes",
            "networkVolumes",
            "volume listing",
            lambda volume: str(volume["id"]) if volume["name"] == name else None,
        )

    def _walk(
        self,
        path: str,
        key: str,
        what: str,
        pick: Callable[[dict[str, Any]], T | None],
    ) -> list[T]:
        """Return what `pick` keeps of every item on every page; raise `Lost`."""
        kept: list[T] = []
        cursor: str | None = None
        seen: set[str] = set()
        for _ in range(MAX_PAGES):
            query = {"limit": 1000} | ({"cursor": cursor} if cursor else {})
            answer = self._call("GET", f"{path}?{urllib.parse.urlencode(query)}")
            try:
                page = answer.json(200)
                items, pagination = page[key], page["pagination"]
                kept.extend(x for item in items if (x := pick(item)) is not None)
                if not pagination["hasNextPage"]:
                    return kept
                cursor = str(pagination["nextCursor"])
            except (TypeError, KeyError, ValueError):
                raise Lost(_report(what, answer)) from None
            if cursor in seen:
                raise Lost(f"the {what} answered cursor {cursor} twice")
            seen.add(cursor)
        raise Lost(f"the {what} ran past {MAX_PAGES} pages")

    def delete(self, pod_id: str) -> int:
        """Delete the pod and return the HTTP status; 0 when no answer came."""
        answer = self._call("DELETE", f"/pods/{_quote(pod_id)}")
        if answer.status not in DELETED:
            log.say(_report(f"delete of {pod_id}", answer))
        return answer.status

    def stop(self, pod_id: str) -> int:
        """Stop the pod and return the HTTP status; 0 when no answer came."""
        return self._call(
            "POST", f"/pods/{_quote(pod_id)}/action", {"action": "stop"}
        ).status

    def stock(self, card: str) -> list[tuple[str, str]]:
        """Return (data centre, availability) where the card is in stock.

        Raise `Unknown` on a 404, else `Lost`. e.g. [("EU-RO-1", "HIGH")]
        """
        query = {"include": "AVAILABILITY", "product": "POD", "cloud": "SECURE"}
        path = f"/catalog/gpus/{_quote(card)}?{urllib.parse.urlencode(query)}"
        answer = self._call("GET", path)
        if answer.status == 404:
            raise Unknown(f"RunPod's catalogue does not know {card!r}")
        try:
            # RunPod omits `dataCenters` when the card is out of stock everywhere.
            stocked = [
                (str(dc["id"]), str(dc["availability"]))
                for dc in answer.json(200).get("dataCenters") or []
            ]
        except (AttributeError, TypeError, KeyError, ValueError):
            raise Lost(_report(f"stock read of {card!r}", answer)) from None
        return [(dc, level) for dc, level in stocked if level != "NONE"]

    def volume_datacenters(self) -> set[str]:
        """Return the data centres offering standard volumes; raise `Lost`."""
        answer = self._call("GET", "/catalog/datacenters?networkVolumeTypes=STANDARD")
        try:
            return {str(dc["id"]) for dc in answer.json(200)["dataCenters"]}
        except (TypeError, KeyError, ValueError):
            raise Lost(_report("data centre read", answer)) from None

    def create_volume(self, name: str, size_gb: int, datacenter: str) -> str:
        """Return the new volume's id; raise `Refused` on a 400 or 422, else `Lost`."""
        body = {
            "name": name,
            "size": size_gb,
            "dataCenter": datacenter,
            "type": "STANDARD",
        }
        answer = self._call("POST", "/network-volumes", body)
        call = f"volume create in {datacenter!r}"
        if answer.status in (400, 422):
            raise Refused(_report(call, answer))
        try:
            volume_id = answer.json(201)["id"]
        except (TypeError, KeyError, ValueError):
            volume_id = None
        if isinstance(volume_id, str) and volume_id:
            return volume_id
        raise Lost(_report(call, answer))

    def delete_volume(self, volume_id: str) -> int:
        """Delete the volume and return the HTTP status; 0 when no answer came."""
        answer = self._call("DELETE", f"/network-volumes/{_quote(volume_id)}")
        if answer.status != 204:
            log.say(_report(f"delete of volume {volume_id}", answer))
        return answer.status

    def list(self, project: str, image: str) -> list[tuple[str, str]]:
        """Return (id, status) of each live project pod; raise `Lost` or `NoImage`."""
        name, repo = pod_name(project), image.split("@", 1)[0]

        def live(pod: dict[str, Any]) -> tuple[str, str] | None:
            if pod["name"] != name or pod["status"] == "TERMINATED":
                return None
            if not pod.get("image"):
                raise NoImage(f"pod {pod['id']} is named {name!r} but carries no image")
            if not _ours(pod["image"], repo):
                return None
            return str(pod["id"]), str(pod["status"])

        return self._walk("/pods", "pods", "pod listing", live)

    def _request(
        self, method: str, path: str, body: object = None
    ) -> urllib.request.Request:
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(API + path, data=data, method=method)
        request.add_header("Authorization", f"Bearer {self._key}")
        # RunPod's Cloudflare refuses Python's default agent with a 403 (code 1010).
        request.add_header("User-Agent", f"gpunit/{__version__}")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        return request

    def _call(self, method: str, path: str, body: object = None) -> _Answer:
        request = self._request(method, path, body)
        try:
            with self._opener.open(request, timeout=TIMEOUT_S) as response:
                return _Answer(status=response.status, body=response.read())
        except urllib.error.HTTPError as error:
            return _Answer(status=error.code, body=error.read())
        except (OSError, ValueError):
            return _Answer(status=0, body=b"")


def _quote(part: str) -> str:
    return urllib.parse.quote(part, safe="")


def _ours(pod_image: str, repo: str) -> bool:
    # A look-alike, one that only begins with the repository's name, is not ours.
    return pod_image == repo or pod_image.startswith((repo + "@", repo + ":"))


def _amount(record: dict[str, object]) -> float:
    amount = record["totalAmount"]
    # A string or a bool is no amount the provider charged.
    if isinstance(amount, bool) or not isinstance(amount, int | float):
        raise ValueError(amount)
    return float(amount)


def _event(raw: bytes) -> list[tuple[str | None, str]]:
    """Return the event's `ts` and line, e.g. b'data: {"line": "x"}' → [(None, "x")]."""
    text = raw.decode("utf-8", errors="replace").rstrip("\r\n")
    if not text.startswith("data: "):
        return []
    try:
        event = json.loads(text[len("data: ") :])
        line, ts = event.get("line"), event.get("ts")
    except (ValueError, AttributeError):
        return []
    if not isinstance(line, str):
        return []
    return [(ts if isinstance(ts, str) else None, line)]


def _report(call: str, answer: _Answer) -> str:
    """Return what the answer says, as `<call> returned HTTP <n>: <title>: <detail>`."""
    if answer.status == 0:
        return f"{call} got no answer"
    text = answer.body.decode("utf-8", errors="replace")
    try:
        problem = json.loads(text)
        said = f"{problem['title']}: {problem['detail']}"
    except (ValueError, TypeError, KeyError):
        said = text[:200]
    return f"{call} returned HTTP {answer.status}: {said}"
