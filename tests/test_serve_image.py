import re
from pathlib import Path

import pytest

from gpunit.spec import DIGEST

ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = ROOT / "serve" / "Dockerfile"
WORKFLOW = ROOT / ".github" / "workflows" / "build-serve-image.yml"


def instructions(text: str) -> list[str]:
    """Return the Dockerfile's instructions, continuation lines joined."""
    joined = re.sub(r"\\\n", " ", text)
    return [line for line in joined.splitlines() if line and not line.startswith("#")]


def triggers(text: str) -> list[str]:
    """Return the workflow's trigger names: the keys one level under `on:`."""
    block = re.search(r"^on:\n((?:[ \t]+.*\n|\n)*)", text, re.MULTILINE)
    assert block is not None
    return re.findall(r"^  ([a-z_]+):", block[1], re.MULTILINE)


def pinned(text: str) -> bool:
    """Return whether every image the Dockerfile builds from is named by digest."""
    bases = [line.split()[1] for line in instructions(text) if line.startswith("FROM")]
    return bool(bases) and all(DIGEST.search(base) for base in bases)


@pytest.mark.spec("serve:image:pinned-inputs")
def test_the_image_is_built_from_pinned_inputs() -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")
    lines = instructions(text)

    assert pinned(text)
    [install] = [line for line in lines if "openssh-server" in line]
    assert "/etc/ssh/ssh_host_*" in install
    assert 'ENTRYPOINT ["/opt/gpunit/boot.sh", "--"]' in lines
    assert "COPY boot/boot.sh /opt/gpunit/boot.sh" in lines
    [env] = [line for line in lines if line.startswith("ENV")]
    for off in (
        "DO_NOT_TRACK=1",
        "HF_HUB_DISABLE_TELEMETRY=1",
        "VLLM_NO_USAGE_STATS=1",
    ):
        assert off in env


@pytest.mark.spec("serve:image:pinned-inputs")
def test_a_tagged_base_is_caught() -> None:
    # The twin: the check fails on the same file with its base named by tag.
    text = DOCKERFILE.read_text(encoding="utf-8")

    assert not pinned(re.sub(r"@sha256:[0-9a-f]{64}", "", text))


@pytest.mark.spec("serve:image:pinned-inputs")
def test_each_action_is_pinned_by_commit() -> None:
    uses = re.findall(r"uses: (\S+)", WORKFLOW.read_text(encoding="utf-8"))

    assert uses
    assert all(re.fullmatch(r"[\w./-]+@[0-9a-f]{40}", action) for action in uses)


@pytest.mark.spec("serve:image:only-a-request-builds")
def test_only_a_manual_request_builds_and_latest_is_refused() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert triggers(text) == ["workflow_dispatch"]
    assert re.search(r'if \[ "\$TAG" = "latest" \]; then\n\s+echo .*\n\s+exit 1', text)
    assert re.search(r"DIGEST: \$\{\{ steps\.build\.outputs\.digest \}\}", text)
    assert '>> "$GITHUB_STEP_SUMMARY"' in text


@pytest.mark.spec("serve:image:only-a-request-builds")
def test_a_second_trigger_is_caught() -> None:
    # The twin: the check fails on the same file with a push trigger added.
    text = WORKFLOW.read_text(encoding="utf-8")

    assert triggers(text.replace("on:\n", "on:\n  push:\n", 1)) != ["workflow_dispatch"]
