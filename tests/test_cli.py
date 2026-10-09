import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import TextIO

import pytest

from gpunit import log
from tests.fakes import FakeProvider
from tests.helpers import NO_REQUESTS, gpunit, write_spec


@pytest.mark.spec("cli:verbs:unknown-verb-exits-2")
def test_an_unknown_verb_exits_2_with_a_usage_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    write_spec(tmp_path)

    assert gpunit(["frobnicate"], provider=NO_REQUESTS) == 2
    err = capsys.readouterr().err
    assert "usage: gpunit" in err


@pytest.mark.spec("cli:verbs:run-without-command-exits-2")
@pytest.mark.parametrize("argv", [["run"], ["run", "--"]])
def test_run_without_a_command_exits_2_naming_the_form(
    argv: list[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    write_spec(tmp_path)

    assert gpunit(argv, provider=NO_REQUESTS) == 2
    assert "gpunit run -- <command>" in capsys.readouterr().err


@pytest.fixture
def dead_pipe() -> Iterator[TextIO]:
    read, write = os.pipe()
    os.close(read)
    stream = os.fdopen(write, "w")
    yield stream
    try:
        stream.close()
    except BrokenPipeError:
        pass  # close flushes what the dead pipe refused


def _unguarded(line: str) -> None:
    print(line, file=sys.stderr, flush=True)


@pytest.mark.spec("cli:exits:closed-stderr")
@pytest.mark.parametrize("guarded", [True, False], ids=["sink", "twin-unguarded"])
def test_a_dead_pipe_on_stderr_ends_no_teardown(
    guarded: bool,
    cwd: Path,
    dead_pipe: TextIO,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeProvider()
    monkeypatch.setattr(sys, "stderr", dead_pipe)
    if guarded:
        assert gpunit(["run", "--", "true"], provider=provider) == 0
        assert provider.named("delete") == [("pod-1",)]
        assert not (cwd / ".gpunit" / "pod").exists()
    else:
        # The twin: without the default sink, the first line ends the run.
        monkeypatch.setattr(log, "_sink", _unguarded)
        with pytest.raises(BrokenPipeError):
            gpunit(["run", "--", "true"], provider=provider)


# The CLI on the fakes, in a process of its own: no key, no network.
ON_THE_FAKES = """
from gpunit import cli
from tests.fakes import FakeProvider
cli.main(["run", "--", "true"], provider=FakeProvider())
"""


@pytest.mark.spec("cli:exits:closed-stderr")
def test_a_dead_pipe_on_stderr_leaves_the_process_exit_code(cwd: Path) -> None:
    # Only a real process meets the interpreter's last flush of stderr.
    root = Path(__file__).resolve().parent.parent
    env = {key: value for key, value in os.environ.items() if key != "RUNPOD_API_KEY"}
    env["PYTHONPATH"] = str(root)
    read, write = os.pipe()
    os.close(read)
    try:
        done = subprocess.run(
            [sys.executable, "-c", ON_THE_FAKES],
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=write,
            timeout=60,
            check=False,
        )
    finally:
        os.close(write)

    assert done.returncode == 0
    assert not (cwd / ".gpunit" / "pod").exists()
