import os
from pathlib import Path

import pytest

from gpunit.state import Record, State, Window


@pytest.mark.spec("session:down:success-clears")
def test_the_record_round_trips(tmp_path: Path) -> None:
    state = State(tmp_path)
    assert state.read() is None

    record = Record(
        id="p1", image="img", host="1.2.3.4", port=40022, created="2026-10-07T00:00:00Z"
    )
    state.write(record)

    assert state.read() == record
    state.clear_session()
    assert state.read() is None


@pytest.mark.spec("session:key:fresh-per-session")
def test_the_key_files_are_0600(tmp_path: Path) -> None:
    state = State(tmp_path)

    public = state.keygen("gpunit-isekai")

    modes = {path.stat().st_mode & 0o777 for path in (state.key, state.key_pub)}
    assert modes == {0o600}
    assert public.startswith("ssh-ed25519 ") and public.endswith(" gpunit-isekai")


@pytest.mark.spec("session:key:dir-private")
def test_a_found_directory_is_made_private(tmp_path: Path) -> None:
    state = State(tmp_path)
    state.dir.mkdir()
    state.dir.chmod(0o755)
    assert state.dir.stat().st_mode & 0o777 == 0o755

    state.keygen("gpunit-isekai")

    assert state.dir.stat().st_mode & 0o777 == 0o700


@pytest.mark.spec("volume:up:datacenter-from-stock")
def test_the_window_round_trips(tmp_path: Path) -> None:
    state = State(tmp_path)
    assert state.window() is None

    window = Window(id="v1", datacenter="EU-RO-1", size_gb=60, ends="2026-10-15T14:30Z")
    state.write_window(window)

    assert state.window() == window
    assert state.volume == tmp_path / ".gpunit" / "volume"
    state.clear_window()
    assert state.window() is None


@pytest.mark.spec("volume:up:lost-create-exits-3")
def test_the_volume_pending_mark_is_its_own(tmp_path: Path) -> None:
    state = State(tmp_path)

    state.mark_volume_pending()
    assert state.volume_pending.exists()
    assert not state.pending.exists()
    state.clear_volume_pending()
    assert not state.volume_pending.exists()


@pytest.mark.spec("session:stock:waiting-marked")
def test_the_wait_mark_holds_this_process(tmp_path: Path) -> None:
    state = State(tmp_path)

    state.mark_waiting()
    assert state.waiting == tmp_path / ".gpunit" / "waiting"
    assert state.waiting.read_text(encoding="utf-8") == f"{os.getpid()}\n"
    assert sorted(path.name for path in state.dir.iterdir()) == ["waiting"]
    state.clear_waiting()
    assert not state.waiting.exists()
    state.clear_waiting()
    # A process refused beside another's wait leaves that process's mark.
    state.waiting.write_text(f"{os.getppid()}\n", encoding="utf-8")
    state.clear_waiting()
    assert state.waiting.read_text(encoding="utf-8") == f"{os.getppid()}\n"
