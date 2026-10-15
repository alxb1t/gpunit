import pytest

from live.serve_dead import check

# What a run that proves the scenario prints, in the order gpunit says it.
PROVED = [
    "2026-10-14T10:00:00Z price: NVIDIA RTX A5000 $0.27/h",
    "2026-10-14T10:04:00Z loading: vllm: error: unrecognized arguments: --no-such-flag",
    "2026-10-14T10:04:40Z pod: vllm: error: unrecognized arguments: --no-such-flag",
    "2026-10-14T10:04:40Z pod: 2026-10-14T10:03:58Z the command exited 2",
    "2026-10-14T10:04:40Z the pod's log is kept at pod.log",
    "2026-10-14T10:04:40Z refused: the pod stopped while the model loaded",
    "2026-10-14T10:04:43Z pod pod-abc deleted",
]


def without(needle: str) -> list[str]:
    return [line for line in PROVED if needle not in line]


@pytest.mark.spec("serve:wait:dead-pod-ends-the-wait")
def test_a_run_that_proves_the_scenario_passes() -> None:
    assert check(PROVED, 1) == []


@pytest.mark.spec("serve:wait:dead-pod-ends-the-wait")
@pytest.mark.parametrize(
    ("lines", "code", "failure"),
    [
        (PROVED, 0, "the exit code is 0, not 1"),
        (without("refused:"), 1, "no line holds 'refused: the pod stopped"),
        (without(" pod: vllm"), 1, "no pod: line holds 'no-such-flag'"),
        (without("exited 2"), 1, "no pod: line holds 'the command exited 2'"),
        (without(" deleted"), 1, "no line says the pod was deleted"),
        (
            [*PROVED[:-1], "2026-10-14T10:05:00Z pod pod-abc deleted"],
            1,
            "the delete came 20s after the refusal",
        ),
    ],
    ids=["code", "no-refusal", "no-flag", "no-exit", "no-delete", "late-delete"],
)
def test_a_run_that_misses_a_part_fails_naming_it(
    lines: list[str], code: int, failure: str
) -> None:
    failures = check(lines, code)

    assert len(failures) == 1
    assert failures[0].startswith(failure)
