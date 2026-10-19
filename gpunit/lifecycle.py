"""Open, report and close one GPU session: `up`, `status`, `down`."""

import functools
import json
import os
import secrets
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import NoReturn, TypeVar

from gpunit import hostkey, ledger, log
from gpunit.provider import (
    DELETED,
    Lost,
    NoImage,
    PodInfo,
    Provider,
    Unknown,
    Unplaceable,
    pod_name,
)
from gpunit.spec import Spec
from gpunit.state import Record, State, Window

POLL_S = 5
# The statuses of a container that is not running; two polls in a row end the wait.
DEAD = ("EXITED", "ERROR", "TERMINATED")
# Checked before the create: a tool missing after it leaves a pod rented.
SSH_TOOLS = ("ssh", "ssh-keygen", "ssh-keyscan")

T = TypeVar("T")


class Stranded(log.Refusal):
    """`up` refused after its create, and its own teardown failed: the pod may bill."""


@dataclass(frozen=True)
class Clock:
    """The time source the waits read; the tests replace it."""

    monotonic: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep


CLOCK = Clock()
# Each pod's nonce for its host-key line; the tests replace it, as they do `CLOCK`.
NONCE: Callable[[], str] = functools.partial(secrets.token_hex, 16)


class DeadPod:
    """Two polls in a row reading a dead status; a failed read is not yet."""

    def __init__(self) -> None:
        """Start with no dead poll seen."""
        self._last = False

    def seen(self, info: PodInfo | None) -> bool:
        """Return True when this poll and the one before both read a dead status."""
        # A restart may show a dead status once, so only a second poll in a row ends it.
        dead = info is not None and info.status in DEAD
        twice, self._last = dead and self._last, dead
        return twice


def up(spec: Spec, provider: Provider, state: State) -> Record:
    """Place a pod, wait for it, verify its host key, and return its record.

    Refuse when it cannot; raise `Lost` when a create's answer did not arrive.
    """
    sweep_window(state, lambda: provider)
    missing = [tool for tool in SSH_TOOLS if shutil.which(tool) is None]
    if missing:
        log.refuse(f"not on PATH: {', '.join(missing)}; install OpenSSH")
    _warn_unignored(state)
    if state.pod.exists():
        log.refuse(f"a pod is already recorded in {state.pod}; run gpunit down")
    if state.pending.exists():
        log.refuse(f"a create may have left a pod ({state.pending}); run gpunit down")
    if spec.volume_gb is not None:
        spec = _in_window(spec, state)
    _refuse_listed(spec, provider)
    if spec.volume is not None:
        try:
            volume = provider.volume(spec.volume)
        except (Unknown, Lost) as fault:
            log.refuse(f"volume {spec.volume} could not be read: {fault}")
        if not spec.allows(volume.datacenter):
            log.refuse(
                f"volume {spec.volume} is in {volume.datacenter}, "
                f"outside datacenters {', '.join(spec.datacenters)}"
            )
    cards = placeable(spec, provider)

    pubkey = state.keygen(pod_name(spec.project))
    nonce = NONCE()
    # Before the create, so a log read `since` it misses none of the pod's lines
    # within the provider's tail (0003 design D2, 0010 design D14).
    created = log.utc()
    state.mark_pending()
    pod_id = _create(spec, provider, cards, pubkey, nonce)
    if pod_id is None:
        state.clear_pending()
        log.refuse("no card in 'gpus' was placed")
    record = Record(pod_id, spec.image, host=None, port=None, created=created)
    state.write(record)
    state.clear_pending()
    log.say(f"pod {pod_id} created; waiting for SSH")

    record = _wait(spec, provider, state, record)
    if reason := hostkey.verify(provider, state, record, nonce, _poll):
        _tear_down(spec, provider, state, reason)
    log.say(f"session up: pod {record.id}, root@{record.host} -p {record.port}")
    return record


def ssh_command(state: State, record: Record) -> list[str]:
    """Return the `ssh` argv that opens a shell on the recorded pod."""
    # Every ssh line is gpunit's own: no ssh_config, no agent key (0002 design D1).
    return [
        "ssh",
        "-F",
        "none",
        "-o",
        "IdentitiesOnly=yes",
        "-i",
        str(state.key),
        "-o",
        f"UserKnownHostsFile={state.known_hosts}",
        "-o",
        "StrictHostKeyChecking=yes",
        f"root@{record.host}",
        "-p",
        str(record.port),
    ]


def ssh(
    state: State, *, execvp: Callable[[str, list[str]], object] | None = None
) -> None:
    """Replace this process with `ssh` to the recorded pod; refuse when it cannot."""
    record = state.read()
    if record is None or record.host is None:
        log.refuse("no session is recorded; run gpunit up")
    try:
        (execvp or os.execvp)("ssh", ssh_command(state, record))
    except OSError as fault:
        log.refuse(f"ssh could not be run: {fault}")


def status(provider: Callable[[], Provider], state: State, *, as_json: bool) -> int:
    """Print the recorded session to stdout, in words or as one JSON object.

    `provider` is built only when a record exists, or a window volume is overdue: no
    record needs no key.
    """
    built = functools.cache(provider)
    sweep_window(state, built)
    window = state.window()
    record = state.read()
    if record is None:
        print("null" if as_json else "no session is recorded")
    else:
        _report(built().get(record.id), record, as_json)
    if window is not None and not as_json:
        ends = "overdue" if window.ends_within(0) else window.ends
        print(f"volume={window.id} datacenter={window.datacenter} ends={ends}")
    return 0


def down(spec: Spec, provider: Provider, state: State) -> int:
    """Delete the recorded pod, sweep every listed one; return 0, or 1 on a fault.

    An overdue window volume is swept after the pods, which may hold it.
    """
    code = _delete_pods(spec, provider, state)
    sweep_window(state, lambda: provider)
    return code


def _delete_pods(spec: Spec, provider: Provider, state: State) -> int:
    failed = False
    record = state.read()
    if record is not None:
        code = provider.delete(record.id)
        if code in DELETED:
            state.clear_session()
            log.say(f"pod {record.id} deleted")
        elif code == 404:
            # A wrong key also gets a 404: a false "gone" leaves a pod billing.
            log.say(
                f"the API does not know pod {record.id}: it may be gone, or the key "
                f"may be wrong; the record is kept until it is confirmed gone"
            )
            failed = True
        else:
            log.say(
                f"delete of pod {record.id} answered HTTP {code}; the record is kept"
            )
            failed = True
    try:
        listed = provider.list(spec.project, spec.image)
    except (Lost, NoImage) as fault:
        log.say(f"no sweep was made: {fault}")
        return 1
    for pod_id, pod_status in listed:
        if record is not None and pod_id == record.id:
            continue
        # Before the delete: a pod the delete fails on is still named.
        ledger.record(spec.project, pod_id, None, spec.image)
        code = provider.delete(pod_id)
        if code in DELETED:
            log.say(f"swept pod {pod_id} ({pod_status})")
        else:
            log.say(f"delete of swept pod {pod_id} answered HTTP {code}")
            failed = True
    if failed:
        return 1
    state.clear_pending()
    if record is None:
        state.clear_session()
    return 0


def delete_volume(provider: Provider, volume_id: str) -> int:
    """Return the delete's status; on a 204, record `deleted` in the ledger."""
    code = provider.delete_volume(volume_id)
    if code == 204:
        ledger.record_deleted(volume_id)
    return code


def sweep_window(state: State, provider: Callable[[], Provider]) -> None:
    """Delete the window volume once its end has passed; build `provider` only then.

    A delete that fails keeps the record, and warns.
    """
    window = state.window()
    if window is None or not window.ends_within(0):
        return
    code = delete_volume(provider(), window.id)
    if code == 204:
        state.clear_window()
        # A record beside the mark: the create came back. 0011 design D2.
        state.clear_volume_pending()
        log.say(f"volume {window.id} passed its ceiling at {window.ends}; deleted")
    else:
        log.say(
            f"warning: volume {window.id} passed its ceiling at {window.ends}; its "
            f"delete answered HTTP {code}, so the record is kept"
        )


def _report(info: PodInfo | None, record: Record, as_json: bool) -> None:
    report = {
        "id": record.id,
        "image": record.image,
        "host": record.host,
        "port": record.port,
        "status": info.status if info else "UNKNOWN",
    }
    if as_json:
        print(json.dumps(report))
    else:
        print(" ".join(f"{key}={value}" for key, value in report.items()))


def live_window(state: State) -> Window:
    """Return the recorded window volume; refuse when none is up."""
    window = state.window()
    # A volume still recorded after the sweep is one whose delete failed.
    if window is None or window.ends_within(0):
        log.refuse("no window volume is up; run gpunit volume up")
    return window


def _in_window(spec: Spec, state: State) -> Spec:
    """Return `spec` mounting the window volume; refuse a session that outlives it."""
    window = live_window(state)
    if window.ends_within(spec.ceiling_s + spec.timeout_s):
        log.refuse(
            f"the volume ends at {window.ends}; shorten the ceiling or run gpunit "
            "volume up"
        )
    return replace(spec, volume=window.id)


def _warn_unignored(state: State) -> None:
    if shutil.which("git") is None:
        return
    # 1 is "not ignored"; 128 is "not a repository", where nothing can be committed.
    # The slash matters: `.gpunit/` matches a directory not yet made only with it.
    checked = subprocess.run(
        ["git", "check-ignore", "-q", f"{state.dir.name}/"],
        cwd=state.dir.parent,
        capture_output=True,
        check=False,
    )
    if checked.returncode == 1:
        log.say(
            f"warning: {state.dir.name}/ is not gitignored; it will hold a private key"
        )


def _refuse_listed(spec: Spec, provider: Provider) -> None:
    try:
        listed = provider.list(spec.project, spec.image)
    except (Lost, NoImage) as fault:
        log.refuse(f"the account's pods could not be listed: {fault}")
    if listed:
        pods = ", ".join(f"{pod_id} ({pod_status})" for pod_id, pod_status in listed)
        log.refuse(
            f"a {pod_name(spec.project)} pod already exists: {pods}; run gpunit down"
        )


def placeable(spec: Spec, provider: Provider) -> list[str]:
    """Return the cards of `gpus` that meet `vram_gb` and `max_hourly`, in order."""
    cards = []
    for card in spec.gpus:
        try:
            info = provider.gpu(card)
        except Unknown:
            log.refuse(f"'gpus' names {card!r}, which the catalogue does not know")
        except Lost as fault:
            log.refuse(f"the catalogue could not be read for {card!r}: {fault}")
        if info.vram_gb < spec.vram_gb:
            log.say(f"skipped: {card} has {info.vram_gb} GB, under {spec.vram_gb}")
        elif spec.max_hourly is not None and info.hourly > spec.max_hourly:
            log.say(f"skipped: {card} costs ${info.hourly}/h, over {spec.max_hourly}")
        else:
            cards.append(card)
    if not cards:
        log.refuse("no card in 'gpus' meets vram_gb and max_hourly")
    return cards


def _create(
    spec: Spec, provider: Provider, cards: list[str], pubkey: str, nonce: str
) -> str | None:
    for card in cards:
        log.say(f"creating on {card}")
        try:
            pod_id = provider.create(spec, card, pubkey, spec.ceiling_s, nonce=nonce)
        except Unplaceable as unplaceable:
            log.say(str(unplaceable))
            continue
        except Lost as lost:
            log.say(str(lost))
            log.say(f"the create's outcome is unknown: a {pod_name(spec.project)}")
            log.say(
                "pod may exist and bill; run gpunit down, which finds and deletes it"
            )
            raise
        ledger.record(spec.project, pod_id, card, spec.image)
        return pod_id
    return None


def _wait(spec: Spec, provider: Provider, state: State, record: Record) -> Record:
    dead = DeadPod()

    def mapped() -> PodInfo | None:
        # A failed poll is "not yet", never an abort: an abort would skip the teardown.
        info = provider.get(record.id)
        if dead.seen(info) and info is not None:
            _tear_down(
                spec,
                provider,
                state,
                f"pod {record.id} is {info.status}: the container is not running",
            )
        if info is None:
            return None
        # RunPod calls the create's data centres preferred: 0013 design D8.
        if not spec.allows(info.datacenter):
            if info.datacenter is not None:
                _tear_down(
                    spec,
                    provider,
                    state,
                    f"pod {record.id} was placed in {info.datacenter}, "
                    f"outside datacenters {', '.join(spec.datacenters)}",
                )
            return None
        return info if info.host and info.port else None

    info = _poll(spec.timeout_s, mapped)
    if info is None:
        _tear_down(
            spec,
            provider,
            state,
            f"pod {record.id} got no host and port 22 within {spec.timeout_s}s",
        )
    ready = replace(record, host=info.host, port=info.port)
    state.write(ready)
    return ready


def _poll(seconds: int, attempt: Callable[[], T | None]) -> T | None:
    deadline = CLOCK.monotonic() + seconds
    while True:
        found = attempt()
        if found is not None or CLOCK.monotonic() >= deadline:
            return found
        CLOCK.sleep(POLL_S)


def _tear_down(spec: Spec, provider: Provider, state: State, reason: str) -> NoReturn:
    log.say(f"{reason}; tearing the pod down")
    if down(spec, provider, state) != 0:
        log.say(f"refused: {reason}")
        raise Stranded(reason)
    log.refuse(reason)
