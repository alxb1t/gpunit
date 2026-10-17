import json
from datetime import UTC, datetime
from typing import NoReturn

import pytest

from gpunit import ledger, spend
from gpunit.provider import Lost, PodCost, VolumeCost
from tests.fakes import FakeProvider
from tests.helpers import IMAGE, gpunit

DAY_1, DAY_2 = "2026-10-11T00:00:00Z", "2026-10-12T00:00:00Z"
WEEK = ("2026-10-06T00:00:00Z", "2026-10-13T00:00:00Z")


@pytest.fixture(autouse=True)
def today(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2026, 10, 12, 15, 0, tzinfo=UTC)
    monkeypatch.setattr(spend, "utc_now", lambda: now)


def owned(**projects: str) -> None:
    for pod_id, project in projects.items():
        ledger.record(project, pod_id, "NVIDIA A40", IMAGE)


def report(
    capsys: pytest.CaptureFixture[str], provider: FakeProvider, *argv: str
) -> tuple[str, str]:
    assert gpunit(["spend", *argv], provider=provider) == 0
    return capsys.readouterr()


@pytest.mark.spec("spend:report:by-project")
def test_pods_are_summed_by_project(capsys: pytest.CaptureFixture[str]) -> None:
    owned(p1="isekai", p2="isekai", p3="serve-qwen3-4b")
    costs = [
        PodCost(pod_id, day, amount)
        for pod_id, amount in (("p1", 0.10), ("p2", 0.20), ("p3", 0.05))
        for day in (DAY_1, DAY_2)
    ]

    out, _ = report(capsys, FakeProvider(pod_costs=costs))
    assert "pods      isekai               2 pods  $0.60\n" in out
    assert "pods      serve-qwen3-4b       1 pod   $0.10\n" in out
    assert out.index("isekai") < out.index("serve-qwen3-4b")


@pytest.mark.spec("spend:report:by-project")
def test_a_long_name_or_count_never_runs_into_the_next_column(
    capsys: pytest.CaptureFixture[str],
) -> None:
    owned(p1="research-diffusion-lab")
    strays = [PodCost(f"s{n}", DAY_1, 0.01) for n in range(120)]

    out, _ = report(
        capsys, FakeProvider(pod_costs=[PodCost("p1", DAY_1, 0.5), *strays])
    )
    assert "pods      research-diffusion-lab 1 pod   $0.50\n" in out
    assert "pods      unattributed         120 pods $1.20\n" in out


@pytest.mark.spec("spend:report:unattributed")
def test_a_pod_the_ledger_does_not_name_is_unattributed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    owned(p1="isekai")
    costs = [PodCost("p1", DAY_1, 0.25), PodCost("p9", DAY_2, 0.50)]

    out, _ = report(capsys, FakeProvider(pod_costs=costs))
    assert "pods      unattributed         1 pod   $0.50\n" in out
    assert out.endswith("total                                  $0.75\n")


@pytest.mark.spec("spend:report:storage-is-its-own-line")
def test_storage_is_a_line_of_its_own(capsys: pytest.CaptureFixture[str]) -> None:
    owned(p1="isekai")
    provider = FakeProvider(
        pod_costs=[PodCost("p1", DAY_1, 0.25)],
        volume_costs=[VolumeCost("v1", DAY_1, 0.047), VolumeCost("v1", DAY_2, 0.047)],
    )

    out, _ = report(capsys, provider)
    assert "storage   v1                           $0.09\n" in out
    assert "pods      isekai               1 pod   $0.25\n" in out


@pytest.mark.spec("spend:report:total-is-the-providers")
def test_the_total_is_the_providers_rounded_once(
    capsys: pytest.CaptureFixture[str],
) -> None:
    owned(a="isekai", b="other")
    provider = FakeProvider(
        pod_costs=[PodCost("a", DAY_1, 0.004), PodCost("b", DAY_1, 0.004)],
        volume_costs=[VolumeCost("v1", DAY_2, 0.004)],
    )

    out, _ = report(capsys, provider)
    assert out == (
        "spend, 2026-10-06 → 2026-10-12 (UTC)\n"
        "pods      isekai               1 pod   $0.00\n"
        "pods      other                1 pod   $0.00\n"
        "pods      unattributed         0 pods  $0.00\n"
        "storage   v1                           $0.00\n"
        "total                                  $0.01\n"
    )


@pytest.mark.spec("spend:report:in-progress-day-noted")
def test_the_day_still_billing_is_named(capsys: pytest.CaptureFixture[str]) -> None:
    out, err = report(capsys, FakeProvider())
    assert "still being billed" not in out
    assert spend.STILL_BILLING in err


@pytest.mark.spec("spend:report:json")
def test_the_report_as_json(capsys: pytest.CaptureFixture[str]) -> None:
    owned(p1="isekai")
    provider = FakeProvider(
        pod_costs=[PodCost("p1", DAY_1, 0.574), PodCost("p9", DAY_1, 0.2)],
        volume_costs=[VolumeCost("db7sc8cild", DAY_2, 0.31)],
    )

    out, _ = report(capsys, provider, "--json")
    assert json.loads(out) == {
        "from": "2026-10-06",
        "to": "2026-10-12",
        "projects": [{"project": "isekai", "pods": 1, "amount": 57}],
        "unattributed": {"pods": 1, "amount": 20},
        "storage": [{"volume": "db7sc8cild", "amount": 31}],
        "total": 108,
    }


@pytest.mark.spec("spend:report:unreadable-billing-fails")
@pytest.mark.parametrize("read", ["pod_costs", "volume_costs"])
def test_an_unreadable_billing_is_an_error_not_zeros(
    read: str, capsys: pytest.CaptureFixture[str]
) -> None:
    lost = Lost("pods billing read returned HTTP 500: oops")
    if read == "pod_costs":
        provider = FakeProvider(pod_costs=lost)
    else:
        provider = FakeProvider(volume_costs=lost)

    assert gpunit(["spend"], provider=provider) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert "the billing could not be read" in err


def _no_home() -> NoReturn:
    raise RuntimeError("Could not determine home directory.")


@pytest.mark.spec("spend:report:unreadable-ledger-fails")
@pytest.mark.parametrize("fault", ["not-utf8", "a-directory", "no-home"])
def test_an_unreadable_ledger_is_an_error_not_a_table(
    fault: str, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger.path().parent.mkdir(parents=True)
    if fault == "not-utf8":
        ledger.path().write_bytes(b"\xff\xfe\n")
    elif fault == "a-directory":
        ledger.path().mkdir()
    else:
        monkeypatch.setattr(ledger, "home_state", _no_home)
    provider = FakeProvider(pod_costs=[PodCost("p1", DAY_1, 0.5)])

    assert gpunit(["spend"], provider=provider) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert "refused: the ledger could not be read" in err


@pytest.mark.spec("spend:report:unattributed")
def test_a_ledger_line_whose_fields_are_not_strings_is_skipped(
    capsys: pytest.CaptureFixture[str],
) -> None:
    good = {"id": "p1", "project": "isekai", "card": None, "image": "i", "at": "t"}
    ledger.path().parent.mkdir(parents=True)
    ledger.path().write_text(
        "\n".join(
            json.dumps(line)
            for line in (
                {**good, "id": "p2", "project": None},
                {**good, "id": "p3", "card": 5},
                {**good, "id": 4},
                good,
            )
        )
        + "\n",
        encoding="utf-8",
    )
    costs = [PodCost(pod_id, DAY_1, 0.25) for pod_id in ("p1", "p2", "p3", "4")]

    out, _ = report(capsys, FakeProvider(pod_costs=costs))
    assert "pods      isekai               1 pod   $0.25\n" in out
    assert "pods      unattributed         3 pods  $0.75\n" in out


@pytest.mark.spec("spend:window:default-is-seven-days")
def test_the_default_window_is_seven_whole_days(
    capsys: pytest.CaptureFixture[str],
) -> None:
    provider = FakeProvider()

    report(capsys, provider)
    assert provider.named("pod_billing") == [WEEK]
    assert provider.named("volume_billing") == [WEEK]


@pytest.mark.spec("spend:window:days")
def test_a_chosen_window(capsys: pytest.CaptureFixture[str]) -> None:
    provider = FakeProvider(pod_costs=[PodCost("p1", "2026-10-10T00:00:00Z", 1.0)])

    out, _ = report(capsys, provider, "--days", "2")
    assert provider.named("pod_billing") == [(DAY_1, WEEK[1])]
    assert out.startswith("spend, 2026-10-11 → 2026-10-12 (UTC)\n")
    assert "$1.00" not in out


@pytest.mark.spec("spend:report:window-volume-under-project")
def test_a_window_volume_bills_under_its_project(
    capsys: pytest.CaptureFixture[str],
) -> None:
    owned(p1="isekai")
    ledger.record_volume("isekai", "v2", "2026-10-12T18:00:00Z")
    ledger.record_volume("portraits", "v3", "2026-10-12T18:00:00Z")
    provider = FakeProvider(
        pod_costs=[PodCost("p1", DAY_1, 0.25)],
        volume_costs=[
            VolumeCost("v2", DAY_2, 0.02),
            VolumeCost("v3", DAY_2, 0.01),
            VolumeCost("v1", DAY_2, 0.05),
        ],
    )

    out, _ = report(capsys, provider)
    assert "pods      isekai               1 pod   $0.27\n" in out
    assert "pods      portraits            0 pods  $0.01\n" in out
    assert "storage   v1                           $0.05\n" in out
    assert "v2" not in out
    assert "v3" not in out
    assert out.endswith("total                                  $0.33\n")


@pytest.mark.spec("spend:report:overdue-volume-named")
@pytest.mark.parametrize(
    ("ends", "day", "named"),
    [
        ("2026-10-11T18:00:00Z", DAY_2, True),
        ("2026-10-12T10:00:00Z", DAY_2, False),
        ("2026-10-10T18:00:00Z", DAY_1, False),
    ],
    ids=["ended-yesterday-bills-today", "twin-ended-today", "twin-no-charge-today"],
)
def test_an_overdue_volume_still_billing_is_named(
    ends: str, day: str, named: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    ledger.record_volume("isekai", "v2", ends)
    provider = FakeProvider(volume_costs=[VolumeCost("v2", day, 0.01)])

    _, err = report(capsys, provider)
    said = (
        "volume v2 (isekai) passed its ceiling and still bills; run gpunit volume down"
    )
    assert (said in err) is named


@pytest.mark.spec("spend:report:deleted-volume-not-named")
@pytest.mark.parametrize("deleted", [True, False], ids=["deleted", "twin-kept"])
def test_a_deleted_volume_is_not_named(
    deleted: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    ledger.record_volume("isekai", "v2", "2026-10-11T18:00:00Z")
    if deleted:
        ledger.record_deleted("v2")
    provider = FakeProvider(volume_costs=[VolumeCost("v2", DAY_2, 0.02)])

    out, err = report(capsys, provider)
    assert ("volume v2" in err) is not deleted
    assert "pods      isekai               0 pods  $0.02\n" in out
