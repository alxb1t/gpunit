import json
import pwd
import re
from pathlib import Path
from typing import NoReturn

import pytest

from gpunit import ledger
from gpunit.state import State
from tests.fakes import RUNNING, FakeProvider
from tests.helpers import IMAGE, VALID, gpunit, write_spec

UTC = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")


def lines() -> list[dict[str, object]]:
    text = ledger.path().read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines()]


@pytest.mark.spec("spend:ledger:create-is-recorded")
def test_a_create_is_recorded(cwd: Path) -> None:
    write_spec(cwd, VALID.replace('["RTX 4090", "RTX A6000"]', '["NVIDIA A40"]'))

    assert gpunit(["up"], provider=FakeProvider(creates=["pod-9"])) == 0
    [line] = lines()
    assert {key: line[key] for key in ("id", "project", "card", "image")} == {
        "id": "pod-9",
        "project": "isekai",
        "card": "NVIDIA A40",
        "image": IMAGE,
    }
    assert UTC.fullmatch(str(line["at"]))
    assert ledger.path().stat().st_mode & 0o777 == 0o600
    assert ledger.path().parent.stat().st_mode & 0o777 == 0o700


@pytest.mark.spec("spend:ledger:sweep-is-recorded")
@pytest.mark.parametrize("answer", [204, 500], ids=["swept", "delete-failed"])
def test_a_swept_pod_is_recorded(answer: int, cwd: Path) -> None:
    provider = FakeProvider(
        listings=[[("pod-7", "RUNNING")]], deletes={"pod-7": answer}
    )

    gpunit(["down"], provider=provider)
    assert [(line["id"], line["project"], line["card"]) for line in lines()] == [
        ("pod-7", "isekai", None)
    ]


@pytest.mark.spec("spend:ledger:holds-nothing-else")
def test_the_line_holds_nothing_else(cwd: Path) -> None:
    assert gpunit(["up"], provider=FakeProvider()) == 0
    [line] = lines()
    assert sorted(line) == ["at", "card", "id", "image", "project"]
    text = ledger.path().read_text(encoding="utf-8")
    for leak in (str(RUNNING.host), str(cwd), "AAAAstub", "PRIVATE"):
        assert leak not in text


@pytest.mark.spec("spend:ledger:failure-never-blocks")
@pytest.mark.parametrize("guarded", [True, False], ids=["record", "twin-unguarded"])
def test_an_unwritable_ledger_blocks_nothing(
    guarded: bool,
    cwd: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A file where the ledger's directory goes: no mkdir or chmod can get past it.
    ledger.path().parent.parent.mkdir(parents=True)
    ledger.path().parent.write_text("", encoding="utf-8")

    if guarded:
        assert gpunit(["up"], provider=FakeProvider()) == 0
        assert State(cwd).read() is not None
        assert "the ledger could not be written" in capsys.readouterr().err
    else:
        # The twin: without the guard, the ledger's fault ends `up`.
        monkeypatch.setattr(ledger, "record", _unguarded)
        with pytest.raises(OSError):
            gpunit(["up"], provider=FakeProvider())


def _unguarded(project: str, pod_id: str, card: str | None, image: str) -> None:
    ledger.path().parent.mkdir(mode=0o700, parents=True, exist_ok=True)


@pytest.mark.spec("spend:ledger:failure-never-blocks")
def test_no_home_blocks_nothing(
    cwd: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # No HOME and no passwd entry: `Path.home()` raises `RuntimeError`, not `OSError`.
    monkeypatch.delenv("HOME")
    monkeypatch.setattr(pwd, "getpwuid", _no_entry)

    assert gpunit(["up"], provider=FakeProvider(creates=["pod-9"])) == 0
    assert State(cwd).read() is not None
    assert "the ledger could not be written" in capsys.readouterr().err

    # pod-7 is not the recorded pod: the sweep names it in the ledger, then deletes it.
    provider = FakeProvider(listings=[[("pod-9", "RUNNING"), ("pod-7", "RUNNING")]])
    assert gpunit(["down"], provider=provider) == 0
    assert provider.named("delete") == [("pod-9",), ("pod-7",)]
    assert "the ledger could not be written" in capsys.readouterr().err


def _no_entry(uid: int) -> NoReturn:
    raise KeyError(f"getpwuid(): uid not found: {uid}")


@pytest.mark.spec("spend:report:by-project")
def test_the_first_line_for_an_id_wins() -> None:
    ledger.path().parent.mkdir(parents=True)
    first = {"id": "p1", "project": "isekai", "card": "A40", "image": "i", "at": "t"}
    later = {**first, "project": "other"}
    no_key = {"id": "p2", "project": "isekai"}
    ledger.path().write_text(
        "\n".join(
            [json.dumps(first), "not json", "[]", json.dumps(no_key), json.dumps(later)]
        )
        + "\n",
        encoding="utf-8",
    )

    assert ledger.read() == {"p1": ledger.Entry("p1", "isekai", "A40", "i", "t")}


@pytest.mark.spec("spend:report:unattributed")
def test_a_missing_ledger_is_empty() -> None:
    assert ledger.read() == {}
