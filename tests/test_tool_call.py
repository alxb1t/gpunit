import json
import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

CHECK = Path(__file__).parent.parent / "live" / "tool_call.py"
KEY = "k" * 43


def answer(finish_reason: str, calls: list[dict[str, object]] | None = None) -> dict:
    message: dict[str, object] = {"role": "assistant", "content": None}
    if calls is None:
        message["content"] = "It is sunny in Paris."
    else:
        message["tool_calls"] = calls
    return {"choices": [{"finish_reason": finish_reason, "message": message}]}


def weather(arguments: str) -> dict[str, object]:
    return {
        "id": "call-1",
        "type": "function",
        "function": {"name": "get_weather", "arguments": arguments},
    }


class ModelServer(ThreadingHTTPServer):
    """Answer each chat request with `answer`, and keep what was asked."""

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), Answering)
        self.answer: dict = answer("tool_calls", [weather('{"city": "Paris"}')])
        self.requests: list[tuple[str, str | None, dict[str, object]]] = []

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}/v1"


class Answering(BaseHTTPRequestHandler):
    server: ModelServer

    def do_POST(self) -> None:
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))
        self.server.requests.append((self.path, self.headers["Authorization"], body))
        data = json.dumps(self.server.answer).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture
def model() -> Iterator[ModelServer]:
    server = ModelServer()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()


def check(*argv: str, key: str | None = KEY) -> subprocess.CompletedProcess[str]:
    env = {
        name: value for name, value in os.environ.items() if name != "OPENAI_API_KEY"
    }
    if key is not None:
        env["OPENAI_API_KEY"] = key
    return subprocess.run(
        [sys.executable, str(CHECK), *argv],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


@pytest.mark.spec("serve:tools:call-passes")
def test_a_tool_call_passes(model: ModelServer) -> None:
    done = check(model.base_url, "qwen3.8-27b")

    assert done.returncode == 0, done.stderr
    assert done.stdout == 'tool call: get_weather {"city": "Paris"}\n'
    path, _, body = model.requests[0]
    assert path == "/v1/chat/completions"
    assert body["model"] == "qwen3.8-27b"
    assert body["tool_choice"] == "auto"
    assert body["chat_template_kwargs"] == {"enable_thinking": False}
    tools = body["tools"]
    assert isinstance(tools, list)
    [tool] = tools
    assert tool["function"]["name"] == "get_weather"


@pytest.mark.spec("serve:tools:plain-text-fails")
@pytest.mark.parametrize(
    "reply",
    [answer("stop"), answer("tool_calls", [])],
    ids=["text", "no-calls"],
)
def test_plain_text_fails(model: ModelServer, reply: dict) -> None:
    model.answer = reply

    done = check(model.base_url, "qwen3.8-27b")

    assert done.returncode == 1
    assert "held no tool call" in done.stderr


@pytest.mark.spec("serve:tools:bad-arguments-fail")
@pytest.mark.parametrize(
    ("call", "said"),
    [
        (weather("{city: Paris"), "arguments are not JSON"),
        (
            {"type": "function", "function": {"name": "get_time", "arguments": "{}"}},
            "named 'get_time'",
        ),
    ],
    ids=["not-json", "other-function"],
)
def test_unparseable_arguments_fail(
    model: ModelServer, call: dict[str, object], said: str
) -> None:
    model.answer = answer("tool_calls", [call])

    done = check(model.base_url, "qwen3.8-27b")

    assert done.returncode == 1
    assert said in done.stderr


@pytest.mark.spec("serve:tools:key-from-the-environment")
def test_the_key_is_sent_from_the_environment(model: ModelServer) -> None:
    assert check(model.base_url, "qwen3.8-27b").returncode == 0

    [(_, authorization, _)] = model.requests
    assert authorization == f"Bearer {KEY}"


@pytest.mark.spec("serve:tools:key-from-the-environment")
@pytest.mark.parametrize(
    "extra", [["--key", KEY], []], ids=["key-on-argv", "twin-none"]
)
def test_a_key_on_the_command_line_is_refused(
    model: ModelServer, extra: list[str]
) -> None:
    done = check(model.base_url, "qwen3.8-27b", *extra)

    assert done.returncode == (1 if extra else 0)
    assert ("usage" in done.stderr) is bool(extra)
    assert KEY not in done.stderr + done.stdout
    assert len(model.requests) == (0 if extra else 1)


@pytest.mark.spec("serve:tools:key-from-the-environment")
@pytest.mark.parametrize("key", [None, KEY], ids=["unset", "twin-set"])
def test_no_key_in_the_environment_sends_nothing(
    model: ModelServer, key: str | None
) -> None:
    done = check(model.base_url, "qwen3.8-27b", key=key)

    assert done.returncode == (1 if key is None else 0)
    assert len(model.requests) == (0 if key is None else 1)
