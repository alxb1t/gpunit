"""Run each session test in its own directory, with OpenSSH stubbed and time faked."""

import os
import socket
from pathlib import Path

import pytest

from gpunit import library, lifecycle
from tests.fakes import SERVED, FakeClock
from tests.helpers import install_stubs, write_spec

# Writes the keypair `-f` names; `-lf -` answers $GPUNIT_TEST_SERVED for any key.
SSH_KEYGEN = f"""#!/bin/bash
if [ "$1" = "-lf" ]; then
  cat >/dev/null
  echo "256 ${{GPUNIT_TEST_SERVED:-{SERVED}}} no comment (ED25519)"
  exit 0
fi
while [ $# -gt 0 ]; do
  case "$1" in -f) f=$2; shift ;; -C) c=$2; shift ;; esac
  shift
done
echo PRIVATE > "$f"
echo "ssh-ed25519 AAAAstub $c" > "$f.pub"
"""

# Answers one host-key line, or nothing when $GPUNIT_TEST_NO_SCAN is set.
SSH_KEYSCAN = """#!/bin/bash
[ -z "${GPUNIT_TEST_NO_SCAN:-}" ] || exit 1
while [ $# -gt 1 ]; do
  [ "$1" = "-p" ] && port=$2
  shift
done
echo "# $1:$port SSH-2.0-OpenSSH_9.6"
echo "[$1]:$port ssh-ed25519 AAAAhostkey"
"""

# The tunnel: logs its argv to $GPUNIT_TEST_SSH_LOG, then holds, or exits at once
# when $GPUNIT_TEST_SSH_EXIT is set.
SSH = """#!/bin/bash
echo "$@" >> "${GPUNIT_TEST_SSH_LOG:-/dev/null}"
[ -z "${GPUNIT_TEST_SSH_EXIT:-}" ] || exit 1
exec sleep 30
"""


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> FakeClock:
    fake = FakeClock()
    monkeypatch.setattr(lifecycle, "CLOCK", lifecycle.Clock(fake.monotonic, fake.sleep))
    return fake


@pytest.fixture(scope="session")
def ssh_bin(tmp_path_factory: pytest.TempPathFactory) -> Path:
    # Once per session: macOS makes the first run of a new executable slow, and each
    # stub reads its behaviour from the test's environment, so they can be shared.
    scripts = {"ssh-keygen": SSH_KEYGEN, "ssh-keyscan": SSH_KEYSCAN, "ssh": SSH}
    return install_stubs(tmp_path_factory.mktemp("bin"), scripts)


@pytest.fixture
def stubs(ssh_bin: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("PATH", f"{ssh_bin}{os.pathsep}{os.environ['PATH']}")
    return ssh_bin


@pytest.fixture
def cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: FakeClock, stubs: Path
) -> Path:
    monkeypatch.chdir(tmp_path)
    write_spec(tmp_path)
    return tmp_path


@pytest.fixture
def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture
def dying_tunnel(cwd: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # Every tunnel logs its argv and exits at once; reopening waits 0.1s.
    tunnels = cwd / "tunnels.log"
    monkeypatch.setenv("GPUNIT_TEST_SSH_LOG", str(tunnels))
    monkeypatch.setenv("GPUNIT_TEST_SSH_EXIT", "1")
    monkeypatch.setattr(library, "TUNNEL_POLL_S", 0.1)
    monkeypatch.setattr(library, "REOPEN_FIRST_S", 0.1)
    return tunnels
