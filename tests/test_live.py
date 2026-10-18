import http.client
import signal
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import cast

import pytest

from gpunit.serve import table
from live import dead, serve, volume
from live.window import report, run, window

ROOT = Path(__file__).parent.parent
UP = ["gpunit", "volume", "up"]
DOWN = ["gpunit", "volume", "down"]
STAMP = "2026-10-17T09:00:00Z"


@pytest.fixture(autouse=True)
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run each test in a checkout of its own, whose `.gpunit/` records nothing."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


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
    ("code", "lines", "down", "failures"),
    [
        (1, REFUSED, 0, []),
        (0, REFUSED, 0, ["up exited 0, not 1"]),
        (1, REFUSED[:-1], 0, ["no line says why up refused"]),
        (1, REFUSED, 1, ["gpunit down exited 1: a pod may be left billing"]),
    ],
    ids=["refused", "twin-exit-0", "twin-no-reason", "twin-down-fails"],
)
def test_the_dead_check(
    code: int, lines: list[str], down: int, failures: list[str]
) -> None:
    assert dead.check(code, lines, down) == failures


class Ended:
    """`gpunit up`, faked: prints `lines`, then exits `code`."""

    def __init__(self, code: int, lines: list[str]) -> None:
        self.code = code
        self.stdout: Iterator[str] = iter(f"{line}\n" for line in lines)

    def wait(self) -> int:
        return self.code


LOST = [f"{STAMP} refused: the create's answer was lost; run gpunit down"]


@pytest.mark.spec("session:wait:dead-pod-tears-down")
@pytest.mark.parametrize(
    ("up_code", "lines", "down_code", "result"),
    [(1, REFUSED, 0, 0), (3, LOST, 0, 1), (1, REFUSED, 1, 1)],
    ids=["refused", "lost-create", "down-fails"],
)
def test_dead_deletes_ups_pod_however_up_ends(
    monkeypatch: pytest.MonkeyPatch,
    up_code: int,
    lines: list[str],
    down_code: int,
    result: int,
) -> None:
    # The dead image never starts boot.py: no ceiling stops a pod `up` left behind.
    order: list[str] = []

    def popen(argv: list[str], **kwargs: object) -> Ended:
        order.append(argv[-3])
        return Ended(up_code, lines)

    def run(argv: list[str]) -> int:
        order.append(argv[-3])
        return down_code if argv[-3] == "down" else 0

    monkeypatch.setattr(subprocess, "Popen", popen)
    monkeypatch.setattr(dead, "price", lambda spec: 0)
    monkeypatch.setattr(dead, "run", run)

    assert dead.main() == result

    assert order == ["up", "down", "status"]


@pytest.mark.spec("session:wait:dead-proof-spares-a-record")
@pytest.mark.parametrize("held", ["pod", "pending"])
def test_dead_leaves_a_recorded_pod_alone(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    checkout: Path,
    held: str,
) -> None:
    # Another session's record: `up` would refuse on it, and `down` delete its pod.
    record = checkout / ".gpunit" / held
    record.parent.mkdir()
    record.write_text("another session's\n")
    order: list[str] = []

    def popen(argv: list[str], **kwargs: object) -> Ended:
        order.append(argv[-3])
        return Ended(1, REFUSED)

    def run(argv: list[str]) -> int:
        order.append(argv[-3])
        return 0

    def price(spec: str) -> int:
        order.append("price")
        return 0

    monkeypatch.setattr(subprocess, "Popen", popen)
    monkeypatch.setattr(dead, "price", price)
    monkeypatch.setattr(dead, "run", run)

    assert dead.main() == 1

    assert order == []
    assert record.read_text() == "another session's\n"
    assert "gpunit down" in capsys.readouterr().err


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


@pytest.mark.spec("serve:rows:merged")
def test_the_live_user_file_joins_the_bundled_rows() -> None:
    path = ROOT / "live" / "models.toml"

    found = table.rows(path)
    bundled = table.load()

    assert found.models["granite-4.0-micro"].source == str(path)
    assert found.models["granite-4.0-micro"].image == bundled.image
    assert bundled.models.keys() < found.models.keys()
    assert found.replaced == ()


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


# A window whose body is sent the signal argv[1] names; each step prints its argv.
HUNG_UP = """\
import os
import sys

from live.window import window


def run(argv):
    print(argv[-1], flush=True)
    return 0


def body():
    os.kill(os.getpid(), int(sys.argv[1]))
    return 0


window(["up"], ["down"], body, run)
"""


@pytest.mark.spec("volume:down:deletes")
@pytest.mark.parametrize(
    "signum", [signal.SIGHUP, signal.SIGTERM], ids=["sighup", "sigterm"]
)
def test_a_hangup_still_deletes_the_volume(signum: signal.Signals) -> None:
    # A closed terminal sends SIGHUP; Python's default for it runs no `finally`.
    done = subprocess.run(
        [sys.executable, "-c", HUNG_UP, str(int(signum))],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=60,
    )

    assert done.stdout.splitlines() == ["up", "down"]
    assert "KeyboardInterrupt" in done.stderr


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
    """`subprocess.Popen`, faked: its nth child takes `interrupts[n]` Ctrl-Cs.

    `exited[n]` holds the codes of the children before the nth as it started, `None`
    for one still running.
    """

    def __init__(self, *interrupts: int) -> None:
        self.interrupts = list(interrupts)
        self.started: list[Child] = []
        self.exited: list[list[int | None]] = []

    def __call__(self, argv: list[str], **kwargs: object) -> Child:
        self.exited.append([child.returncode for child in self.started])
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

    # Every child: in `dead-up`, `up` as well as the `down` after it.
    for child in children.started:
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
    # `up` was waited to its exit before `down` started: it may still write its record.
    assert children.exited[1] == [0]


@pytest.mark.spec("session:wait:dead-pod-tears-down")
def test_a_hangup_in_dead_is_a_ctrl_c(monkeypatch: pytest.MonkeyPatch) -> None:
    hangups = (signal.SIGHUP, signal.SIGTERM)
    before = [signal.getsignal(signum) for signum in hangups]
    held: list[object] = []
    up = Ended(1, [])

    def lines() -> Iterator[str]:
        held.extend(signal.getsignal(signum) for signum in hangups)
        yield from (f"{line}\n" for line in REFUSED)

    up.stdout = lines()
    monkeypatch.setattr(subprocess, "Popen", lambda argv, **kwargs: up)
    monkeypatch.setattr(dead, "price", lambda spec: 0)
    monkeypatch.setattr(dead, "run", lambda argv: 0)

    assert dead.main() == 0

    # While `up` runs, a SIGHUP or SIGTERM takes the Ctrl-C's path to `gpunit down`.
    assert held == [signal.default_int_handler] * 2
    assert [signal.getsignal(signum) for signum in hangups] == before


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
