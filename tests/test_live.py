import http.client
import subprocess
from collections.abc import Callable, Iterator
from typing import cast

import pytest

from live import dead, serve, volume
from live.window import report, run, window

UP = ["gpunit", "volume", "up"]
DOWN = ["gpunit", "volume", "down"]
STAMP = "2026-10-17T09:00:00Z"


@pytest.mark.spec("session:volume:window-mounted")
@pytest.mark.parametrize(
    ("wrote", "read", "failures"),
    [
        (STAMP, STAMP, []),
        ("", "", ["the first pod wrote nothing"]),
        (STAMP, "", [f"the second pod read '', not '{STAMP}'"]),
    ],
    ids=["carried", "twin-nothing-written", "twin-nothing-read"],
)
def test_the_volume_check(wrote: str, read: str, failures: list[str]) -> None:
    assert volume.check(wrote, read) == failures


REFUSED = [
    f"{STAMP} pod pod-abc: EXITED",
    f"{STAMP} pod pod-abc deleted",
    f"{STAMP} refused: the pod exited twice in a row: EXITED",
]


@pytest.mark.spec("session:wait:dead-pod-tears-down")
@pytest.mark.parametrize(
    ("code", "lines", "failures"),
    [
        (1, REFUSED, []),
        (0, REFUSED, ["up exited 0, not 1"]),
        (1, REFUSED[:-1], ["no line says why up refused"]),
    ],
    ids=["refused", "twin-exit-0", "twin-no-reason"],
)
def test_the_dead_check(code: int, lines: list[str], failures: list[str]) -> None:
    assert dead.check(code, lines) == failures


@pytest.mark.spec("session:wait:dead-pod-tears-down")
def test_the_reason_is_the_last_refusal() -> None:
    lines = [
        f"{STAMP} refused: first",
        f"{STAMP} pod: echoed",
        f"{STAMP} refused: last",
    ]

    assert dead.reason(lines) == "last"
    assert dead.reason([]) == ""


@pytest.mark.spec("serve:api:prints-the-endpoint")
def test_the_endpoint_is_read_once_both_lines_are_out() -> None:
    base = "OPENAI_BASE_URL=http://127.0.0.1:8000/v1"
    key = "OPENAI_API_KEY=" + "k" * 43

    assert serve.endpoint([base]) is None
    assert serve.endpoint([base, key]) == ("http://127.0.0.1:8000/v1", "k" * 43)
    assert serve.endpoint([key]) is None


class Runs:
    """`run`, faked: answers each argv from `codes` and logs the order."""

    def __init__(self, codes: dict[str, int]) -> None:
        self.codes = codes
        self.order: list[str] = []

    def __call__(self, argv: list[str]) -> int:
        step = argv[-1]
        self.order.append(step)
        return self.codes.get(step, 0)


def body(code: int, order: list[str]) -> int:
    order.append("body")
    return code


@pytest.mark.spec("volume:down:deletes")
@pytest.mark.parametrize(
    ("codes", "body_code", "result", "order"),
    [
        ({}, 0, 0, ["up", "body", "down"]),
        ({}, 3, 3, ["up", "body", "down"]),
        ({"down": 1}, 0, 1, ["up", "body", "down"]),
        ({"up": 2}, 0, 2, ["up", "down"]),
    ],
    ids=["proved", "body-fails", "down-fails", "up-fails"],
)
def test_the_window_deletes_the_volume_however_the_run_ends(
    codes: dict[str, int], body_code: int, result: int, order: list[str]
) -> None:
    runs = Runs(codes)

    code = window(UP, DOWN, lambda: body(body_code, runs.order), runs)

    assert code == result
    assert runs.order == order


@pytest.mark.spec("volume:down:deletes")
def test_a_body_that_raises_still_deletes_the_volume() -> None:
    runs = Runs({})

    def raises() -> int:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        window(UP, DOWN, raises, runs)

    assert runs.order == ["up", "down"]


@pytest.mark.spec("session:volume:window-mounted")
def test_a_failure_fails_the_run(capsys: pytest.CaptureFixture[str]) -> None:
    assert report([]) == 0
    assert report(["the first pod wrote nothing"]) == 1
    assert "check failed: the first pod wrote nothing" in capsys.readouterr().err


class Child:
    """A gpunit child, faked: `interrupts` Ctrl-Cs land in its waits before it exits.

    Its first Ctrl-C lands while it runs, in `communicate`; `calls` logs what was asked.
    """

    def __init__(self, argv: list[str], interrupts: int) -> None:
        self.argv = argv
        self.calls: list[str] = []
        self.interrupts = interrupts
        self.returncode: int | None = None
        self.stdout: Iterator[str] = iter(
            ["OPENAI_BASE_URL=http://127.0.0.1:8000/v1\n", "OPENAI_API_KEY=k\n"]
        )

    def __enter__(self) -> "Child":
        return self

    def __exit__(self, *exc: object) -> None:
        self.calls.append("exit")

    def communicate(
        self, input: str | None = None, timeout: float | None = None
    ) -> tuple[str, str]:
        self.calls.append("communicate")
        raise KeyboardInterrupt

    def wait(self, timeout: float | None = None) -> int:
        self.calls.append("wait")
        if self.interrupts:
            self.interrupts -= 1
            raise KeyboardInterrupt
        self.returncode = 0
        return 0

    def poll(self) -> int | None:
        return self.returncode

    def kill(self) -> None:
        self.calls.append("kill")
        self.returncode = -9

    def terminate(self) -> None:
        self.calls.append("terminate")


class Children:
    """`subprocess.Popen`, faked: its nth child takes `interrupts[n]` Ctrl-Cs."""

    def __init__(self, *interrupts: int) -> None:
        self.interrupts = list(interrupts)
        self.started: list[Child] = []

    def __call__(self, argv: list[str], **kwargs: object) -> Child:
        child = Child(argv, self.interrupts[len(self.started)])
        self.started.append(child)
        return child


def _chat(monkeypatch: pytest.MonkeyPatch) -> object:
    """Reach `body`'s chat session: the endpoint proved, the window extended."""
    monkeypatch.setattr(serve, "_proved", lambda base, key, model: True)
    monkeypatch.setattr(serve, "run", lambda argv: 0)
    return serve.body("qwen3-4b")


def _dead_up(monkeypatch: pytest.MonkeyPatch) -> object:
    """Reach `dead.main`'s read of `up`'s lines; the Ctrl-C lands in it."""
    children = cast(Children, subprocess.Popen)

    def cut(lines: Iterator[str]) -> Iterator[str]:
        yield from lines
        raise KeyboardInterrupt

    def popen(argv: list[str], **kwargs: object) -> Child:
        child = children(argv, **kwargs)
        child.stdout = cut(child.stdout)
        return child

    monkeypatch.setattr(subprocess, "Popen", popen)
    monkeypatch.setattr(dead, "price", lambda spec: 0)
    return dead.main()


@pytest.mark.spec("volume:down:deletes")
@pytest.mark.parametrize(
    ("start", "interrupts"),
    [
        (lambda monkeypatch: run(UP), (2,)),
        (lambda monkeypatch: volume._said("true"), (2,)),
        (_chat, (0, 2)),
        (_dead_up, (1, 0)),
    ],
    ids=["window-run", "volume-said", "serve-chat", "dead-up"],
)
def test_ctrl_c_waits_for_gpunits_teardown(
    monkeypatch: pytest.MonkeyPatch,
    start: Callable[[pytest.MonkeyPatch], object],
    interrupts: tuple[int, ...],
) -> None:
    children = Children(*interrupts)
    monkeypatch.setattr(subprocess, "Popen", children)

    with pytest.raises(KeyboardInterrupt):
        start(monkeypatch)

    child = children.started[-1]
    assert "kill" not in child.calls
    assert child.returncode == 0


@pytest.mark.spec("session:wait:dead-pod-tears-down")
def test_a_ctrl_c_in_dead_still_deletes_ups_pod(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # `gpunit up` has no SIGINT teardown. The Ctrl-C lands in the read, then the wait.
    children = Children(1, 0)
    monkeypatch.setattr(subprocess, "Popen", children)

    with pytest.raises(KeyboardInterrupt):
        _dead_up(monkeypatch)

    up, down = children.started
    assert up.argv[-3:] == ["up", "--spec", dead.SPEC]
    assert "kill" not in up.calls
    assert down.argv[-3:] == ["down", "--spec", dead.SPEC]


@pytest.mark.spec("serve:api:prints-the-endpoint")
def test_a_failed_proof_still_ends_the_api_hold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    children = Children(0)
    monkeypatch.setattr(subprocess, "Popen", children)

    def cut_short(base: str, key: str, model: str) -> bool:
        raise http.client.IncompleteRead(b"")

    monkeypatch.setattr(serve, "_proved", cut_short)

    with pytest.raises(http.client.IncompleteRead):
        serve.body("qwen3-4b")

    [served] = children.started
    assert served.calls == ["terminate", "wait"]
    assert served.returncode == 0
