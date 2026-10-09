import os
import signal
import socket
import sys
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from pathlib import Path
from types import FrameType

import pytest

from gpunit import library
from gpunit.library import Interrupted, Refused, Session, TeardownFailed
from gpunit.provider import Lost, Provider
from gpunit.runpod import RunPod
from gpunit.spec import load_spec
from gpunit.state import State
from tests.fakes import KEY_LINE, RECORD, FakeOpener, FakeProvider, fixture, page, quiet
from tests.helpers import IMAGE, NO_REQUESTS, install_stubs, with_port

KEY = "rpa_mapping_key"

# A tunnel that listens on the local side of its `-L`, so a connection can be made.
LISTENING_SSH = f"""#!{sys.executable}
import re, socket, sys, time
local = next(int(m[1]) for arg in sys.argv if (m := re.match(r"-L(\\d+):", arg)))
server = socket.create_server(("127.0.0.1", local))
time.sleep(30)
"""


def opened(
    cwd: Path, provider: Provider, say: Callable[[str], None] | None = None
) -> AbstractContextManager[Session]:
    return library._open(load_spec(cwd / "gpunit.toml"), provider, State(cwd), say)


def until(done: Callable[[], bool], seconds: float = 10.0) -> bool:
    deadline = time.monotonic() + seconds
    while not done():
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.05)
    return True


def accepts(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


@pytest.fixture
def saved_handlers() -> Iterator[None]:
    saved = {number: signal.getsignal(number) for number in library.SIGNALS}
    yield
    for number, handler in saved.items():
        signal.signal(number, handler)


class SignallingProvider(FakeProvider):
    """Send this process `SIGINT` from inside the teardown's delete."""

    def delete(self, pod_id: str) -> int:
        os.kill(os.getpid(), signal.SIGINT)
        return super().delete(pod_id)


@pytest.mark.spec("library:session:yields-the-session")
def test_the_block_sees_the_session(
    cwd: Path, free_port: int, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    with_port(cwd, free_port)
    listening = install_stubs(tmp_path / "listening", {"ssh": LISTENING_SSH})
    monkeypatch.setenv("PATH", f"{listening}{os.pathsep}{os.environ['PATH']}")

    with opened(cwd, FakeProvider()) as s:
        assert s.host == "203.0.113.7"
        assert s.pod_id == "pod-1"
        assert s.image == IMAGE
        assert s.ssh[:3] == ("ssh", "-F", "none")
        assert s.ssh[-3:] == ("root@203.0.113.7", "-p", "40022")
        assert s.port(8188) == free_port
        assert until(lambda: accepts(free_port))
        with pytest.raises(Refused):
            s.port(9999)


@pytest.mark.spec("library:session:exit-tears-down")
def test_the_blocks_end_tears_down(cwd: Path) -> None:
    provider = FakeProvider()

    with opened(cwd, provider):
        assert (cwd / ".gpunit" / "pod").exists()

    assert provider.named("delete") == [("pod-1",)]
    assert not (cwd / ".gpunit" / "pod").exists()


@pytest.mark.spec("library:session:error-tears-down")
def test_an_error_in_the_block_tears_down(cwd: Path) -> None:
    provider = FakeProvider()

    with pytest.raises(ValueError, match="the caller's"), opened(cwd, provider):
        raise ValueError("the caller's")

    assert provider.named("delete") == [("pod-1",)]
    assert not (cwd / ".gpunit" / "pod").exists()


@pytest.mark.spec("library:errors:refused")
def test_a_refusal_raises_refused(cwd: Path) -> None:
    State(cwd).write(RECORD)
    provider = FakeProvider()

    with pytest.raises(Refused, match="already recorded"), opened(cwd, provider):
        pass

    assert provider.named("create") == []
    assert provider.named("delete") == []
    assert State(cwd).read() == RECORD


@pytest.mark.spec("library:errors:lost")
def test_a_lost_create_raises_lost_after_the_sweep(cwd: Path) -> None:
    provider = FakeProvider(
        creates=[Lost("create got no answer")], listings=[[], [("pod-1", "RUNNING")]]
    )

    with pytest.raises(Lost), opened(cwd, provider):
        pass

    assert provider.named("delete") == [("pod-1",)]
    assert not (cwd / ".gpunit" / "pending").exists()


@pytest.mark.spec("library:errors:teardown-failed")
@pytest.mark.parametrize(
    "ended", [None, ValueError("the caller's")], ids=["ok", "raised"]
)
def test_a_failed_teardown_raises_teardown_failed(
    ended: Exception | None, cwd: Path
) -> None:
    provider = FakeProvider(deletes={"pod-1": 404})

    with pytest.raises(TeardownFailed) as failed, opened(cwd, provider):
        if ended is not None:
            raise ended

    assert failed.value.__cause__ is ended
    assert (cwd / ".gpunit" / "pod").exists()


@pytest.mark.spec("library:signals:term-raises")
def test_sigterm_ends_the_block_and_tears_down(cwd: Path, saved_handlers: None) -> None:
    provider = FakeProvider()

    with pytest.raises(Interrupted) as interrupted, opened(cwd, provider):
        os.kill(os.getpid(), signal.SIGTERM)
        time.sleep(5)

    assert interrupted.value.signal == 15
    assert isinstance(interrupted.value, KeyboardInterrupt)
    assert provider.named("delete") == [("pod-1",)]
    assert not (cwd / ".gpunit" / "pod").exists()


@pytest.mark.spec("library:signals:teardown-shielded")
@pytest.mark.parametrize("shielded", [True, False], ids=["shield", "twin-unshielded"])
def test_a_signal_during_the_teardown_is_ignored(
    shielded: bool, cwd: Path, monkeypatch: pytest.MonkeyPatch, saved_handlers: None
) -> None:
    provider = SignallingProvider()
    if shielded:
        with opened(cwd, provider):
            pass
        assert provider.named("delete") == [("pod-1",)]
        assert not (cwd / ".gpunit" / "pod").exists()
    else:
        # The twin: without the shield, the signal cuts the delete short.
        monkeypatch.setattr(library._Signals, "shield", lambda self: None)
        with pytest.raises(Interrupted), opened(cwd, provider):
            pass
        assert (cwd / ".gpunit" / "pod").exists()


def callers(number: int, frame: FrameType | None) -> None:
    """Stand for a handler the caller set before the session."""


@pytest.mark.spec("library:signals:handlers-restored")
def test_the_callers_handlers_come_back(cwd: Path, saved_handlers: None) -> None:
    for number in library.SIGNALS:
        signal.signal(number, callers)

    with opened(cwd, FakeProvider()):
        # The twin: inside the block the handlers are the session's.
        assert all(signal.getsignal(n) is not callers for n in library.SIGNALS)

    assert all(signal.getsignal(n) is callers for n in library.SIGNALS)


@pytest.mark.spec("library:signals:main-thread-only")
def test_another_thread_is_refused(cwd: Path) -> None:
    raised: list[BaseException] = []

    def open_here() -> None:
        try:
            with opened(cwd, NO_REQUESTS):
                pass
        except BaseException as fault:  # handed to the main thread to assert on
            raised.append(fault)

    thread = threading.Thread(target=open_here)
    thread.start()
    thread.join()

    assert len(raised) == 1
    assert isinstance(raised[0], Refused)
    assert "main thread" in str(raised[0])


@pytest.mark.spec("library:tunnel:reopened")
def test_a_dead_tunnel_is_reopened(
    cwd: Path, free_port: int, dying_tunnel: Path
) -> None:
    with_port(cwd, free_port)
    tunnels = dying_tunnel
    lines: list[str] = []

    def opened_twice() -> bool:
        return tunnels.exists() and len(tunnels.read_text().splitlines()) >= 2

    with opened(cwd, FakeProvider(), lines.append):
        assert until(opened_twice)

    assert f"-L{free_port}:localhost:8188" in tunnels.read_text().splitlines()[1]
    assert any("reopening it in 0.1s" in line for line in lines)


@pytest.mark.spec("library:say:sink")
def test_the_lines_go_to_the_sink(cwd: Path, capfd: pytest.CaptureFixture[str]) -> None:
    lines: list[str] = []

    with opened(cwd, FakeProvider(), lines.append):
        pass

    assert any("session up" in line for line in lines)
    assert any("deleted" in line for line in lines)
    assert capfd.readouterr().err == ""


@pytest.mark.spec("library:environ:key-from-mapping")
def test_the_key_comes_from_the_mapping(
    cwd: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("RUNPOD_API_KEY", raising=False)
    opener = FakeOpener(
        (200, page([], None)),
        (200, fixture("gpu.json")),
        (200, fixture("gpu.json")),
        (201, fixture("pod_created.json")),
        (200, fixture("pod_running.json")),
        quiet(f'data: {{"line": "{KEY_LINE}"}}\n'.encode()),
        (204, b""),
        (200, page([], None)),
    )
    monkeypatch.setattr(
        library, "RunPod", lambda environ: RunPod(environ, opener=opener)
    )

    with library.session(
        cwd / "gpunit.toml", environ={"RUNPOD_API_KEY": KEY}, cwd=cwd
    ) as s:
        assert s.pod_id == "pod-abc123"

    assert opener.answers == []
    headers = {request.get_header("Authorization") for request in opener.requests}
    assert headers == {f"Bearer {KEY}"}
