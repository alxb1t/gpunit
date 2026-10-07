"""Open, report and close one GPU session: `up`, `status`, `down`."""

import json
import os
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import NoReturn, TypeVar

from gpunit import log
from gpunit.provider import (
    Lost,
    NoImage,
    PodInfo,
    Provider,
    Refused,
    Unknown,
    fingerprint,
    pod_name,
)
from gpunit.spec import Spec
from gpunit.state import Record, State

POLL_S = 5
LOG_WAIT_S = 60
# sshd can answer after the port is mapped, so the scan waits longer than the log.
SCAN_WAIT_S = 180
LOG_TAIL = 5000

T = TypeVar("T")


@dataclass(frozen=True)
class Clock:
    """The time source the waits read; the tests replace it."""

    monotonic: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep


CLOCK = Clock()


def up(spec: Spec, provider: Provider, state: State) -> Record:
    """Place a pod, wait for it, verify its host key, and return its record.

    Refuse when it cannot; raise `Lost` when a create's answer did not arrive.
    """
    if shutil.which("ssh-keygen") is None:
        log.refuse("ssh-keygen is not on PATH; install OpenSSH")
    _warn_unignored(state)
    if state.pod.exists():
        log.refuse(f"a pod is already recorded in {state.pod}; run gpunit down")
    if state.pending.exists():
        log.refuse(f"a create may have left a pod ({state.pending}); run gpunit down")
    _refuse_listed(spec, provider)
    if spec.volume is not None:
        try:
            provider.volume(spec.volume)
        except (Unknown, Lost) as fault:
            log.refuse(f"volume {spec.volume} could not be read: {fault}")
    cards = _placeable(spec, provider)

    pubkey = state.keygen(pod_name(spec.project))
    state.mark_pending()
    pod_id = _create(spec, provider, cards, pubkey)
    if pod_id is None:
        state.clear_pending()
        log.refuse("no card in 'gpus' was placed")
    record = Record(pod_id, spec.image, host=None, port=None, created=log.utc())
    state.write(record)
    state.clear_pending()
    log.say(f"pod {pod_id} created; waiting for SSH")

    record = _wait(spec, provider, state, record)
    _verify_host_key(spec, provider, state, record)
    log.say(f"session up: pod {record.id}, root@{record.host} -p {record.port}")
    return record


def ssh_command(state: State, record: Record) -> list[str]:
    """Return the `ssh` argv that opens a shell on the recorded pod."""
    return [
        "ssh",
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
    """Replace this process with `ssh` to the recorded pod; refuse with no record."""
    record = state.read()
    if record is None or record.host is None:
        log.refuse("no session is recorded; run gpunit up")
    (execvp or os.execvp)("ssh", ssh_command(state, record))


def status(provider: Callable[[], Provider], state: State, *, as_json: bool) -> int:
    """Print the recorded session to stdout, in words or as one JSON object.

    `provider` is built only when a record exists: no record needs no key.
    """
    record = state.read()
    if record is None:
        print("null" if as_json else "no session is recorded")
        return 0
    info = provider().get(record.id)
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
    return 0


def down(spec: Spec, provider: Provider, state: State) -> int:
    """Delete the recorded pod, sweep every listed one; return 0, or 1 on a fault."""
    failed = False
    record = state.read()
    if record is not None:
        code = provider.delete(record.id)
        if code == 204:
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
        code = provider.delete(pod_id)
        if code == 204:
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


def _placeable(spec: Spec, provider: Provider) -> list[str]:
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
    spec: Spec, provider: Provider, cards: list[str], pubkey: str
) -> str | None:
    for card in cards:
        log.say(f"creating on {card}")
        try:
            return provider.create(spec, card, pubkey, spec.ceiling_s)
        except Refused as refusal:
            log.say(str(refusal))
        except Lost as lost:
            log.say(str(lost))
            log.say(f"the create's outcome is unknown: a {pod_name(spec.project)}")
            log.say(
                "pod may exist and bill; run gpunit down, which finds and deletes it"
            )
            raise
    return None


def _wait(spec: Spec, provider: Provider, state: State, record: Record) -> Record:
    def mapped() -> PodInfo | None:
        # A failed poll is "not yet", never an abort: an abort would skip the teardown.
        info = provider.get(record.id)
        return info if info is not None and info.host and info.port else None

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


def _verify_host_key(
    spec: Spec, provider: Provider, state: State, record: Record
) -> None:
    # The fingerprint comes over the authenticated API, never over the connection
    # it vouches for; nothing connects until the two agree.
    printed = _poll(
        LOG_WAIT_S, lambda: fingerprint(provider.log(record.id, tail=LOG_TAIL))
    )
    if printed is None:
        _tear_down(spec, provider, state, f"no host-key line within {LOG_WAIT_S}s")
    scanned = _poll(SCAN_WAIT_S, lambda: _scan(str(record.host), int(record.port or 0)))
    if scanned is None:
        _tear_down(
            spec, provider, state, f"no host-key scan answered within {SCAN_WAIT_S}s"
        )
    served = _fingerprint_of(scanned)
    if served != printed:
        _tear_down(
            spec,
            provider,
            state,
            f"the pod's host key {served} does not match the printed {printed}",
        )
    state.write_known_hosts(scanned)
    log.say(f"host key verified: {printed}")


def _poll(seconds: int, attempt: Callable[[], T | None]) -> T | None:
    deadline = CLOCK.monotonic() + seconds
    while True:
        found = attempt()
        if found is not None or CLOCK.monotonic() >= deadline:
            return found
        CLOCK.sleep(POLL_S)


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


def _tear_down(spec: Spec, provider: Provider, state: State, reason: str) -> NoReturn:
    log.say(f"{reason}; tearing the pod down")
    down(spec, provider, state)
    log.refuse(reason)
