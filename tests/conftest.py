"""Run each session test in its own directory, with OpenSSH stubbed and time faked."""

import os
from pathlib import Path

import pytest

from gpunit import session
from tests.fakes import SERVED, FakeClock
from tests.helpers import write_spec

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
    monkeypatch.setattr(session, "CLOCK", session.Clock(fake.monotonic, fake.sleep))
    return fake


@pytest.fixture
def stubs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stubbed = (("ssh-keygen", SSH_KEYGEN), ("ssh-keyscan", SSH_KEYSCAN), ("ssh", SSH))
    for name, script in stubbed:
        (bin_dir / name).write_text(script, encoding="utf-8")
        (bin_dir / name).chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return bin_dir


@pytest.fixture
def cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: FakeClock, stubs: Path
) -> Path:
    monkeypatch.chdir(tmp_path)
    write_spec(tmp_path)
    return tmp_path
