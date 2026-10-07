from pathlib import Path

import pytest

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
