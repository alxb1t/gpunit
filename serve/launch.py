"""Start vLLM on the serve image's row, the weights on the window volume, if set.

e.g. GPUNIT_VOLUME_PATH=/runpod-volume → HF_HOME=/runpod-volume/huggingface, then
`vllm serve <SERVE_REPO> …`. Why Python, not `sh -c`: 0012 design D9.

    CMD ["python3", "/opt/gpunit/launch.py"]
"""

import os


def main() -> None:
    """Set HF_HOME on the volume, if one is set, and replace this process with vLLM."""
    volume = os.environ.get("GPUNIT_VOLUME_PATH")
    if volume:
        os.environ["HF_HOME"] = f"{volume}/huggingface"
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
        ],
    )


if __name__ == "__main__":
    main()
