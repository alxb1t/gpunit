from pathlib import Path

import pytest

from gpunit.state import Record, State


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
