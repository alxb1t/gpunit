import io
from decimal import Decimal
from pathlib import Path
from typing import NoReturn

import pytest

from gpunit import ledger, log
from gpunit.provider import GpuInfo, Lost, Refused
from gpunit.state import State
from gpunit.volume import most_cost
from tests.fakes import FakeProvider, TtyInput
from tests.helpers import (
    NO_REQUESTS,
    VALID,
    WINDOW,
    gpunit,
    open_window,
    write_spec,
)

CARDS = WINDOW.replace('["RTX 4090", "RTX A6000"]', '["NVIDIA A40", "NVIDIA L40"]')


def interrupt(prompt: str) -> NoReturn:
    raise KeyboardInterrupt


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


@pytest.mark.spec("volume:up:no-by-default")
def test_an_interrupt_at_the_price_creates_nothing(
    cwd: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_spec(cwd, WINDOW)
    monkeypatch.setattr("builtins.input", interrupt)
    provider = FakeProvider()

    assert gpunit(["volume", "up"], provider=provider) == 1
    assert provider.named("create_volume") == []
    assert "not created" in capsys.readouterr().err


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
    err = capsys.readouterr().err
    assert "run gpunit volume down, which finds it and asks before deleting it" in err


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


@pytest.mark.spec("volume:extend:never-earlier")
@pytest.mark.parametrize(
    ("ceiling", "kept"), [("30m", True), ("8h", False)], ids=["shorter", "twin-longer"]
)
def test_up_again_never_pulls_the_end_in(ceiling: str, kept: bool, cwd: Path) -> None:
    write_spec(cwd, VALID + f'volume_gb = 60\nvolume_ceiling = "{ceiling}"\n')
    state = open_window(cwd, 14400)
    recorded = state.window()
    assert recorded is not None
    provider = FakeProvider()

    assert gpunit(["volume", "up", "--yes"], provider=provider) == 0

    assert provider.calls == []
    window = state.window()
    assert window is not None
    assert (window.ends == recorded.ends) is kept
    assert ledger.volumes()["v1"].ends == window.ends


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
    # No pending mark: nothing is swept by name.
    assert provider.named("volumes") == []
    assert not state.volume.exists()
    assert "volume v1 deleted" in capsys.readouterr().err


@pytest.mark.spec("volume:down:sweeps-by-name")
def test_a_lost_create_is_swept(
    cwd: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    state = State(cwd)
    state.mark_volume_pending()
    monkeypatch.setattr("sys.stdin", TtyInput("y\n"))
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
def test_a_failed_sweep_keeps_the_pending_mark(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = State(cwd)
    state.mark_volume_pending()
    monkeypatch.setattr("sys.stdin", TtyInput("y\n"))
    provider = FakeProvider(volume_listings=[["v9"]], volume_deletes={"v9": 500})

    assert gpunit(["volume", "down"], provider=provider) == 1
    assert state.volume_pending.exists()


@pytest.mark.spec("volume:down:no-sweep-without-pending")
def test_down_leaves_a_volume_of_its_name_it_did_not_make(cwd: Path) -> None:
    # Another checkout of the project, on the same account, holds `v8`.
    state = open_window(cwd, 3600)
    provider = FakeProvider(volume_listings=[["v1", "v8"]])

    assert gpunit(["volume", "down"], provider=provider) == 0
    assert provider.named("delete_volume") == [("v1",)]
    assert provider.named("volumes") == []
    assert not state.volume.exists()


@pytest.mark.spec("volume:down:recorded-window-clears-the-mark")
@pytest.mark.parametrize(("code", "exit_code"), [(204, 0), (409, 1)])
def test_a_recorded_window_clears_the_mark_and_sweeps_nothing(
    code: int, exit_code: int, cwd: Path
) -> None:
    # A run stopped between the window's write and the mark's clear leaves both: the
    # create came back, so `v8`, of the name, is another checkout's.
    state = open_window(cwd, 3600)
    state.mark_volume_pending()
    provider = FakeProvider(volume_listings=[["v1", "v8"]], volume_deletes={"v1": code})

    assert gpunit(["volume", "down"], provider=provider) == exit_code
    assert provider.named("delete_volume") == [("v1",)]
    assert provider.named("volumes") == []
    assert (state.window() is None) is (code == 204)
    assert not state.volume_pending.exists()


@pytest.mark.spec("volume:ceiling:overdue-clears-the-mark")
def test_the_overdue_sweep_clears_the_mark_beside_it(
    cwd: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    state = open_window(cwd, -60)
    state.mark_volume_pending()
    monkeypatch.setattr("sys.stdin", io.StringIO("y\n"))
    provider = FakeProvider(volume_listings=[["v1", "v8"]])

    assert gpunit(["volume", "down"], provider=provider) == 0
    assert provider.named("delete_volume") == [("v1",)]
    assert provider.named("volumes") == []
    assert state.window() is None
    assert not state.volume_pending.exists()
    assert "[y/N]" not in capsys.readouterr().out


@pytest.mark.spec("volume:down:ledger-volume-kept")
def test_a_volume_the_ledger_records_is_not_swept(
    cwd: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Another checkout on this machine made `v5`; this one's create was lost.
    ledger.record_volume("isekai", "v5", log.utc(3600))
    state = State(cwd)
    state.mark_volume_pending()
    monkeypatch.setattr("sys.stdin", TtyInput("y\n"))
    provider = FakeProvider(volume_listings=[["v5", "v9"]])

    assert gpunit(["volume", "down"], provider=provider) == 0
    assert provider.named("delete_volume") == [("v9",)]
    assert not state.volume_pending.exists()
    captured = capsys.readouterr()
    assert "v5" not in captured.out
    assert "v5" not in captured.err


@pytest.mark.spec("volume:down:sweep-asks")
@pytest.mark.parametrize(
    ("answer", "deleted", "exit_code"),
    [("y\n", True, 0), ("n\n", False, 0), ("", False, 1)],
    ids=["yes", "no", "no-answer"],
)
def test_the_sweep_asks_before_each_delete(
    answer: str,
    deleted: bool,
    exit_code: int,
    cwd: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state = State(cwd)
    state.mark_volume_pending()
    monkeypatch.setattr("sys.stdin", TtyInput(answer))
    provider = FakeProvider(volume_listings=[["v9"]])

    assert gpunit(["volume", "down"], provider=provider) == exit_code
    assert bool(provider.named("delete_volume")) is deleted
    # An answer, yes or no, settles the mark; no answer keeps it for a later run.
    assert state.volume_pending.exists() is (answer == "")
    captured = capsys.readouterr()
    assert "delete volume v9" in captured.out
    assert "[y/N]" in captured.out
    if answer == "":
        assert "volume v9 kept" in captured.err
        assert "gpunit volume down" in captured.err


@pytest.mark.spec("volume:down:sweep-needs-a-terminal")
@pytest.mark.parametrize("tty", [False, True], ids=["pipe", "twin-terminal"])
def test_the_sweep_asks_only_a_terminal(
    tty: bool,
    cwd: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state = State(cwd)
    state.mark_volume_pending()
    monkeypatch.setattr("sys.stdin", TtyInput("y\n") if tty else io.StringIO("y\n"))
    provider = FakeProvider(volume_listings=[["v9"]])

    assert gpunit(["volume", "down"], provider=provider) == (0 if tty else 1)
    assert bool(provider.named("delete_volume")) is tty
    assert state.volume_pending.exists() is not tty
    captured = capsys.readouterr()
    assert ("[y/N]" in captured.out) is tty
    if not tty:
        assert "volume v9 kept: no answer; run gpunit volume down" in captured.err


@pytest.mark.spec("volume:down:ctrl-c-ends-the-sweep")
@pytest.mark.parametrize("ctrl_c", [True, False], ids=["ctrl-c", "twin-no"])
def test_ctrl_c_ends_the_sweep(
    ctrl_c: bool,
    cwd: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state = State(cwd)
    state.mark_volume_pending()
    monkeypatch.setattr("sys.stdin", TtyInput(""))
    asked: list[str] = []

    def answer(prompt: str) -> str:
        asked.append(prompt)
        if ctrl_c:
            raise KeyboardInterrupt
        return "n"

    monkeypatch.setattr("builtins.input", answer)
    provider = FakeProvider(volume_listings=[["v8", "v9"]])

    assert gpunit(["volume", "down"], provider=provider) == (130 if ctrl_c else 0)
    assert provider.named("delete_volume") == []
    assert ["v9" in prompt for prompt in asked] == (
        [False] if ctrl_c else [False, True]
    )
    assert state.volume_pending.exists() is ctrl_c
    if ctrl_c:
        assert "run gpunit volume down" in capsys.readouterr().err
