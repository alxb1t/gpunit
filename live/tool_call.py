"""Prove a served model answers a tool request with a tool call (0008 design D3).

e.g. `OPENAI_API_KEY=<key> python live/tool_call.py http://127.0.0.1:8000/v1 qwen3-4b`
prints `tool call: get_weather {"city": "Paris"}` and exits 0; anything else exits 1.
"""

import json
import os
import sys
import urllib.error
import urllib.request

TOOL = "get_weather"
USAGE = "usage: OPENAI_API_KEY=<key> tool_call.py <base-url> <model>"
# The endpoint is gpunit's local tunnel: a proxy would only stand in its way.
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(model: str) -> dict[str, object]:
    """Return a chat request of one user message and one function."""
    return {
        "model": model,
        "messages": [
            {"role": "user", "content": "What is the weather in Paris? Use the tool."}
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": TOOL,
                    "description": "Get the weather in a city",
                    "parameters": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                        "required": ["city"],
                    },
                },
            }
        ],
        "tool_choice": "auto",
        "chat_template_kwargs": {"enable_thinking": False},
    }


def verdict(answer: dict) -> str:
    """Return the call's line, or raise `ValueError` naming what the answer held."""
    choice = answer["choices"][0]
    calls = choice["message"].get("tool_calls") or []
    reason = choice.get("finish_reason")
    if reason != "tool_calls" or not calls:
        content = choice["message"].get("content")
        raise ValueError(
            f"the answer held no tool call: finish_reason {reason!r},"
            f" content {content!r}"
        )
    function = calls[0]["function"]
    if function["name"] != TOOL:
        raise ValueError(f"the tool call named {function['name']!r}, not {TOOL!r}")
    try:
        json.loads(function["arguments"])
    except json.JSONDecodeError:
        raise ValueError(
            f"the tool call's arguments are not JSON: {function['arguments']!r}"
        ) from None
    return f"tool call: {TOOL} {function['arguments']}"


def main(argv: list[str]) -> int:
    """Return 0 and print the call, or return 1 and say what came back."""
    # Never echo argv: a key passed there must not reach a log.
    if len(argv) != 2:
        print(USAGE, file=sys.stderr)
        return 1
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print(f"OPENAI_API_KEY is not set\n{USAGE}", file=sys.stderr)
        return 1
    base, model = argv
    sent = urllib.request.Request(
        f"{base.rstrip('/')}/chat/completions",
        data=json.dumps(request(model)).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with OPENER.open(sent, timeout=300) as response:
            line = verdict(json.load(response))
    except urllib.error.HTTPError as error:
        print(f"the server answered {error.code} {error.reason}", file=sys.stderr)
        return 1
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    except (OSError, KeyError, IndexError, TypeError) as error:
        print(f"no tool call: {error!r}", file=sys.stderr)
        return 1
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
