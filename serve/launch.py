"""Start vLLM on the serve image's row, quiet, the weights on the window volume, if set.

e.g. GPUNIT_VOLUME_PATH=/runpod-volume → HF_HOME=/runpod-volume/huggingface, then
`vllm serve <SERVE_REPO> … --no-enable-log-requests`. Why Python, not `sh -c`:
decision D40.

    CMD ["python3", "/opt/gpunit/launch.py"]
"""

import os


def main() -> None:
    """Set HF_HOME on the volume, if one is set, and replace this process with vLLM."""
    volume = os.environ.get("GPUNIT_VOLUME_PATH")
    if volume:
        os.environ["HF_HOME"] = f"{volume}/huggingface"
    # Whatever the pod's environment holds: every row passes here (decision D40).
    os.environ.update(
        DO_NOT_TRACK="1", HF_HUB_DISABLE_TELEMETRY="1", VLLM_NO_USAGE_STATS="1"
    )
    # Loopback only: the laptop reaches it over the session's tunnel. vLLM reads
    # VLLM_API_KEY itself. split() undoes table.py's join, without a shell's globbing.
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
            *os.environ.get("SERVE_ARGS", "").split(),
            # Last: argparse keeps the last of a flag, so no row outvotes it.
            "--no-enable-log-requests",
        ],
    )


if __name__ == "__main__":
    main()
