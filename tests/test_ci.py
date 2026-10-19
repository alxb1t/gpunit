import re
from pathlib import Path

import pytest

from tests.helpers import triggers

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
GATE = WORKFLOWS / "gate.yml"


def openspec_version() -> str:
    """Return the OpenSpec CLI version `CLAUDE.md` records, e.g. "1.11.0"."""
    found = re.search(
        r"@fission-ai/openspec@([\w.-]+)",
        (ROOT / "CLAUDE.md").read_text(encoding="utf-8"),
    )
    assert found is not None
    return found[1]


def unpinned(text: str) -> list[str]:
    """Return each action a workflow names by anything but a 40-hex commit."""
    uses = re.findall(r"uses: (\S+)", text)
    return [
        action for action in uses if not re.fullmatch(r"[\w./-]+@[0-9a-f]{40}", action)
    ]


@pytest.mark.spec("architecture:ci:runs-the-gate")
def test_the_gate_workflow_runs_the_gate() -> None:
    text = GATE.read_text(encoding="utf-8")

    assert triggers(text) == ["push", "pull_request"]
    assert re.search(r"^\s+- run: make gate$", text, re.MULTILINE)
    assert f"run: npm install -g @fission-ai/openspec@{openspec_version()}\n" in text


@pytest.mark.spec("architecture:ci:runs-the-gate")
def test_a_third_trigger_is_caught() -> None:
    # The twin: the check fails on the same file with a schedule trigger added.
    text = GATE.read_text(encoding="utf-8")

    assert triggers(text.replace("on:\n", "on:\n  schedule:\n", 1)) != [
        "push",
        "pull_request",
    ]


@pytest.mark.spec("architecture:ci:actions-pinned")
def test_every_workflow_pins_its_actions() -> None:
    workflows = sorted(WORKFLOWS.glob("*.yml"))

    assert GATE in workflows
    for workflow in workflows:
        text = workflow.read_text(encoding="utf-8")
        assert "uses: " in text, workflow.name
        assert unpinned(text) == [], workflow.name


@pytest.mark.spec("architecture:ci:actions-pinned")
def test_an_action_named_by_a_tag_is_caught() -> None:
    # The twin: the check fails on the gate workflow with its checkout named by tag.
    text = GATE.read_text(encoding="utf-8")

    assert unpinned(
        re.sub(r"actions/checkout@[0-9a-f]{40}", "actions/checkout@v7", text)
    ) == ["actions/checkout@v7"]
