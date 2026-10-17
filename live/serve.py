"""Prove a served model answers over its endpoint, then in a chat (0005 design D9).

e.g. `RUNPOD_API_KEY=<key> python live/serve.py qwen3-4b` serves the row with `--api`
for one chat request and one tool call (0008 design D4), then chats one prompt, inside
the row's window volume (0010 design D10): the endpoint downloads the weights into it,
the chat's new pod loads them from it.
"""

import json
import os
import subprocess
import sys
import urllib.request

from live.tool_call import OPENER
from live.window import LIVE, gpunit, run, serve_volume_up, serve_window

CEILING = "30m"
PROMPT = "What is 2 + 2? Answer with the number.\n"


def endpoint(lines: list[str]) -> tuple[str, str] | None:
    """Return the base URL and the key `serve --api` printed, or None before both.

    e.g. ["OPENAI_BASE_URL=http://127.0.0.1:8000/v1", "OPENAI_API_KEY=k"]
        → ("http://127.0.0.1:8000/v1", "k")
    """
    said = dict(line.split("=", 1) for line in lines if "=" in line)
    base, key = said.get("OPENAI_BASE_URL"), said.get("OPENAI_API_KEY")
    return (base, key) if base and key else None


def chat(base: str, key: str, model: str) -> str:
    """Return the endpoint's answer to one prompt; raise `OSError` when it fails."""
    sent = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(
            {
                "model": model,
                "messages": [{"role": "user", "content": "Say hello in one word."}],
                "chat_template_kwargs": {"enable_thinking": False},
            }
        ).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with OPENER.open(sent, timeout=300) as response:
        return response.read().decode()


def _proved(base: str, key: str, model: str) -> bool:
    """Send the chat request and the tool call; return True when both answered."""
    try:
        print(chat(base, key, model), flush=True)
    except OSError as error:
        print(f"the chat request failed: {error}", file=sys.stderr)
        return False
    tool_call = [sys.executable, str(LIVE / "tool_call.py"), base, model]
    done = subprocess.run(tool_call, env={**os.environ, "OPENAI_API_KEY": key})
    return done.returncode == 0


def body(model: str) -> int:
    """Hold the endpoint for the requests, then chat one prompt in a new session."""
    # stdout is piped: the key is read here and never reaches the terminal.
    served = subprocess.Popen(
        gpunit("serve", model, "--ceiling", CEILING, "--yes", "--api"),
        stdout=subprocess.PIPE,
        text=True,
    )
    assert served.stdout is not None
    lines: list[str] = []
    found = None
    for line in served.stdout:
        lines.append(line.rstrip("\n"))
        if found := endpoint(lines):
            break
    if found is None:
        served.wait()
        return 1
    proved = _proved(*found, model)
    served.terminate()
    served.wait()
    if not proved:
        return 1
    # The chat extends the window first: its 30m and 1200s wait must fit inside it.
    code = run(serve_volume_up(model))
    if code:
        return code
    chatted = subprocess.run(
        gpunit("serve", model, "--ceiling", CEILING, "--yes"), input=PROMPT, text=True
    )
    return chatted.returncode


def main(argv: list[str]) -> int:
    """Prove the row `argv` names inside its window volume; return 0 when it answers."""
    if len(argv) != 1:
        print("usage: python live/serve.py <model>", file=sys.stderr)
        return 1
    [model] = argv
    return serve_window(model, lambda: body(model))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
