"""Chat with a served model in the terminal: each answer streamed as it is written."""

import http.client
import json
import sys
import urllib.request
from collections.abc import Callable

from gpunit import log

# Per read, not per answer: a long answer streams for as long as it takes.
READ_S = 300
EXIT = "/exit"


def run(
    base_url: str,
    key: str,
    model: str,
    think: bool,
    read: Callable[[str], str] | None = None,
    write: Callable[[str], None] | None = None,
    *,
    opener: urllib.request.OpenerDirector,
) -> None:
    """Chat until `/exit` or the end of input, the conversation kept in memory."""
    if read is None:
        try:
            # Gives `input` line editing and history where the platform has it.
            import readline  # noqa: F401
        except ImportError:
            pass
        read = input
    write = write or _stdout
    messages: list[dict[str, str]] = []
    while True:
        try:
            line = read("> ")
        except EOFError:
            write("\n")
            return
        if line.strip() == EXIT:
            return
        if not line.strip():
            continue
        turn = [*messages, {"role": "user", "content": line}]
        body = {
            "model": model,
            "messages": turn,
            "stream": True,
            "chat_template_kwargs": {"enable_thinking": think},
        }
        request = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
        )
        try:
            answer = _stream(opener, request, write)
        except (OSError, http.client.HTTPException, ValueError) as fault:
            # The turn is dropped, so the next one is sent as if it never was.
            write("\n")
            log.say(f"the model did not answer: {fault}")
            continue
        write("\n")
        messages = [*turn, {"role": "assistant", "content": answer}]


def _stream(
    opener: urllib.request.OpenerDirector,
    request: urllib.request.Request,
    write: Callable[[str], None],
) -> str:
    """Write each streamed part as it arrives; return the whole answer.

    e.g. b'data: {"choices": [{"delta": {"content": "Hi"}}]}' → "Hi"
    """
    parts = []
    with opener.open(request, timeout=READ_S) as answer:
        for raw in answer:
            line = raw.decode("utf-8").strip()
            if not line.startswith("data:"):
                continue
            data = line.removeprefix("data:").strip()
            if data == "[DONE]":
                break
            choices = json.loads(data).get("choices") or [{}]
            part = (choices[0].get("delta") or {}).get("content")
            if part:
                write(part)
                parts.append(part)
    return "".join(parts)


def _stdout(text: str) -> None:
    sys.stdout.write(text)
    sys.stdout.flush()
