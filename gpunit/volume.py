"""Make, extend and end a working window's network volume: `volume up · down`."""

import math
import sys
from dataclasses import replace
from decimal import ROUND_UP, Decimal

from gpunit import ledger, lifecycle, log
from gpunit.provider import Lost, Provider, Refused, Unknown, pod_name
from gpunit.spec import Spec
from gpunit.state import State, Window

# RunPod's standard storage under 1 TB, billed by the hour: 0010 design D5.
VOLUME_GB_MONTH = Decimal("0.07")
HOURS_A_MONTH = 730
# The stock levels a volume may be placed on, best first.
STOCK = ("HIGH", "MEDIUM", "LOW")


def up(
    spec: Spec,
    provider: Provider,
    state: State,
    *,
    yes: bool,
) -> int:
    """Create the window volume, or extend a live one, after the price; return 0.

    Refuse when it cannot; raise `Lost` when a create's answer did not arrive.
    """
    lifecycle.sweep_window(state, lambda: provider)
    if state.volume_pending.exists():
        log.refuse(
            f"a create may have left a volume ({state.volume_pending}); "
            "run gpunit volume down"
        )
    if spec.volume_gb is None or spec.volume_ceiling_s is None:
        log.refuse("the spec sets no 'volume_gb'; a window volume needs it")
    name = pod_name(spec.project)
    window = state.window()
    if window is not None:
        return _extend(spec.project, state, window, spec.volume_ceiling_s, yes)

    datacenter = _datacenter(spec, provider)
    log.say(f"data centre: {datacenter}")
    _agree(
        spec.volume_gb,
        spec.volume_ceiling_s,
        f"create volume {name}",
        "not created",
        yes,
    )
    state.mark_volume_pending()
    try:
        volume_id = provider.create_volume(name, spec.volume_gb, datacenter)
    except Refused as refusal:
        state.clear_volume_pending()
        log.refuse(str(refusal))
    except Lost as lost:
        log.say(str(lost))
        log.say(f"the create's outcome is unknown: a volume {name} may exist and bill;")
        log.say("run gpunit volume down, which finds and deletes it")
        raise
    ends = log.utc(spec.volume_ceiling_s)
    state.write_window(Window(volume_id, datacenter, spec.volume_gb, ends))
    ledger.record_volume(spec.project, volume_id, ends)
    state.clear_volume_pending()
    log.say(f"volume {volume_id} up in {datacenter}, {spec.volume_gb} GB, until {ends}")
    return 0


def down(spec: Spec, provider: Provider, state: State) -> int:
    """Delete the recorded volume, then sweep its name after a lost create; 0, or 1."""
    lifecycle.sweep_window(state, lambda: provider)
    failed = False
    window = state.window()
    if window is not None:
        code = provider.delete_volume(window.id)
        if code == 204:
            state.clear_window()
            log.say(f"volume {window.id} deleted")
        else:
            # A 404 is never gone: a wrong key gets one too.
            log.say(
                f"delete of volume {window.id} answered HTTP {code}; the record is kept"
            )
            failed = True
    if not state.volume_pending.exists():
        return 1 if failed else 0
    if window is not None:
        # A record beside the mark: the create came back, and its volume is the
        # record's; any other of the name is another checkout's.
        state.clear_volume_pending()
        return 1 if failed else 0
    return _sweep(pod_name(spec.project), provider, state)


def _sweep(name: str, provider: Provider, state: State) -> int:
    """Offer each unrecorded volume `name` lists for deletion; clear the mark; 0, or 1.

    A volume this machine's ledger records is another checkout's, and is skipped;
    any other is named and deleted on a yes alone, since a teammate's on the
    account carries the same name and a network volume's delete cannot be undone.
    """
    try:
        listed = provider.volumes(name)
    except Lost as fault:
        log.say(f"no sweep was made: {fault}")
        return 1
    known = ledger.volumes()
    settled = True
    for volume_id in listed:
        if volume_id in known:
            continue
        answer = _ask(f"delete volume {volume_id}, named {name} but in no record?")
        if answer is None:
            log.say(f"volume {volume_id} kept: no answer; run gpunit volume down")
            settled = False
        elif not answer:
            log.say(f"volume {volume_id} kept")
        elif (code := provider.delete_volume(volume_id)) == 204:
            log.say(f"swept volume {volume_id}")
        else:
            log.say(f"delete of swept volume {volume_id} answered HTTP {code}")
            settled = False
    if not settled:
        return 1
    state.clear_volume_pending()
    return 0


def most_cost(size_gb: int, ceiling_s: int) -> Decimal:
    """Return the most `size_gb` can cost over `ceiling_s`, up to the cent.

    e.g. 60 GB over 14400s → Decimal("0.03")
    """
    hours = math.ceil(ceiling_s / 3600)
    month = size_gb * VOLUME_GB_MONTH * hours / HOURS_A_MONTH
    return month.quantize(Decimal("0.01"), ROUND_UP)


def _extend(
    project: str,
    state: State,
    window: Window,
    ceiling_s: int,
    yes: bool,
) -> int:
    if window.ends_within(0):
        # The sweep's delete failed: there is no live window to extend.
        log.refuse(
            f"volume {window.id} passed its ceiling at {window.ends} and is kept; "
            "run gpunit volume down"
        )
    question = f"extend volume {window.id}"
    _agree(window.size_gb, ceiling_s, question, "not extended", yes)
    extended = replace(window, ends=log.utc(ceiling_s))
    state.write_window(extended)
    ledger.record_volume(project, window.id, extended.ends)
    log.say(f"volume {window.id} extended until {extended.ends}")
    return 0


def _datacenter(spec: Spec, provider: Provider) -> str:
    if spec.volume_datacenter is not None:
        return spec.volume_datacenter
    try:
        standard = provider.volume_datacenters()
    except Lost as fault:
        log.refuse(f"the data centres could not be read: {fault}")
    cards = lifecycle.placeable(spec, provider)
    for card in cards:
        try:
            stocked = provider.stock(card)
        except (Unknown, Lost) as fault:
            log.refuse(f"the stock of {card!r} could not be read: {fault}")
        placed = [
            (dc, level) for dc, level in stocked if dc in standard and level in STOCK
        ]
        if placed:
            # `min` keeps the provider's order among equal levels.
            return min(placed, key=lambda pair: STOCK.index(pair[1]))[0]
    log.refuse(
        "no card of gpus is in stock in a data centre with standard volumes: "
        + ", ".join(cards)
    )


def _agree(
    size_gb: int,
    ceiling_s: int,
    question: str,
    refused: str,
    yes: bool,
) -> None:
    """Print the price and ask `question`; refuse anything but yes, unless `yes`."""
    most = most_cost(size_gb, ceiling_s)
    log.say(f"price: ${VOLUME_GB_MONTH}/GB a month")
    log.say(f"at most ${most} for {size_gb} GB over {_hours(ceiling_s)}")
    if not yes and not _ask(f"{question} for at most ${most}?"):
        log.refuse(refused)


def _ask(question: str) -> bool | None:
    """Ask `question` [y/N]; return whether the answer is yes, or None for no answer."""
    try:
        answer = input(f"{question} [y/N] ")
    except EOFError:
        return None
    except KeyboardInterrupt:
        # Ends the prompt's line, so what follows opens at its start.
        print(file=sys.stderr, flush=True)
        return None
    return answer.strip().lower() in ("y", "yes")


def _hours(seconds: int) -> str:
    """Return the hours a ceiling bills, e.g. 5400 → "2h"."""
    return f"{math.ceil(seconds / 3600)}h"
