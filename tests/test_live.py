import pytest

from live import dead, serve, volume
from live.window import report, window

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
