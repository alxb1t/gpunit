import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from gpunit.spec import DIGEST
from tests.helpers import install_stubs

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
    # boot.py's stop goes over urllib: the image needs TLS roots, not curl.
    assert "ca-certificates" in install.split()
    assert "curl" not in install.split()
    assert 'ENTRYPOINT ["python3", "/opt/gpunit/boot.py", "--"]' in lines
    assert "COPY boot/boot.py /opt/gpunit/boot.py" in lines
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


# Prints what vLLM would start with, in place of vLLM.
VLLM = """#!/bin/sh
echo "HF_HOME=${HF_HOME:-unset}"
echo "args: $*"
"""


LAUNCH = ROOT / "serve" / "launch.py"


def command() -> list[str]:
    """Return the Dockerfile's CMD, the exec form's array."""
    [cmd] = [
        line
        for line in instructions(DOCKERFILE.read_text(encoding="utf-8"))
        if line.startswith("CMD ")
    ]
    return json.loads(cmd[len("CMD ") :])


def started(bin_dir: Path, volume: str | None) -> subprocess.CompletedProcess[str]:
    """Run the CMD's script from this tree under the test's Python, vLLM stubbed."""
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "SERVE_REPO": "Qwen/Qwen3-4B",
        "SERVE_REVISION": "abc123",
        "SERVE_NAME": "qwen3-4b",
        "SERVE_ARGS": "--max-model-len 16384",
    }
    if volume is not None:
        env["GPUNIT_VOLUME_PATH"] = volume
    return subprocess.run(
        [sys.executable, str(LAUNCH)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


ARGS = (
    "args: serve Qwen/Qwen3-4B --revision abc123 --served-model-name qwen3-4b"
    " --host 127.0.0.1 --port 8000 --max-model-len 16384"
)


@pytest.mark.spec("serve:volume:weights-on-the-volume")
def test_the_cmd_is_launch_py() -> None:
    lines = instructions(DOCKERFILE.read_text(encoding="utf-8"))

    assert command() == ["python3", "/opt/gpunit/launch.py"]
    assert "COPY serve/launch.py /opt/gpunit/launch.py" in lines


@pytest.mark.spec("serve:volume:weights-on-the-volume")
@pytest.mark.parametrize(
    ("volume", "home"),
    [
        ("/runpod-volume", "/runpod-volume/huggingface"),
        (None, "unset"),
        ("", "unset"),
    ],
    ids=["volume", "no-volume", "twin-empty"],
)
def test_vllm_starts_with_the_weights_on_the_volume(
    volume: str | None, home: str, tmp_path: Path
) -> None:
    bin_dir = install_stubs(tmp_path / "bin", {"vllm": VLLM})

    done = started(bin_dir, volume)

    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines() == [f"HF_HOME={home}", ARGS]
