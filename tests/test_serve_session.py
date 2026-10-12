import os
import signal
import socket
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import NoReturn

import pytest

from gpunit.provider import Provider
from gpunit.serve import session, table
from gpunit.spec import Spec
from tests.fakes import (
    BOOT_LOG,
    Answer,
    FakeOpener,
    FakeProvider,
    _Response,
)

MODELS = (200, b'{"object": "list", "data": [{"id": "qwen3-4b"}]}')
NOT_YET = urllib.error.URLError(ConnectionRefusedError(61, "Connection refused"))


@pytest.fixture
def home(isolated_home: Path, cwd: Path) -> Path:
    return isolated_home


def no_question(prompt: str) -> NoReturn:
    raise AssertionError(f"asked: {prompt}")


def leaves(prompt: str) -> str:
    return "/exit"


def served(
    provider: Provider,
    opener: FakeOpener,
    *,
    yes: bool = True,
    ask: Callable[[str], str] = no_question,
    api: bool = False,
    read: Callable[[str], str] = leaves,
) -> int:
    return session.serve(
        "qwen3-4b",
        7200,
        api=api,
        volume=None,
        max_hourly=None,
        yes=yes,
        think=False,
        provider=provider,
        ask=ask,
        read=read,
        opener=opener,
    )


def created_spec(provider: FakeProvider) -> Spec:
    [(spec, *_)] = provider.named("create")
    assert isinstance(spec, Spec)
    return spec


def local_port(provider: FakeProvider) -> int:
    [port] = created_spec(provider).ports
    return port.local


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

    assert asked == ["rent serve-qwen3-4b for at most $1.61? [y/N] "]
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
    assert "at most $1.61 for 7200s and a 1200s wait for SSH" in err
    assert len(provider.named("create")) == 1


@pytest.mark.spec("serve:price:covers-the-wait")
def test_the_agreed_price_covers_the_ceiling_and_the_ssh_wait(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = FakeProvider()
    asked: list[str] = []

    def ask(prompt: str) -> str:
        asked.append(prompt)
        return "n"

    code = session.serve(
        "qwen3-4b",
        1800,
        api=False,
        volume=None,
        max_hourly=None,
        yes=False,
        think=False,
        provider=provider,
        ask=ask,
        opener=FakeOpener(MODELS),
    )

    # The pull bills before boot arms the ceiling: $0.69/h × (1800s + 1200s), up.
    assert code == 1
    assert asked == ["rent serve-qwen3-4b for at most $0.58? [y/N] "]
    assert "at most $0.58 for 1800s and a 1200s wait for SSH" in capsys.readouterr().err


@pytest.mark.spec("serve:wait:awaited")
def test_the_model_is_awaited_through_the_tunnel_with_the_key(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = FakeProvider()
    opener = FakeOpener(NOT_YET, (503, b""), NOT_YET, MODELS)

    assert served(provider, opener) == 0

    key = created_spec(provider).env["VLLM_API_KEY"]
    local = local_port(provider)
    assert len(opener.requests) == 4
    for request in opener.requests:
        assert request.full_url == f"http://127.0.0.1:{local}/v1/models"
        assert request.get_header("Authorization") == f"Bearer {key}"
    assert opener.timeouts == [5, 5, 5, 5]
    err = capsys.readouterr().err
    assert f"qwen3-4b answers on http://127.0.0.1:{local}/v1" in err
    assert provider.named("delete") == [("pod-1",)]


@pytest.mark.spec("serve:wait:bound-tears-down")
def test_a_model_that_never_answers_is_refused_and_torn_down(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = FakeProvider(logs=[BOOT_LOG] * 3 + [["50%"]])
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


class InterruptingOpener(FakeOpener):
    """Answer the wait, then send this process `number` from the hold's first poll."""

    def __init__(self, *answers: Answer, number: int = signal.SIGINT) -> None:
        super().__init__(*answers)
        self.number = number

    def open(
        self,
        fullurl: str | urllib.request.Request,
        data: object = None,
        timeout: float | None = None,
    ) -> _Response:
        if len(self.requests) == 1:
            os.kill(os.getpid(), self.number)
        return super().open(fullurl, data, timeout)


@pytest.mark.spec("serve:api:prints-the-endpoint")
@pytest.mark.parametrize("end", ["quiet", "interrupt"])
def test_api_prints_the_endpoint_and_holds_until_the_end(
    end: str,
    home: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    provider = FakeProvider()
    if end == "quiet":
        # The wait's answer, one in the hold, then silence as a stopped pod gives.
        opener = FakeOpener(MODELS, MODELS, NOT_YET, NOT_YET)
    else:
        opener = InterruptingOpener(MODELS, MODELS)

    code = served(provider, opener, api=True)

    out, err = capsys.readouterr()
    key = created_spec(provider).env["VLLM_API_KEY"]
    assert out.splitlines() == [
        f"OPENAI_BASE_URL=http://127.0.0.1:{local_port(provider)}/v1",
        f"OPENAI_API_KEY={key}",
    ]
    assert len(key) >= 32
    assert provider.named("delete") == [("pod-1",)]
    if end == "quiet":
        assert code == 1
        assert len(opener.requests) == 4
        assert "refused: the model has not answered for 60s" in err
    else:
        assert code == 128 + signal.SIGINT


@pytest.mark.spec("serve:api:key-required")
def test_the_pod_requires_a_key_of_its_own_each_session(home: Path) -> None:
    keys = []
    for _ in range(2):
        provider = FakeProvider()
        opener = FakeOpener(MODELS, NOT_YET, NOT_YET)
        assert served(provider, opener, api=True) == 1
        keys.append(created_spec(provider).env["VLLM_API_KEY"])
        assert {request.get_header("Authorization") for request in opener.requests} == {
            f"Bearer {keys[-1]}"
        }

    assert all(len(key) >= 32 for key in keys)
    assert keys[0] != keys[1]


@pytest.mark.spec("serve:chat:eof-ends")
@pytest.mark.parametrize("said", ["/exit", "eof"])
def test_the_end_of_the_chat_closes_the_session(said: str, home: Path) -> None:
    provider = FakeProvider()

    def read(prompt: str) -> str:
        if said == "eof":
            raise EOFError
        return said

    assert served(provider, FakeOpener(MODELS), read=read) == 0
    assert provider.named("delete") == [("pod-1",)]


@pytest.mark.spec("serve:chat:stopped-server-ends")
def test_a_stopped_server_ends_the_chat_and_closes_the_session(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = FakeProvider()
    # The wait's answer, then the chat's request refused, as a stopped server gives.
    opener = FakeOpener(MODELS, NOT_YET)

    assert served(provider, opener, read=lambda prompt: "hi") == 1

    assert len(opener.requests) == 2
    assert "the server stopped answering" in capsys.readouterr().err
    assert provider.named("delete") == [("pod-1",)]


@pytest.mark.spec("serve:wait:busy-local-port-is-skipped")
def test_a_busy_local_port_is_skipped_before_the_price(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = FakeProvider()
    asked: list[str] = []

    def ask(prompt: str) -> str:
        asked.append(prompt)
        return "y"

    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        taken = busy.getsockname()[1]
        # The served port answers on this machine already, as a local vLLM's 8000 would.
        monkeypatch.setattr(table, "PORT", taken)
        code = served(provider, FakeOpener(MODELS), yes=False, ask=ask)

    [port] = created_spec(provider).ports
    assert code == 0
    assert len(asked) == 1
    assert port.remote == taken
    assert port.local != taken
    assert f"answers on http://127.0.0.1:{port.local}/v1" in capsys.readouterr().err


@pytest.mark.spec("serve:price:interrupt-is-no")
def test_an_interrupt_at_the_question_rents_nothing(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = FakeProvider()

    def interrupted(prompt: str) -> str:
        raise KeyboardInterrupt

    assert served(provider, FakeOpener(MODELS), yes=False, ask=interrupted) == 130
    assert provider.named("create") == []
    err = capsys.readouterr().err
    assert "not rented" in err
    assert "Traceback" not in err


@pytest.mark.spec("cli:exits:serve-signal-is-128-plus-n")
def test_a_sigterm_on_the_held_endpoint_exits_143(home: Path) -> None:
    provider = FakeProvider()
    opener = InterruptingOpener(MODELS, MODELS, number=signal.SIGTERM)

    assert served(provider, opener, api=True) == 143
    assert provider.named("delete") == [("pod-1",)]
