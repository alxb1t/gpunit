import os
import signal
import socket
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import NoReturn

import pytest

from gpunit import log
from gpunit.provider import PodInfo, Provider, VolumeInfo
from gpunit.runpod import RunPod
from gpunit.serve import session, table
from gpunit.spec import Spec
from gpunit.state import State
from tests.fakes import (
    RUNNING,
    Answer,
    FakeOpener,
    FakeProvider,
    _Response,
    fixture,
)
from tests.helpers import gpunit, open_window

MODELS = (200, b'{"object": "list", "data": [{"id": "qwen3-4b"}]}')
NOT_YET = urllib.error.URLError(ConnectionRefusedError(61, "Connection refused"))
EXITED = PodInfo(status="EXITED", host=None, port=None)
# What `log.utc` answers in a test that patches it: the record's `created`.
CREATED = "2026-10-14T00:00:00Z"


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
    ceiling_s: int = 7200,
) -> int:
    return session.serve(
        "qwen3-4b",
        ceiling_s,
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


def kept_path() -> Path:
    return session.home("qwen3-4b") / "pod.log"


def said_pod(err: str) -> list[str]:
    return [line.split(" pod: ", 1)[1] for line in err.splitlines() if " pod: " in line]


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
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(log, "utc", lambda: CREATED)
    provider = FakeProvider(since_logs=[["10%"], ["10%", "50%"]])
    # One answer a poll: 1200s at 5s, and the first.
    opener = FakeOpener(*[NOT_YET] * (1200 // 5 + 1))

    assert served(provider, opener) == 1

    err = capsys.readouterr().err
    assert "refused: the model did not load within 1200s" in err
    assert "loading: 50%" in err
    assert "answers on" not in err
    assert provider.named("delete") == [("pod-1",)]
    # Every read the wait makes is the log since the create.
    assert ("pod-1", 50, CREATED) in provider.named("log")
    assert ("pod-1", 50, None) not in provider.named("log")


@pytest.mark.spec("serve:wait:dead-pod-ends-the-wait")
def test_a_dead_pod_ends_the_wait_and_closes_the_session(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lines = [f"vllm {n}" for n in range(35)]
    # `up`'s poll, the wait's to the log's read at 30s, then EXITED on every poll.
    provider = FakeProvider(gets=[RUNNING] * 8 + [EXITED], since_logs=[lines])
    opener = FakeOpener(*[NOT_YET] * 9)

    assert served(provider, opener) == 1

    err = capsys.readouterr().err
    assert "refused: the pod stopped while the model loaded" in err
    assert "did not load within" not in err
    assert len(opener.requests) == 9
    assert provider.named("delete") == [("pod-1",)]
    assert said_pod(err) == lines[-30:]
    assert f"the pod's log is kept at {kept_path()}" in err


@pytest.mark.spec("serve:wait:log-lines-cleaned")
def test_printed_log_lines_are_cleaned(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    raw = "\x1b]0;owned\x07loading\x1b[2J 50%\x9b"
    # `up`'s poll, the wait's to the log's read at 30s, then EXITED on every poll.
    provider = FakeProvider(gets=[RUNNING] * 8 + [EXITED], since_logs=[[raw]])

    assert served(provider, FakeOpener(*[NOT_YET] * 9)) == 1

    err = capsys.readouterr().err
    printed = [line for line in err.splitlines() if "ownedloading" in line]
    assert [line.split(": ", 1)[0][21:] for line in printed] == ["loading", "pod"]
    for line in printed:
        assert line.endswith(": ]0;ownedloading[2J 50%")
    assert kept_path().read_text(encoding="utf-8") == f"{raw}\n"


@pytest.mark.spec("serve:wait:running-pod-waits")
@pytest.mark.parametrize(
    "gets",
    [[RUNNING], [RUNNING, RUNNING, EXITED, RUNNING]],
    ids=["running", "one-exited"],
)
def test_a_running_pod_keeps_the_wait(
    gets: list[PodInfo], home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = FakeProvider(gets=gets)
    opener = FakeOpener(*[NOT_YET] * 4, MODELS)

    assert served(provider, opener) == 0

    err = capsys.readouterr().err
    assert "refused" not in err
    assert "qwen3-4b answers on" in err
    # One status read for each poll the model did not answer, after `up`'s.
    assert len(provider.named("get")) == 1 + 4


@pytest.mark.spec("serve:wait:log-kept")
def test_the_pods_log_is_kept_and_the_next_session_starts_without_it(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Reads at 30s and 60s, the second shorter; the model answers at 65s.
    provider = FakeProvider(since_logs=[["a", "b", "c"], ["a"]])
    opener = FakeOpener(*[NOT_YET] * 13, MODELS)
    # The stamp says whether the create had been asked when it was taken.
    utc = log.utc
    monkeypatch.setattr(
        log, "utc", lambda _=0: "after" if provider.named("create") else "before"
    )

    assert served(provider, opener) == 0

    kept = kept_path()
    assert kept.read_text(encoding="utf-8") == "a\nb\nc\n"
    assert kept.stat().st_mode & 0o777 == 0o600
    since = [call[2] for call in provider.named("log") if call[2] is not None]
    assert since == ["before", "before"]
    monkeypatch.setattr(log, "utc", utc)

    assert served(FakeProvider(), FakeOpener(MODELS)) == 0
    assert not kept.exists()


@pytest.mark.spec("serve:wait:log-kept")
def test_a_refused_serve_keeps_the_last_pods_log(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lines = [f"vllm {n}" for n in range(5)]
    # The pod dies in the wait and its teardown fails: the record stays.
    crashed = FakeProvider(
        gets=[RUNNING] * 8 + [EXITED], since_logs=[lines], deletes={"pod-1": 500}
    )
    assert served(crashed, FakeOpener(*[NOT_YET] * 9)) == 1
    capsys.readouterr()

    provider = FakeProvider()
    assert served(provider, FakeOpener(MODELS)) == 1

    assert "a pod is already recorded" in capsys.readouterr().err
    assert provider.named("create") == []
    assert kept_path().read_text(encoding="utf-8") == "".join(
        f"{line}\n" for line in lines
    )


@pytest.mark.spec("serve:wait:log-kept")
def test_a_pod_that_dies_before_ssh_removes_the_last_pods_log(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lines = [f"vllm {n}" for n in range(5)]
    crashed = FakeProvider(gets=[RUNNING] * 8 + [EXITED], since_logs=[lines])
    assert served(crashed, FakeOpener(*[NOT_YET] * 9)) == 1
    assert kept_path().exists()
    capsys.readouterr()

    # The next pod is created, then reads EXITED twice in `up`'s wait for SSH.
    provider = FakeProvider(gets=[EXITED])
    assert served(provider, FakeOpener(MODELS)) == 1

    assert "is EXITED" in capsys.readouterr().err
    assert len(provider.named("create")) == 1
    assert provider.named("delete") == [("pod-1",)]
    assert not kept_path().exists()


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


@pytest.mark.spec("serve:api:dead-pod-ends-the-hold")
def test_a_dead_pod_ends_the_hold(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # `up`'s poll, then the hold's: EXITED on two polls in a row. The second log
    # read comes back empty, as a stopped pod's does.
    provider = FakeProvider(
        gets=[RUNNING, EXITED], since_logs=[["vllm up", "vllm crashed"], []]
    )
    # The wait's answer, then the hold's first poll unanswered.
    opener = FakeOpener(MODELS, NOT_YET)

    assert served(provider, opener, api=True) == 1

    err = capsys.readouterr().err
    assert "refused: the pod stopped while serving" in err
    assert "has not answered" not in err
    assert len(opener.requests) == 2
    assert provider.named("delete") == [("pod-1",)]
    assert said_pod(err) == ["vllm up", "vllm crashed"]
    assert f"the pod's log is kept at {kept_path()}" in err


@pytest.mark.spec("serve:api:prints-the-endpoint")
def test_a_quiet_hold_prints_the_kept_log(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # vLLM crashed in the hold; boot's grace keeps the pod RUNNING past the quiet bound.
    provider = FakeProvider(since_logs=[["vllm up", "vllm out of memory"]])
    opener = FakeOpener(MODELS, MODELS, NOT_YET, NOT_YET)

    assert served(provider, opener, api=True) == 1

    err = capsys.readouterr().err
    assert "refused: the model has not answered for 60s" in err
    assert said_pod(err) == ["vllm up", "vllm out of memory"]
    assert f"the pod's log is kept at {kept_path()}" in err
    assert provider.named("delete") == [("pod-1",)]


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


@pytest.mark.spec("serve:volume:window-mounted")
def test_serve_mounts_the_rows_window_volume(home: Path) -> None:
    provider = FakeProvider(
        volume_creates=["v3"], volumes={"v3": VolumeInfo("EU-RO-1", 40)}
    )

    assert session.volume_up("qwen3-4b", 3600, yes=True, provider=provider) == 0
    assert served(provider, FakeOpener(MODELS), ceiling_s=1800) == 0

    row = table.load().models["qwen3-4b"]
    [(name, size_gb, _)] = provider.named("create_volume")
    assert (name, size_gb) == ("gpunit-serve-qwen3-4b", row.disk_gb)
    spec = created_spec(provider)
    assert spec.volume == "v3"
    # The spec reaches RunPod's create: the volume's data centre, mount and path.
    opener = FakeOpener((200, fixture("volume.json")), (201, b'{"id": "p"}'))
    runpod = RunPod({"RUNPOD_API_KEY": "rpa_test"}, opener=opener)
    runpod.create(spec, "NVIDIA A40", "key", spec.ceiling_s, nonce="n")
    body = opener.sent()
    assert body["dataCenterIds"] == ["EU-RO-1"]
    env = body["env"]
    assert isinstance(env, dict)
    assert env["GPUNIT_VOLUME_PATH"] == "/runpod-volume"


@pytest.mark.spec("volume:ceiling:serve-sweeps-first")
def test_serve_sweeps_an_overdue_volume_before_the_price(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    place = session.home("qwen3-4b")
    place.mkdir(parents=True)
    open_window(place, -60, "v3")
    provider = FakeProvider()

    assert served(provider, FakeOpener(MODELS), yes=False) == 1
    assert provider.named("delete_volume") == [("v3",)]
    assert provider.named("gpu") == []
    assert State(place).window() is None
    assert "run gpunit volume up" in capsys.readouterr().err


@pytest.mark.spec("serve:volume:never-created")
def test_serve_never_makes_a_volume(home: Path) -> None:
    provider = FakeProvider()

    assert served(provider, FakeOpener(MODELS)) == 0
    assert provider.named("create_volume") == []
    spec = created_spec(provider)
    assert (spec.volume, spec.volume_gb) == (None, None)


@pytest.mark.spec("volume:down:deletes")
def test_volume_down_serve_deletes_the_rows_volume(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = FakeProvider(volume_creates=["v3"])
    assert session.volume_up("qwen3-4b", 3600, yes=True, provider=provider) == 0

    assert gpunit(["volume", "down", "--serve", "qwen3-4b"], provider=provider) == 0
    assert provider.named("delete_volume") == [("v3",)]
    # No pending mark: nothing is swept by name.
    assert provider.named("volumes") == []
    assert State(session.home("qwen3-4b")).window() is None
    assert "volume v3 deleted" in capsys.readouterr().err
