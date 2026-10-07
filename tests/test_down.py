from pathlib import Path

import pytest

from gpunit.provider import Lost
from gpunit.state import State
from tests.fakes import RECORD, FakeProvider
from tests.helpers import gpunit


def recorded(cwd: Path) -> State:
    state = State(cwd)
    state.keygen("gpunit-isekai")
    state.write(RECORD)
    state.write_known_hosts("[203.0.113.7]:40022 ssh-ed25519 AAAAhostkey")
    return state


@pytest.mark.spec("session:down:404-keeps-record")
def test_a_404_keeps_the_record(cwd: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state = recorded(cwd)

    assert gpunit(["down"], provider=FakeProvider(deletes={"pod-1": 404})) == 1
    assert state.pod.exists()
    assert "the key may be wrong" in capsys.readouterr().err


@pytest.mark.spec("session:down:success-clears")
def test_a_success_clears_the_record(cwd: Path) -> None:
    state = recorded(cwd)

    assert gpunit(["down"], provider=FakeProvider()) == 0
    for path in (state.pod, state.known_hosts, state.key, state.key_pub):
        assert not path.exists()


@pytest.mark.spec("session:down:sweep-unrecorded")
@pytest.mark.parametrize(
    ("answer", "code", "pending_kept"),
    [(204, 0, False), (500, 1, True)],
    ids=["swept", "sweep-failed"],
)
def test_the_sweep_removes_a_pod_no_record_names(
    answer: int, code: int, pending_kept: bool, cwd: Path
) -> None:
    state = State(cwd)
    state.mark_pending()
    provider = FakeProvider(
        listings=[[("pod-7", "RUNNING")]], deletes={"pod-7": answer}
    )

    assert gpunit(["down"], provider=provider) == code
    assert provider.named("delete") == [("pod-7",)]
    assert state.pending.exists() is pending_kept


@pytest.mark.spec("session:down:unreadable-listing-fails")
def test_an_unreadable_listing_fails(
    cwd: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = FakeProvider(listings=[Lost("pod listing returned HTTP 500: oops")])

    assert gpunit(["down"], provider=provider) == 1
    assert "no sweep was made" in capsys.readouterr().err


@pytest.mark.spec("session:key:deleted-at-teardown")
def test_the_keypair_leaves_with_the_pod(cwd: Path) -> None:
    state = recorded(cwd)

    assert gpunit(["down"], provider=FakeProvider()) == 0
    assert not state.key.exists()
    assert not state.key_pub.exists()
