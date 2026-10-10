import json
import threading
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from gpunit.serve import chat

KEY = "k" * 43


class ModelServer(ThreadingHTTPServer):
    """Stream `parts` as SSE, each only once the client has written the one before."""

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), Streaming)
        self.parts = ["Hel", "lo"]
        self.requests: list[tuple[str, str | None, dict[str, object]]] = []
        self.written = threading.Semaphore(0)
        self.buffered = False
        self.patience = 5.0

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}/v1"


class Streaming(BaseHTTPRequestHandler):
    server: ModelServer

    def do_POST(self) -> None:
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))
        self.server.requests.append((self.path, self.headers["Authorization"], body))
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        self.wfile.write(b'data: {"choices": [{"delta": {"role": "assistant"}}]}\n\n')
        for part in self.server.parts:
            chunk = {"choices": [{"delta": {"content": part}}]}
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
            self.wfile.flush()
            # A client that waits for the whole answer never writes this part.
            if not self.server.written.acquire(timeout=self.server.patience):
                self.server.buffered = True
        self.wfile.write(b"data: [DONE]\n\n")

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


def lines(*said: str) -> Iterator[str]:
    yield from said
    raise EOFError


def reader(*said: str) -> Callable[[str], str]:
    script = lines(*said)
    return lambda prompt: next(script)


@pytest.mark.spec("serve:chat:streams")
@pytest.mark.parametrize("streamed", [True, False], ids=["streamed", "twin-buffered"])
def test_each_part_is_written_as_it_arrives_and_the_answer_is_kept(
    streamed: bool, model: ModelServer
) -> None:
    written: list[str] = []

    def write(text: str) -> None:
        written.append(text)
        if streamed and text in model.parts:
            model.written.release()

    if not streamed:
        # The twin: a client that never writes a part until the end is caught.
        model.patience = 0.1
    chat.run(model.base_url, KEY, "qwen3-4b", False, reader("hi", "again"), write)

    assert model.buffered is not streamed
    assert written == ["Hel", "lo", "\n", "Hel", "lo", "\n", "\n"]
    [first, second] = model.requests
    assert first[0] == "/v1/chat/completions"
    assert first[1] == f"Bearer {KEY}"
    assert first[2]["messages"] == [{"role": "user", "content": "hi"}]
    assert second[2]["messages"] == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "Hello"},
        {"role": "user", "content": "again"},
    ]


@pytest.mark.spec("serve:chat:thinking-off")
@pytest.mark.parametrize("think", [False, True], ids=["default", "twin-think"])
def test_thinking_is_off_unless_asked_for(think: bool, model: ModelServer) -> None:
    def write(text: str) -> None:
        if text in model.parts:
            model.written.release()

    chat.run(model.base_url, KEY, "qwen3-4b", think, reader("hi"), write)

    [(_, _, body)] = model.requests
    assert body["model"] == "qwen3-4b"
    assert body["stream"] is True
    assert body["chat_template_kwargs"] == {"enable_thinking": think}


@pytest.mark.spec("serve:chat:eof-ends")
@pytest.mark.parametrize("said", [("/exit", "never read"), ()], ids=["exit", "eof"])
def test_exit_or_the_end_of_input_ends_the_chat(
    said: tuple[str, ...], model: ModelServer
) -> None:
    read = reader(*said)
    asked: list[str] = []

    def counted(prompt: str) -> str:
        asked.append(prompt)
        return read(prompt)

    chat.run(model.base_url, KEY, "qwen3-4b", False, counted, lambda text: None)

    assert asked == ["> "]
    assert model.requests == []
