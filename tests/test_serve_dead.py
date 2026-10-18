from pathlib import Path

import pytest

from gpunit.serve import table
from live import serve_dead
from live.serve_dead import MODEL, check

ROOT = Path(__file__).parent.parent

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


@pytest.mark.spec("serve:wait:dead-pod-ends-the-wait")
def test_the_proof_reads_the_bundled_table_alone(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # The operator's own healthy row of the proof's name, by both ways it is found.
    own = (ROOT / "live" / "models.toml").read_text(encoding="utf-8")
    own = own.replace("granite-4.0-micro", MODEL)
    named = tmp_path / "models.toml"
    named.write_text(own, encoding="utf-8")
    default = tmp_path / "config" / "gpunit" / "models.toml"
    default.parent.mkdir(parents=True)
    default.write_text(own, encoding="utf-8")
    monkeypatch.setenv("GPUNIT_MODELS", str(named))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    seen: list[tuple[str, str]] = []

    def window(model: str, body: object) -> int:
        # The patched `prove` and the `volume` children read this environment.
        seen.append((model, table.rows().models[model].source))
        return 0

    monkeypatch.setattr(serve_dead, "serve_window", window)

    assert serve_dead.main() == 0

    assert seen == [(MODEL, "bundled")]
