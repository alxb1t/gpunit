"""Report what the provider billed over whole UTC days, under each pod's project."""

import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from gpunit import ledger, log
from gpunit.provider import Lost, PodCost, Provider, VolumeCost

UNATTRIBUTED = "unattributed"
STILL_BILLING = "the current UTC day is still being billed; its figures can change"
CENT = Decimal("0.01")


@dataclass(frozen=True)
class Line:
    """One project: its name, its pod count, and its pods' and volumes' amount."""

    name: str
    pods: int
    amount: Decimal


@dataclass(frozen=True)
class Report:
    """The window's billing: projects and volumes by amount, highest first."""

    first: date
    last: date
    projects: list[Line]
    unattributed: Line
    storage: list[tuple[str, Decimal]]

    @property
    def total(self) -> Decimal:
        """Return the sum of the unrounded amounts; it is rounded once, when printed."""
        lines = [*self.projects, self.unattributed]
        return sum((line.amount for line in lines), Decimal()) + sum(
            (amount for _, amount in self.storage), Decimal()
        )


def utc_now() -> datetime:
    """Return the time now, in UTC; the tests replace it."""
    return datetime.now(UTC)


def window(days: int, now: datetime) -> tuple[date, date]:
    """Return the first and the last UTC day of the `days` ending with `now`'s.

    e.g. (7, 2026-10-12T15:00Z) → (2026-10-06, 2026-10-12)
    """
    today = now.astimezone(UTC).date()
    return today - timedelta(days=days - 1), today


def spend(provider: Provider, days: int, *, as_json: bool) -> int:
    """Print the report and return 0.

    Refuse when the billing or the ledger cannot be read.
    """
    first, last = window(days, utc_now())
    start, end = _midnight(first), _midnight(last + timedelta(days=1))
    try:
        pods = provider.pod_billing(start, end)
        volumes = provider.volume_billing(start, end)
    except Lost as fault:
        # A table of zeros would read as a free week (0007 design D3).
        log.refuse(f"the billing could not be read: {fault}")
    owners = {pod_id: entry.project for pod_id, entry in ledger.read().items()}
    windows = ledger.volumes()
    volume_owners = {volume_id: entry.project for volume_id, entry in windows.items()}
    report = build(first, last, pods, volumes, owners, volume_owners)
    print(json.dumps(to_json(report)) if as_json else render(report))
    log.say(STILL_BILLING)
    today = _midnight(last)
    billed_today = {cost.volume_id for cost in volumes if cost.start >= today}
    for volume_id in sorted(billed_today & set(windows)):
        # Before today's midnight: a volume deleted at its end today still bills today.
        if windows[volume_id].ends < today:
            log.say(
                f"volume {volume_id} ({windows[volume_id].project}) passed its ceiling "
                "and still bills; run gpunit volume down"
            )
    return 0


def build(
    first: date,
    last: date,
    pods: list[PodCost],
    volumes: list[VolumeCost],
    owners: dict[str, str],
    volume_owners: dict[str, str],
) -> Report:
    """Return the report: pods and window volumes by project, other volumes alone."""
    by_pod = _summed((cost.pod_id, cost.amount) for cost in pods)
    by_volume = _summed((cost.volume_id, cost.amount) for cost in volumes)
    by_project: dict[str, list[Decimal]] = defaultdict(list)
    for pod_id, amount in by_pod.items():
        by_project[owners.get(pod_id, UNATTRIBUTED)].append(amount)
    stored: dict[str, Decimal] = defaultdict(Decimal)
    storage: list[tuple[str, Decimal]] = []
    for volume_id, amount in by_volume.items():
        if volume_id in volume_owners:
            stored[volume_owners[volume_id]] += amount
        else:
            storage.append((volume_id, amount))
    lines = {
        name: Line(name, len(by_project[name]), sum(by_project[name], stored[name]))
        for name in by_project.keys() | stored.keys()
    }
    stray = lines.pop(UNATTRIBUTED, Line(UNATTRIBUTED, 0, Decimal()))
    storage.sort(key=lambda item: (-item[1], item[0]))
    return Report(first, last, _ranked(lines.values()), stray, storage)


def render(report: Report) -> str:
    """Return the report as the table `spend` prints, a space always between columns."""
    rows = [f"spend, {report.first} → {report.last} (UTC)"]
    for line in [*report.projects, report.unattributed]:
        count = f"{line.pods} pod{'' if line.pods == 1 else 's'}"
        rows.append(f"{'pods':<10}{line.name:<20} {count:<7} {_dollars(line.amount)}")
    for volume, amount in report.storage:
        rows.append(f"{'storage':<10}{volume:<20} {'':<7} {_dollars(amount)}")
    rows.append(f"{'total':<39}{_dollars(report.total)}")
    return "\n".join(rows)


def to_json(report: Report) -> dict[str, object]:
    """Return the report as one JSON object, each amount in whole cents."""
    return {
        "from": report.first.isoformat(),
        "to": report.last.isoformat(),
        "projects": [
            {"project": line.name, "pods": line.pods, "amount": _cents(line.amount)}
            for line in report.projects
        ],
        "unattributed": {
            "pods": report.unattributed.pods,
            "amount": _cents(report.unattributed.amount),
        },
        "storage": [
            {"volume": volume, "amount": _cents(amount)}
            for volume, amount in report.storage
        ],
        "total": _cents(report.total),
    }


def _summed(costs: Iterable[tuple[str, float]]) -> dict[str, Decimal]:
    # Through `str`, so 0.1 sums as the provider wrote it, not as a binary float.
    sums: dict[str, Decimal] = defaultdict(Decimal)
    for key, amount in costs:
        sums[key] += Decimal(str(amount))
    return dict(sums)


def _ranked(lines: Iterable[Line]) -> list[Line]:
    return sorted(lines, key=lambda line: (-line.amount, line.name))


def _midnight(day: date) -> str:
    return f"{day.isoformat()}T00:00:00Z"


def _round(amount: Decimal) -> Decimal:
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def _dollars(amount: Decimal) -> str:
    return f"${_round(amount)}"


def _cents(amount: Decimal) -> int:
    return int(_round(amount) * 100)
