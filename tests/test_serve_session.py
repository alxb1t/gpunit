import urllib.error
from collections.abc import Callable
from pathlib import Path
from typing import NoReturn

import pytest

from gpunit.provider import Provider
from gpunit.serve import session, table
from gpunit.spec import Spec
from tests.fakes import FakeOpener, FakeProvider

MODELS = (200, b'{"object": "list", "data": [{"id": "qwen3-4b"}]}')
NOT_YET = urllib.error.URLError(ConnectionRefusedError(61, "Connection refused"))


@pytest.fixture
def home(
    tmp_path: Path, cwd: Path, free_port: int, monkeypatch: pytest.MonkeyPatch
) -> Path:
    # A free port stands for 8000, which this machine may already serve.
    monkeypatch.setattr(table, "PORT", free_port)
    place = tmp_path / "home"
    monkeypatch.setenv("HOME", str(place))
    return place


def no_question(prompt: str) -> NoReturn:
    raise AssertionError(f"asked: {prompt}")


def served(
    provider: Provider,
    opener: FakeOpener,
    *,
    yes: bool = True,
    ask: Callable[[str], str] = no_question,
) -> int:
    return session.serve(
        "qwen3-4b",
        7200,
        api=False,
        volume=None,
        max_hourly=None,
        yes=yes,
        think=False,
        provider=provider,
        ask=ask,
        opener=opener,
    )


def created_spec(provider: FakeProvider) -> Spec:
    [(spec, *_)] = provider.named("create")
    assert isinstance(spec, Spec)
    return spec


@pytest.mark.spec("serve:price:no-by-default")
@pytest.mark.parametrize("answer", ["", "n", "y"], ids=["empty", "no", "twin-yes"])
def test_nothing_is_rented_unless_the_operator_says_y(
    answer: str, home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = FakeProvider()
    asked: list[str] = []

    def ask(prompt: str) -> str:
        asked.append(prompt)
        return answer

    code = served(provider, FakeOpener(MODELS), yes=False, ask=ask)

    assert asked == ["rent serve-qwen3-4b for at most $1.38? [y/N] "]
    if answer == "y":
        # The twin: a `y` rents.
        assert code == 0
        assert len(provider.named("create")) == 1
        return
    assert code == 1
    assert provider.named("create") == []
    assert "refused: not rented" in capsys.readouterr().err


@pytest.mark.spec("serve:price:no-by-default")
def test_the_end_of_input_is_a_no(home: Path) -> None:
    provider = FakeProvider()

    def ended(prompt: str) -> str:
        raise EOFError

    assert served(provider, FakeOpener(MODELS), yes=False, ask=ended) == 1
    assert provider.named("create") == []


@pytest.mark.spec("serve:price:yes-skips")
def test_yes_prints_the_prices_and_opens_without_a_question(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = FakeProvider()

    assert served(provider, FakeOpener(MODELS)) == 0

    err = capsys.readouterr().err
    assert "price: NVIDIA RTX A5000 $0.69/h" in err
    assert "at most $1.38 for 7200s" in err
    assert len(provider.named("create")) == 1


@pytest.mark.spec("serve:wait:awaited")
def test_the_model_is_awaited_through_the_tunnel_with_the_key(
    home: Path, free_port: int, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = FakeProvider()
    opener = FakeOpener(NOT_YET, (503, b""), NOT_YET, MODELS)

    assert served(provider, opener) == 0

    key = created_spec(provider).env["VLLM_API_KEY"]
    assert len(opener.requests) == 4
    for request in opener.requests:
        assert request.full_url == f"http://127.0.0.1:{free_port}/v1/models"
        assert request.get_header("Authorization") == f"Bearer {key}"
    assert opener.timeouts == [5, 5, 5, 5]
    err = capsys.readouterr().err
    assert f"qwen3-4b answers on http://127.0.0.1:{free_port}/v1" in err
    assert provider.named("delete") == [("pod-1",)]


@pytest.mark.spec("serve:wait:bound-tears-down")
def test_a_model_that_never_answers_is_refused_and_torn_down(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = FakeProvider(logs=[["gpunit host key: SHA256:served"]] * 3 + [["50%"]])
    # One answer a poll: 1200s at 5s, and the first.
    opener = FakeOpener(*[NOT_YET] * (1200 // 5 + 1))

    assert served(provider, opener) == 1

    err = capsys.readouterr().err
    assert "refused: the model did not load within 1200s" in err
    assert "loading: 50%" in err
    assert "answers on" not in err
    assert provider.named("delete") == [("pod-1",)]
    assert ("pod-1", 50, None) in provider.named("log")


@pytest.mark.spec("serve:wait:state-per-model")
def test_the_session_files_are_the_models_wherever_it_runs(
    home: Path, cwd: Path
) -> None:
    provider = FakeProvider(deletes={"pod-1": 500})

    assert served(provider, FakeOpener(MODELS)) == 1

    place = home / ".local" / "state" / "gpunit" / "serve" / "qwen3-4b" / ".gpunit"
    assert (place / "pod").is_file()
    assert not (cwd / ".gpunit").exists()
    assert place.stat().st_mode & 0o777 == 0o700


@pytest.mark.spec("serve:wait:state-per-model")
def test_down_serve_reads_the_models_record(home: Path, cwd: Path) -> None:
    left = FakeProvider(deletes={"pod-1": 500})
    assert served(left, FakeOpener(MODELS)) == 1

    provider = FakeProvider()
    assert session.down("qwen3-4b", provider) == 0
    assert provider.named("delete") == [("pod-1",)]
    assert provider.named("list") == [("serve-qwen3-4b", created_spec(left).image)]
