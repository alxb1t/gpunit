import io
from decimal import Decimal
from pathlib import Path

import pytest

from gpunit import ledger, log
from gpunit.provider import GpuInfo, Lost, Refused
from gpunit.state import State
from gpunit.volume import most_cost
from tests.fakes import FakeProvider
from tests.helpers import NO_REQUESTS, WINDOW, gpunit, open_window, write_spec

CARDS = WINDOW.replace('["RTX 4090", "RTX A6000"]', '["NVIDIA A40", "NVIDIA L40"]')


@pytest.mark.spec("volume:up:datacenter-from-stock")
def test_the_volume_is_made_where_the_first_card_is_in_stock(
    cwd: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_spec(cwd, CARDS)
    provider = FakeProvider(
        volume_datacenters={"EU-RO-1", "CA-MTL-4"},
        stocks={
            "NVIDIA A40": [("US-KS-2", "HIGH"), ("EU-RO-1", "LOW")],
            "NVIDIA L40": [("CA-MTL-4", "HIGH")],
        },
        volume_creates=["v7"],
    )

    assert gpunit(["volume", "up", "--yes"], provider=provider) == 0
    assert provider.named("create_volume") == [("gpunit-isekai", 60, "EU-RO-1")]
    assert provider.named("stock") == [("NVIDIA A40",)]
    window = State(cwd).window()
    assert window is not None
    assert (window.id, window.datacenter, window.size_gb) == ("v7", "EU-RO-1", 60)
    assert not State(cwd).volume_pending.exists()
    assert list(ledger.volumes()) == ["v7"]
    assert "volume v7 up in EU-RO-1, 60 GB" in capsys.readouterr().err


@pytest.mark.spec("volume:up:datacenter-from-stock")
def test_the_highest_stock_wins_and_a_card_under_the_floor_is_not_read(
    cwd: Path,
) -> None:
    write_spec(cwd, CARDS)
    provider = FakeProvider(
        gpus={"NVIDIA A40": GpuInfo(vram_gb=16, hourly=0.4)},
        volume_datacenters={"EU-RO-1", "CA-MTL-4"},
        stocks={
            "NVIDIA L40": [
                ("EU-RO-1", "LOW"),
                ("CA-MTL-4", "HIGH"),
                ("EU-RO-1", "HIGH"),
            ]
        },
    )

    assert gpunit(["volume", "up", "--yes"], provider=provider) == 0
    assert provider.named("stock") == [("NVIDIA L40",)]
    assert provider.named("create_volume") == [("gpunit-isekai", 60, "CA-MTL-4")]


@pytest.mark.spec("volume:up:datacenter-given")
def test_the_given_data_centre_reads_no_stock(cwd: Path) -> None:
    write_spec(cwd, WINDOW + 'volume_datacenter = "CA-MTL-4"\n')
    provider = FakeProvider()

    assert gpunit(["volume", "up", "--yes"], provider=provider) == 0
    assert provider.named("create_volume") == [("gpunit-isekai", 60, "CA-MTL-4")]
    assert [name for name, _ in provider.calls] == ["create_volume"]


@pytest.mark.spec("volume:up:no-stock-refuses")
def test_no_stock_refuses_naming_the_cards(
    cwd: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_spec(cwd, CARDS)
    provider = FakeProvider(
        volume_datacenters={"EU-RO-1"},
        stocks={"NVIDIA A40": [], "NVIDIA L40": [("US-KS-2", "HIGH")]},
    )

    assert gpunit(["volume", "up", "--yes"], provider=provider) == 1
    assert provider.named("create_volume") == []
    assert not State(cwd).volume_pending.exists()
    err = capsys.readouterr().err
    assert "no card of gpus is in stock in a data centre with standard volumes" in err
    assert "NVIDIA A40, NVIDIA L40" in err


@pytest.mark.spec("volume:up:no-by-default")
@pytest.mark.parametrize(
    ("answer", "created"), [("\n", False), ("y\n", True)], ids=["empty", "twin-y"]
)
def test_no_is_the_default(
    answer: str,
    created: bool,
    cwd: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_spec(cwd, WINDOW)
    monkeypatch.setattr("sys.stdin", io.StringIO(answer))
    provider = FakeProvider()

    assert gpunit(["volume", "up"], provider=provider) == (0 if created else 1)
    assert bool(provider.named("create_volume")) is created
    assert ("not created" in capsys.readouterr().err) is not created


@pytest.mark.spec("volume:up:price-names-the-window")
def test_the_price_names_the_window(
    cwd: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_spec(cwd, WINDOW)
    monkeypatch.setattr("sys.stdin", io.StringIO("y\n"))

    assert gpunit(["volume", "up"], provider=FakeProvider()) == 0
    captured = capsys.readouterr()
    assert "price: $0.07/GB a month" in captured.err
    assert "at most $0.03 for 60 GB over 4h" in captured.err
    assert "create volume gpunit-isekai for at most $0.03? [y/N]" in captured.out


@pytest.mark.spec("volume:up:price-names-the-window")
@pytest.mark.parametrize(
    ("size_gb", "ceiling_s", "most"),
    [(60, 14400, "0.03"), (60, 3601, "0.02"), (4000, 3600, "0.39"), (10, 600, "0.01")],
)
def test_the_price_counts_whole_hours_up_to_the_cent(
    size_gb: int, ceiling_s: int, most: str
) -> None:
    assert most_cost(size_gb, ceiling_s) == Decimal(most)


@pytest.mark.spec("volume:up:needs-volume-gb")
def test_no_volume_gb_no_volume(cwd: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert gpunit(["volume", "up", "--yes"], provider=NO_REQUESTS) == 1
    assert "'volume_gb'" in capsys.readouterr().err


@pytest.mark.spec("volume:up:lost-create-exits-3")
def test_a_lost_create_keeps_the_pending_mark(
    cwd: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_spec(cwd, WINDOW)
    provider = FakeProvider(volume_creates=[Lost("volume create returned HTTP 503")])

    assert gpunit(["volume", "up", "--yes"], provider=provider) == 3
    assert State(cwd).volume_pending.exists()
    assert State(cwd).window() is None
    assert "run gpunit volume down" in capsys.readouterr().err


@pytest.mark.spec("volume:up:lost-create-exits-3")
def test_a_refused_create_clears_the_pending_mark(
    cwd: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_spec(cwd, WINDOW)
    provider = FakeProvider(volume_creates=[Refused("volume create returned HTTP 400")])

    assert gpunit(["volume", "up", "--yes"], provider=provider) == 1
    assert not State(cwd).volume_pending.exists()
    assert "HTTP 400" in capsys.readouterr().err


@pytest.mark.spec("volume:up:pending-refuses")
@pytest.mark.parametrize("pending", [True, False], ids=["pending", "twin-none"])
def test_a_pending_mark_refuses(
    pending: bool, cwd: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_spec(cwd, WINDOW)
    if pending:
        State(cwd).mark_volume_pending()
    provider = FakeProvider()

    assert gpunit(["volume", "up", "--yes"], provider=provider) == (1 if pending else 0)
    assert bool(provider.named("create_volume")) is not pending
    assert ("run gpunit volume down" in capsys.readouterr().err) is pending


@pytest.mark.spec("volume:extend:moves-the-end")
def test_up_again_extends(cwd: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_spec(cwd, WINDOW)
    state = open_window(cwd, 3600)
    provider = FakeProvider()

    before = log.utc(14400)
    assert gpunit(["volume", "up", "--yes"], provider=provider) == 0
    after = log.utc(14400)

    assert provider.calls == []
    window = state.window()
    assert window is not None
    assert window.id == "v1"
    assert before <= window.ends <= after
    assert ledger.volumes()["v1"].ends == window.ends
    assert f"volume v1 extended until {window.ends}" in capsys.readouterr().err


@pytest.mark.spec("volume:ceiling:overdue-deleted")
def test_up_on_an_overdue_volume_deletes_it_and_makes_a_new_one(cwd: Path) -> None:
    write_spec(cwd, WINDOW)
    state = open_window(cwd, -60)
    provider = FakeProvider(volume_creates=["v2"])

    assert gpunit(["volume", "up", "--yes"], provider=provider) == 0
    assert provider.named("delete_volume") == [("v1",)]
    window = state.window()
    assert window is not None
    assert window.id == "v2"


@pytest.mark.spec("volume:down:deletes")
def test_down_deletes_the_volume(cwd: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state = open_window(cwd, 3600)
    provider = FakeProvider(volume_listings=[["v1"]])

    assert gpunit(["volume", "down"], provider=provider) == 0
    assert provider.named("delete_volume") == [("v1",)]
    assert provider.named("volumes") == [("gpunit-isekai",)]
    assert not state.volume.exists()
    assert "volume v1 deleted" in capsys.readouterr().err


@pytest.mark.spec("volume:down:sweeps-by-name")
def test_a_lost_create_is_swept(cwd: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state = State(cwd)
    state.mark_volume_pending()
    provider = FakeProvider(volume_listings=[["v9"]])

    assert gpunit(["volume", "down"], provider=provider) == 0
    assert provider.named("delete_volume") == [("v9",)]
    assert not state.volume_pending.exists()
    assert "swept volume v9" in capsys.readouterr().err


@pytest.mark.spec("volume:down:sweeps-by-name")
def test_an_unreadable_listing_keeps_the_pending_mark(cwd: Path) -> None:
    state = State(cwd)
    state.mark_volume_pending()
    provider = FakeProvider(volume_listings=[Lost("volume listing returned HTTP 500")])

    assert gpunit(["volume", "down"], provider=provider) == 1
    assert state.volume_pending.exists()


@pytest.mark.spec("volume:down:refused-delete-kept")
@pytest.mark.parametrize("code", [409, 404, 0])
def test_a_refused_delete_keeps_the_record(
    code: int, cwd: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    state = open_window(cwd, 3600)
    provider = FakeProvider(volume_deletes={"v1": code})

    assert gpunit(["volume", "down"], provider=provider) == 1
    assert state.window() is not None
    assert f"answered HTTP {code}; the record is kept" in capsys.readouterr().err


@pytest.mark.spec("volume:down:refused-delete-kept")
def test_a_failed_sweep_keeps_the_pending_mark(cwd: Path) -> None:
    state = State(cwd)
    state.mark_volume_pending()
    provider = FakeProvider(volume_listings=[["v9"]], volume_deletes={"v9": 500})

    assert gpunit(["volume", "down"], provider=provider) == 1
    assert state.volume_pending.exists()
