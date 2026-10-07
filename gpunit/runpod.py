"""RunPod's REST v2 behind the `Provider` seam, on `urllib`."""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from gpunit import __version__, log
from gpunit.provider import (
    GpuInfo,
    Lost,
    NoImage,
    PodInfo,
    Refused,
    Unknown,
    VolumeInfo,
    pod_name,
)
from gpunit.spec import Spec

API = "https://api.runpod.io/v2"
# Bounded, so a stalled read cannot hold a poll past its deadline.
TIMEOUT_S = 30
# The log stream stays open; what arrived by then is what is read.
LOG_READ_S = 10
MAX_PAGES = 100
VOLUME_PATH = "/runpod-volume"


@dataclass(frozen=True)
class _Answer:
    status: int  # 0 when no answer came
    body: bytes

    def json(self, status: int) -> Any:  # noqa: ANN401 — any shape until read
        """Return the parsed body; raise `ValueError` unless the status is `status`."""
        if self.status != status:
            raise ValueError(self.status)
        return json.loads(self.body)


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
        self._opener = opener or urllib.request.build_opener()
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

    def create(self, spec: Spec, gpu: str, pubkey: str, ceiling_s: int) -> str:
        """Return the new pod's id; raise `Refused` on a 400, else `Lost`."""
        card: dict[str, object] = {"id": gpu, "count": 1}
        if spec.ram_gb is not None:
            card["minRamPerGpu"] = spec.ram_gb
        if spec.cuda is not None:
            card["minCudaVersion"] = spec.cuda
        body: dict[str, object] = {
            "name": pod_name(spec.project),
            "image": spec.image,
            "gpu": card,
            "ports": ["22/tcp"],
            "disk": spec.disk_gb,
            "cloud": "SECURE",
            "env": {**spec.env, "PUBLIC_KEY": pubkey, "GPUNIT_CEILING": str(ceiling_s)},
        }
        if spec.volume is not None:
            # The protocol's create names no data centre: the volume read sets it.
            datacenter = (
                self._datacenters.get(spec.volume)
                or self.volume(spec.volume).datacenter
            )
            body["mounts"] = {
                "network": [{"volumeId": spec.volume, "path": VOLUME_PATH}]
            }
            body["dataCenterIds"] = [datacenter]
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

    def log(self, pod_id: str, *, tail: int) -> list[str]:
        """Return the container log's last `tail` lines; empty on a failed read."""
        query = urllib.parse.urlencode({"tail": tail, "source": "container"})
        request = self._request("GET", f"/pods/{_quote(pod_id)}/logs?{query}")
        lines: list[str] = []
        deadline = time.monotonic() + LOG_READ_S
        try:
            with self._opener.open(request, timeout=LOG_READ_S) as stream:
                while time.monotonic() < deadline:
                    raw = stream.readline()
                    if not raw:
                        break
                    lines.extend(_event_line(raw))
        except (OSError, ValueError):
            pass  # what arrived before the fault is what was read
        return lines

    def list(self, project: str, image: str) -> list[tuple[str, str]]:
        """Return (id, status) of each live project pod; raise `Lost` or `NoImage`."""
        name, repo = pod_name(project), image.split("@", 1)[0]
        live: list[tuple[str, str]] = []
        cursor: str | None = None
        seen: set[str] = set()
        for _ in range(MAX_PAGES):
            query = {"limit": 1000} | ({"cursor": cursor} if cursor else {})
            answer = self._call("GET", f"/pods?{urllib.parse.urlencode(query)}")
            try:
                page = answer.json(200)
                pods, pagination = page["pods"], page["pagination"]
                for pod in pods:
                    if pod["name"] != name or pod["status"] == "TERMINATED":
                        continue
                    if not pod.get("image"):
                        raise NoImage(
                            f"pod {pod['id']} is named {name!r} but carries no image"
                        )
                    if _ours(pod["image"], repo):
                        live.append((str(pod["id"]), str(pod["status"])))
                if not pagination["hasNextPage"]:
                    return live
                cursor = str(pagination["nextCursor"])
            except (TypeError, KeyError, ValueError):
                raise Lost(_report("pod listing", answer)) from None
            if cursor in seen:
                raise Lost(f"the pod listing answered cursor {cursor} twice")
            seen.add(cursor)
        raise Lost(f"the pod listing ran past {MAX_PAGES} pages")

    def delete(self, pod_id: str) -> int:
        """Delete the pod and return the HTTP status; 0 when no answer came."""
        answer = self._call("DELETE", f"/pods/{_quote(pod_id)}")
        if answer.status not in (200, 204):
            log.say(_report(f"delete of {pod_id}", answer))
        return answer.status

    def stop(self, pod_id: str) -> int:
        """Stop the pod and return the HTTP status; 0 when no answer came."""
        return self._call(
            "POST", f"/pods/{_quote(pod_id)}/action", {"action": "stop"}
        ).status

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


def _event_line(raw: bytes) -> list[str]:
    text = raw.decode("utf-8", errors="replace").rstrip("\r\n")
    if not text.startswith("data: "):
        return []
    try:
        line = json.loads(text[len("data: ") :]).get("line")
    except (ValueError, AttributeError):
        return []
    return [line] if isinstance(line, str) else []


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
