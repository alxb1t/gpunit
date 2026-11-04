"""Start vLLM on the serve image's row, quiet, the weights on the window volume, if set.

e.g. GPUNIT_VOLUME_PATH=/runpod-volume → HF_HOME=/runpod-volume/huggingface, then
`vllm serve <SERVE_REPO> … --no-enable-log-requests`. Why Python, not `sh -c`:
decision D40.

    CMD ["python3", "/opt/gpunit/launch.py"]
"""

import os
import re
import sys

# `gpunit/serve/table.py`'s flag rule, held again: the image holds this file alone.
# Decision D40.
_FLAG = re.compile(r"--[a-z0-9-]+")
_LAUNCHERS = frozenset(
    {
        "--revision",
        "--code-revision",
        "--tokenizer-revision",
        "--served-model-name",
        "--host",
        "--port",
        "--api-key",
    }
)
_LOGGING = frozenset(
    {
        "--enable-log-requests",
        "--enable-log-outputs",
        "--log-level",
        "--logging-config",
    }
)


def _refused(args: list[str]) -> str | None:
    """Return the first flag in `args` the model table refuses, or None."""
    for arg in args:
        if not arg.startswith("-"):
            continue
        flag = arg.split("=", 1)[0].replace("_", "-")
        if (
            not _FLAG.fullmatch(flag)
            or flag == "--config"
            or any(name.startswith(flag) for name in _LAUNCHERS | _LOGGING)
        ):
            return flag
    return None


def main() -> None:
    """Refuse a row the model table refuses, else replace this process with vLLM."""
    # split() undoes table.py's join, without a shell's globbing.
    args = os.environ.get("SERVE_ARGS", "").split()
    flag = _refused(args)
    if flag is not None:
        print(f"launch: SERVE_ARGS holds {flag}; refused", file=sys.stderr)
        sys.exit(1)
    volume = os.environ.get("GPUNIT_VOLUME_PATH")
    if volume:
        os.environ["HF_HOME"] = f"{volume}/huggingface"
    # Whatever the pod's environment holds: every row passes here (decision D40).
    os.environ.update(
        DO_NOT_TRACK="1", HF_HUB_DISABLE_TELEMETRY="1", VLLM_NO_USAGE_STATS="1"
    )
    # Loopback only: the laptop reaches it over the session's tunnel. vLLM reads
    # VLLM_API_KEY itself.
    os.execvp(
        "vllm",
        [
            "vllm",
            "serve",
            os.environ["SERVE_REPO"],
            "--revision",
            os.environ["SERVE_REVISION"],
            "--served-model-name",
            os.environ["SERVE_NAME"],
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            *args,
            # Last: argparse keeps the last of a flag, so no row outvotes it.
            "--no-enable-log-requests",
        ],
    )


if __name__ == "__main__":
    main()
