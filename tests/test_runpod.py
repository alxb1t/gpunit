import dataclasses
import io
import json
import urllib.error
import urllib.parse
import urllib.request
import urllib.response
from email.message import Message
from pathlib import Path

import pytest

from gpunit.log import Refusal
from gpunit.provider import (
    GpuInfo,
    Lost,
    NoImage,
    PodCost,
    PodInfo,
    Refused,
    Unknown,
    VolumeCost,
    VolumeInfo,
    fingerprint,
)
from gpunit.runpod import API, LOG_IDLE_S, RunPod, _NoRedirect
from gpunit.spec import Spec
from tests.fakes import NONCE, Answer, FakeOpener, fixture, page, quiet
from tests.helpers import IMAGE

KEY = "rpa_test_key"


def runpod(*answers: Answer) -> tuple[RunPod, FakeOpener]:
    opener = FakeOpener(*answers)
    return RunPod({"RUNPOD_API_KEY": KEY}, opener=opener), opener


SPEC = Spec(
    project="isekai",
    image=IMAGE,
    gpus=("RTX 4090",),
    vram_gb=24,
    ceiling_s=2700,
    disk_gb=50,
    env={"MODE": "render", "GPUNIT_CEILING": "1"},
)


@pytest.mark.spec("session:place:under-floor-skipped")
def test_gpu_reads_the_memory_and_the_secure_price() -> None:
    provider, opener = runpod((200, fixture("gpu.json")))

    assert provider.gpu("NVIDIA GeForce RTX 4090") == GpuInfo(vram_gb=24, hourly=0.69)
    url = opener.requests[0].full_url
    assert url.endswith("/catalog/gpus/NVIDIA%20GeForce%20RTX%204090")
    assert opener.requests[0].get_header("Authorization") == f"Bearer {KEY}"
    assert opener.requests[0].get_header("User-agent") == "gpunit/0.6.0"


@pytest.mark.spec("session:place:unknown-card-refuses")
def test_a_gpu_404_is_unknown() -> None:
    provider, _ = runpod((404, fixture("problem.json")))

    with pytest.raises(Unknown, match="RTX 9999"):
        provider.gpu("RTX 9999")


@pytest.mark.spec("session:volume:pins-datacenter")
def test_the_create_carries_the_volumes_datacenter() -> None:
    provider, opener = runpod(
        (200, fixture("volume.json")), (201, fixture("pod_created.json"))
    )
    spec = dataclasses.replace(SPEC, volume="v1")

    assert provider.volume("v1") == VolumeInfo(datacenter="EU-RO-1", size_gb=100)
    provider.create(
        spec, "RTX 4090", "ssh-ed25519 AAAA gpunit-isekai", 2700, nonce=NONCE
    )

    body = opener.sent()
    assert body["dataCenterIds"] == ["EU-RO-1"]
    assert body["mounts"] == {"network": [{"volumeId": "v1", "path": "/runpod-volume"}]}


@pytest.mark.spec("session:volume:the-pod-is-told")
def test_the_pod_is_told_its_volume() -> None:
    provider, opener = runpod(
        (200, fixture("volume.json")), (201, fixture("pod_created.json"))
    )
    spec = dataclasses.replace(SPEC, volume="v1")

    provider.create(
        spec, "RTX 4090", "ssh-ed25519 AAAA gpunit-isekai", 2700, nonce=NONCE
    )

    assert opener.sent()["env"] == {
        "MODE": "render",
        "GPUNIT_CEILING": "2700",
        "PUBLIC_KEY": "ssh-ed25519 AAAA gpunit-isekai",
        "GPUNIT_NONCE": NONCE,
        "GPUNIT_VOLUME_ID": "v1",
        "GPUNIT_VOLUME_PATH": "/runpod-volume",
    }


@pytest.mark.spec("session:create:secure-and-22")
def test_the_create_is_secure_and_exposes_22_only() -> None:
    provider, opener = runpod((201, fixture("pod_created.json")))

    pod_id = provider.create(
        SPEC, "RTX 4090", "ssh-ed25519 AAAA gpunit-isekai", 2700, nonce=NONCE
    )

    assert pod_id == "pod-abc123"
    body = opener.sent()
    assert body["cloud"] == "SECURE"
    assert body["ports"] == ["22/tcp"]
    assert body["name"] == "gpunit-isekai"
    assert body["image"] == IMAGE


@pytest.mark.spec("spec:ceiling:reaches-the-pod")
def test_the_ceiling_and_the_key_win_over_the_spec_env() -> None:
    provider, opener = runpod((201, fixture("pod_created.json")))

    provider.create(
        SPEC, "RTX 4090", "ssh-ed25519 AAAA gpunit-isekai", 2700, nonce=NONCE
    )

    assert opener.sent()["env"] == {
        "MODE": "render",
        "GPUNIT_CEILING": "2700",
        "PUBLIC_KEY": "ssh-ed25519 AAAA gpunit-isekai",
        "GPUNIT_NONCE": NONCE,
    }


@pytest.mark.spec("session:place:400-moves-on")
def test_a_400_create_is_refused_with_the_problem() -> None:
    provider, _ = runpod((400, fixture("problem.json")))

    with pytest.raises(Refused, match="Bad Request: There are no instances"):
        provider.create(SPEC, "RTX 4090", "key", 2700, nonce=NONCE)


@pytest.mark.spec("session:lost:5xx-exits-3")
@pytest.mark.parametrize(
    "answer",
    [(503, b"upstream unavailable"), (201, b"{}"), (201, b"not json")],
    ids=["503", "201-no-id", "201-garbled"],
)
def test_a_5xx_or_a_201_without_an_id_is_lost(answer: Answer) -> None:
    provider, _ = runpod(answer)

    with pytest.raises(Lost):
        provider.create(SPEC, "RTX 4090", "key", 2700, nonce=NONCE)


@pytest.mark.spec("session:lost:transport-exits-3")
@pytest.mark.parametrize("fault", [urllib.error.URLError("refused"), TimeoutError()])
def test_a_transport_failure_is_lost(fault: Exception) -> None:
    provider, _ = runpod(fault)

    with pytest.raises(Lost, match="got no answer"):
        provider.create(SPEC, "RTX 4090", "key", 2700, nonce=NONCE)


@pytest.mark.spec("session:wait:failed-poll-is-not-yet")
def test_get_reads_the_direct_ssh_address_or_none() -> None:
    provider, _ = runpod(
        (200, fixture("pod_created.json")),
        (200, fixture("pod_pending.json")),
        (500, b"oops"),
        (200, fixture("pod_running.json")),
    )

    assert provider.get("pod-abc123") == PodInfo("PENDING", None, None)
    assert provider.get("pod-abc123") == PodInfo("RUNNING", None, None)
    assert provider.get("pod-abc123") is None
    assert provider.get("pod-abc123") == PodInfo("RUNNING", "203.0.113.7", 40022)


@pytest.mark.spec("session:hostkey:match-recorded")
def test_the_logs_last_fingerprint_wins() -> None:
    provider, opener = runpod((200, fixture("log.txt")))

    lines = provider.log("pod-abc123", tail=5000)

    assert "tail=5000&source=container" in opener.requests[0].full_url
    assert (
        fingerprint(lines, NONCE)
        == "SHA256:LastKeyWins+/111111111111111111111111111111"
    )
    assert (
        fingerprint(lines[:3], NONCE)
        == "SHA256:FirstKeyFromAnEarlierBoot0000000000000000000"
    )
    assert fingerprint(["echo gpunit host key: SHA256:abc"], NONCE) is None


def stamped(*events: tuple[str | None, str]) -> bytes:
    """Return a log stream whose events carry RunPod's `ts`, as a live pod's do."""
    body = []
    for ts, line in events:
        event = {"source": "container", "line": line} | ({"ts": ts} if ts else {})
        body.append(f"data: {json.dumps(event)}\n\n")
    return "".join(body).encode()


@pytest.mark.spec("serve:wait:log-kept")
def test_a_since_read_takes_the_tail_from_that_second_on() -> None:
    # RunPod's own `since` sends no past line (0010 design D14): the read is the tail's.
    provider, opener = runpod(
        (
            200,
            stamped(
                ("2026-10-07T09:59:59.999999999Z", "an earlier boot's line"),
                ("2026-10-07T10:00:00.250000000Z", "2026-10-07T10:00:00Z step: sshd"),
                (None, "a line with no stamp"),
                (
                    "2026-10-07T10:00:05.000000000Z",
                    "2026-10-07T10:00:05Z step: the command",
                ),
            ),
        )
    )

    lines = provider.log("pod-abc123", tail=50, since="2026-10-07T10:00:00Z")

    query = urllib.parse.urlsplit(opener.requests[0].full_url).query
    assert query == "tail=5000&source=container"
    assert lines == [
        "2026-10-07T10:00:00Z step: sshd",
        "a line with no stamp",
        "2026-10-07T10:00:05Z step: the command",
    ]


@pytest.mark.spec("serve:wait:log-kept")
def test_a_tail_read_keeps_every_stamp() -> None:
    # The twin: without `since`, the line stamped before it is read too.
    provider, opener = runpod(
        (200, stamped(("2026-10-07T09:59:59Z", "an earlier boot's line")))
    )

    assert provider.log("pod-abc123", tail=50) == ["an earlier boot's line"]
    query = urllib.parse.urlsplit(opener.requests[0].full_url).query
    assert query == "tail=50&source=container"


@pytest.mark.spec("session:hostkey:quiet-stream-ends-read")
def test_a_quiet_stream_ends_the_read() -> None:
    # log.txt holds an earlier boot's host-key line, then this boot's.
    provider, opener = runpod(quiet(fixture("log.txt")))

    lines = provider.log("pod-abc123", tail=5000)

    assert (
        fingerprint(lines, NONCE)
        == "SHA256:LastKeyWins+/111111111111111111111111111111"
    )
    assert opener.timeouts == [LOG_IDLE_S]


class _Found(urllib.response.addinfourl):
    msg = "Found"


class Redirecting(urllib.request.BaseHandler):
    """Answer every HTTPS request with a 302 to another host; record each one."""

    # Ahead of urllib's own HTTPSHandler, so no request leaves the test.
    handler_order = 100

    def __init__(self) -> None:
        self.opened: list[tuple[str, str | None]] = []

    def https_open(self, req: urllib.request.Request) -> _Found:
        self.opened.append((req.host, req.get_header("Authorization")))
        headers = Message()
        headers["Location"] = "https://elsewhere.example/pods"
        return _Found(io.BytesIO(b""), headers, req.full_url, 302)


@pytest.mark.spec("spec:secrets:redirect-not-followed")
def test_a_redirect_is_not_followed(monkeypatch: pytest.MonkeyPatch) -> None:
    # The baseline: an opener without `_NoRedirect` sends the key to the new host.
    unguarded = Redirecting()
    exposed = RunPod(
        {"RUNPOD_API_KEY": KEY}, opener=urllib.request.build_opener(unguarded)
    )
    with pytest.raises(Lost, match="HTTP 302"):
        exposed.create(SPEC, "RTX 4090", "key", 2700, nonce=NONCE)
    assert ("elsewhere.example", f"Bearer {KEY}") in unguarded.opened

    redirecting = Redirecting()
    build = urllib.request.build_opener
    monkeypatch.setattr(
        urllib.request, "build_opener", lambda *handlers: build(*handlers, redirecting)
    )
    provider = RunPod({"RUNPOD_API_KEY": KEY})

    with pytest.raises(Lost, match="HTTP 302"):
        provider.create(SPEC, "RTX 4090", "key", 2700, nonce=NONCE)
    assert redirecting.opened == [("api.runpod.io", f"Bearer {KEY}")]
    request = urllib.request.Request(API + "/pods")
    elsewhere = "https://elsewhere.example/pods"
    found = _NoRedirect().redirect_request(
        request, io.BytesIO(), 302, "Found", Message(), elsewhere
    )
    assert found is None


@pytest.mark.spec("session:one:listed-refuses")
def test_the_listing_names_the_projects_live_pods() -> None:
    provider, _ = runpod((200, fixture("pods_page.json")))

    listed = provider.list("isekai", IMAGE)

    assert listed == [("pod-abc123", "RUNNING"), ("pod-old", "EXITED")]


@pytest.mark.spec("session:one:look-alike-image-ignored")
def test_a_look_alike_image_is_not_ours() -> None:
    lookalike = {
        "id": "p9",
        "name": "gpunit-isekai",
        "status": "RUNNING",
        "image": "ghcr.io/alxb1t/isekai-tools:latest",
    }
    provider, _ = runpod((200, page([lookalike], None)))

    assert provider.list("isekai", IMAGE) == []


@pytest.mark.spec("session:one:listed-refuses")
def test_a_pod_of_our_name_with_no_image_fails_the_listing() -> None:
    bare = {"id": "p9", "name": "gpunit-isekai", "status": "RUNNING", "image": ""}
    provider, _ = runpod((200, page([bare], None)))

    with pytest.raises(NoImage, match="p9"):
        provider.list("isekai", IMAGE)


@pytest.mark.spec("session:down:unreadable-listing-fails")
def test_the_listing_walks_the_cursor_and_refuses_one_answered_twice() -> None:
    ours = {"id": "p1", "name": "gpunit-isekai", "status": "RUNNING", "image": IMAGE}
    provider, opener = runpod((200, page([ours], "c1")), (200, page([], "c1")))

    with pytest.raises(Lost, match="cursor c1 twice"):
        provider.list("isekai", IMAGE)
    assert "cursor=c1" in opener.requests[1].full_url


@pytest.mark.spec("session:down:unreadable-listing-fails")
def test_an_unreadable_listing_is_lost() -> None:
    provider, _ = runpod((500, fixture("problem.json")))

    with pytest.raises(Lost, match="HTTP 500"):
        provider.list("isekai", IMAGE)


@pytest.mark.spec("session:down:404-keeps-record")
def test_delete_returns_the_status_and_0_without_an_answer() -> None:
    provider, opener = runpod((204, b""), (404, fixture("problem.json")), OSError())

    assert [provider.delete("p1") for _ in range(3)] == [204, 404, 0]
    assert opener.requests[0].get_method() == "DELETE"


@pytest.mark.spec("boot:stop:ceiling")
def test_stop_posts_the_stop_action() -> None:
    provider, opener = runpod((200, b"{}"))

    assert provider.stop("p1") == 200
    assert opener.requests[0].full_url.endswith("/pods/p1/action")
    assert opener.sent() == {"action": "stop"}


@pytest.mark.spec("spec:secrets:no-key-refused")
def test_no_key_refuses_at_construction() -> None:
    with pytest.raises(Refusal, match="RUNPOD_API_KEY"):
        RunPod({}, opener=FakeOpener())


@pytest.mark.spec("spec:secrets:dotenv-ignored")
def test_a_dotenv_beside_the_spec_is_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RUNPOD_API_KEY", raising=False)
    (tmp_path / ".env").write_text(f"RUNPOD_API_KEY={KEY}\n", encoding="utf-8")

    with pytest.raises(Refusal, match="RUNPOD_API_KEY"):
        RunPod(opener=FakeOpener())


WEEK = ("2026-10-06T00:00:00Z", "2026-10-13T00:00:00Z")


def billing_query(opener: FakeOpener) -> tuple[str, dict[str, list[str]]]:
    url = urllib.parse.urlsplit(opener.requests[0].full_url)
    return url.path, urllib.parse.parse_qs(url.query)


@pytest.mark.spec("spend:report:total-is-the-providers")
def test_pod_billing_takes_each_records_total_amount() -> None:
    provider, opener = runpod((200, fixture("billing_pods.json")))

    assert provider.pod_billing(*WEEK) == [
        PodCost("dnlnasr56lt2uq", "2026-10-07T00:00:00Z", 0.00341992499306798),
        PodCost("gypz8tpe5pbl50", "2026-10-10T00:00:00Z", 0.09196642320603132),
        PodCost("fh5qgxf87eu6nr", "2026-10-12T00:00:00Z", 0.5304889967665076),
    ]
    assert billing_query(opener) == (
        "/v2/billing/pods",
        {"bucketSize": ["day"], "startTime": [WEEK[0]], "endTime": [WEEK[1]]},
    )


@pytest.mark.spec("spend:report:total-is-the-providers")
def test_volume_billing_takes_each_records_total_amount() -> None:
    provider, opener = runpod((200, fixture("billing_volumes.json")))

    assert provider.volume_billing(*WEEK) == [
        VolumeCost("3vh5895lws", "2026-10-06T00:00:00Z", 0.01750000042375177),
        VolumeCost("db7sc8cild", "2026-10-06T00:00:00Z", 0.04666666779667139),
        VolumeCost("db7sc8cild", "2026-10-12T00:00:00Z", 0.031111111864447594),
    ]
    assert billing_query(opener)[0] == "/v2/billing/network-volumes"


@pytest.mark.spec("spend:report:total-is-the-providers")
@pytest.mark.parametrize(
    "answer",
    [
        (500, fixture("problem.json")),
        (200, b'{"records": [{"ID": "p", "startTime": "t"}]}'),
        (200, b'{"records": [{"ID": "p", "startTime": "t", "totalAmount": "1"}]}'),
        urllib.error.URLError("down"),
    ],
    ids=["500", "no-amount", "string-amount", "transport"],
)
@pytest.mark.parametrize(
    ("read", "key"),
    [("pod_billing", b"podId"), ("volume_billing", b"networkVolumeId")],
    ids=["pod_billing", "volume_billing"],
)
def test_an_unreadable_billing_is_lost(answer: Answer, read: str, key: bytes) -> None:
    # Each record carries the id its read expects, so only the amount is at fault.
    if isinstance(answer, tuple):
        answer = (answer[0], answer[1].replace(b'"ID"', b'"' + key + b'"'))
    provider, _ = runpod(answer)

    with pytest.raises(Lost, match="billing read"):
        getattr(provider, read)(*WEEK)


@pytest.mark.spec("volume:up:datacenter-from-stock")
def test_stock_reads_the_secure_pod_stock_and_drops_none() -> None:
    provider, opener = runpod((200, fixture("gpu_stock.json")))

    assert provider.stock("NVIDIA A40") == [("EU-RO-1", "MEDIUM"), ("CA-MTL-4", "HIGH")]
    url = urllib.parse.urlsplit(opener.requests[0].full_url)
    assert url.path == "/v2/catalog/gpus/NVIDIA%20A40"
    assert urllib.parse.parse_qs(url.query) == {
        "include": ["AVAILABILITY"],
        "product": ["POD"],
        "cloud": ["SECURE"],
    }


@pytest.mark.spec("volume:up:datacenter-from-stock")
def test_a_card_out_of_stock_everywhere_has_no_data_centre() -> None:
    provider, _ = runpod((200, fixture("gpu.json")))

    assert provider.stock("NVIDIA GeForce RTX 4090") == []


@pytest.mark.spec("volume:up:datacenter-from-stock")
@pytest.mark.parametrize(
    ("answer", "fault"),
    [((404, fixture("problem.json")), Unknown), ((500, b"oops"), Lost)],
    ids=["404", "500"],
)
def test_an_unreadable_stock_is_unknown_or_lost(
    answer: Answer, fault: type[Exception]
) -> None:
    provider, _ = runpod(answer)

    with pytest.raises(fault):
        provider.stock("NVIDIA A40")


@pytest.mark.spec("volume:up:datacenter-from-stock")
def test_the_standard_data_centres_are_read() -> None:
    provider, opener = runpod((200, fixture("datacenters.json")), (500, b"oops"))

    assert provider.volume_datacenters() == {"EU-RO-1", "CA-MTL-4"}
    assert opener.requests[0].full_url.endswith(
        "/catalog/datacenters?networkVolumeTypes=STANDARD"
    )
    with pytest.raises(Lost, match="data centre read"):
        provider.volume_datacenters()


@pytest.mark.spec("volume:up:datacenter-from-stock")
def test_the_volume_create_names_the_standard_tier() -> None:
    provider, opener = runpod((201, fixture("volume_created.json")))

    assert provider.create_volume("gpunit-isekai", 60, "EU-RO-1") == "vol-abc123"
    assert opener.requests[0].get_method() == "POST"
    assert opener.requests[0].full_url.endswith("/network-volumes")
    assert opener.sent() == {
        "name": "gpunit-isekai",
        "size": 60,
        "dataCenter": "EU-RO-1",
        "type": "STANDARD",
    }


@pytest.mark.spec("volume:up:datacenter-from-stock")
@pytest.mark.parametrize("status", [400, 422])
def test_a_refused_volume_create_is_refused(status: int) -> None:
    provider, _ = runpod((status, fixture("problem.json")))

    with pytest.raises(Refused, match="no instances"):
        provider.create_volume("gpunit-isekai", 60, "EU-RO-1")


@pytest.mark.spec("volume:up:lost-create-exits-3")
@pytest.mark.parametrize(
    "answer",
    [(503, b"upstream unavailable"), (201, b"{}"), urllib.error.URLError("down")],
    ids=["503", "201-no-id", "transport"],
)
def test_a_volume_create_without_an_id_is_lost(answer: Answer) -> None:
    provider, _ = runpod(answer)

    with pytest.raises(Lost, match="volume create"):
        provider.create_volume("gpunit-isekai", 60, "EU-RO-1")


@pytest.mark.spec("volume:down:sweeps-by-name")
def test_the_volume_listing_walks_the_cursor_and_keeps_the_name() -> None:
    ours = {"id": "v1", "name": "gpunit-isekai", "dataCenter": "EU-RO-1"}
    other = {"id": "v2", "name": "gpunit-isekai-old", "dataCenter": "EU-RO-1"}
    again = {"id": "v3", "name": "gpunit-isekai", "dataCenter": "CA-MTL-4"}
    provider, opener = runpod(
        (200, page([ours, other], "c1", "networkVolumes")),
        (200, page([again], None, "networkVolumes")),
    )

    assert provider.volumes("gpunit-isekai") == ["v1", "v3"]
    assert opener.requests[0].full_url.endswith("/network-volumes?limit=1000")
    assert "cursor=c1" in opener.requests[1].full_url


@pytest.mark.spec("volume:down:sweeps-by-name")
def test_an_unreadable_volume_listing_is_lost() -> None:
    provider, _ = runpod(
        (200, page([], "c1", "networkVolumes")), (200, page([], "c1", "networkVolumes"))
    )

    with pytest.raises(Lost, match="volume listing answered cursor c1 twice"):
        provider.volumes("gpunit-isekai")
    provider, _ = runpod((500, fixture("problem.json")))
    with pytest.raises(Lost, match="volume listing returned HTTP 500"):
        provider.volumes("gpunit-isekai")


@pytest.mark.spec("volume:down:sweeps-by-name")
def test_delete_volume_returns_the_status_and_0_without_an_answer() -> None:
    provider, opener = runpod((204, b""), (409, fixture("problem.json")), OSError())

    assert [provider.delete_volume("v1") for _ in range(3)] == [204, 409, 0]
    assert opener.requests[0].get_method() == "DELETE"
    assert opener.requests[0].full_url.endswith("/network-volumes/v1")
