import http.client
import json
import threading
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from gpunit import log
from gpunit.serve import chat
from tests.fakes import FakeOpener

KEY = "k" * 43
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


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
    chat.run(
        model.base_url,
        KEY,
        "qwen3-4b",
        False,
        reader("hi", "again"),
        write,
        opener=OPENER,
    )

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

    chat.run(model.base_url, KEY, "qwen3-4b", think, reader("hi"), write, opener=OPENER)

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

    chat.run(
        model.base_url,
        KEY,
        "qwen3-4b",
        False,
        counted,
        lambda text: None,
        opener=OPENER,
    )

    assert asked == ["> "]
    assert model.requests == []


@pytest.mark.spec("serve:chat:stopped-server-ends")
def test_a_server_that_cannot_be_reached_ends_the_chat(
    capsys: pytest.CaptureFixture[str],
) -> None:
    asked: list[str] = []

    def read(prompt: str) -> str:
        asked.append(prompt)
        return "hi"

    refused = urllib.error.URLError(ConnectionRefusedError(61, "Connection refused"))
    with pytest.raises(log.Refusal):
        chat.run(
            "http://127.0.0.1:1/v1",
            KEY,
            "qwen3-4b",
            False,
            read,
            lambda text: None,
            opener=FakeOpener(refused),
        )

    assert asked == ["> "]
    assert "the server stopped answering" in capsys.readouterr().err


@pytest.mark.spec("serve:chat:stopped-server-ends")
def test_a_tunnel_that_closes_without_an_answer_ends_the_chat(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # `ssh -L` accepts the local connection, then closes it when the pod side is gone.
    asked: list[str] = []

    def read(prompt: str) -> str:
        asked.append(prompt)
        return "hi"

    closed = http.client.RemoteDisconnected(
        "Remote end closed connection without response"
    )
    with pytest.raises(log.Refusal):
        chat.run(
            "http://127.0.0.1:1/v1",
            KEY,
            "qwen3-4b",
            False,
            read,
            lambda text: None,
            opener=FakeOpener(closed),
        )

    assert asked == ["> "]
    assert "the server stopped answering" in capsys.readouterr().err


@pytest.mark.spec("serve:chat:server-error-drops-the-turn")
def test_a_server_error_drops_the_turn_and_the_chat_goes_on(
    capsys: pytest.CaptureFixture[str],
) -> None:
    written: list[str] = []
    streamed = b'data: {"choices": [{"delta": {"content": "Hi"}}]}\n\ndata: [DONE]\n'
    opener = FakeOpener((500, b"oops"), (200, streamed))

    chat.run(
        "http://127.0.0.1:1/v1",
        KEY,
        "qwen3-4b",
        False,
        reader("lost", "kept"),
        written.append,
        opener=opener,
    )

    assert "the model did not answer" in capsys.readouterr().err
    assert "Hi" in written
    assert opener.sent(1)["messages"] == [{"role": "user", "content": "kept"}]


@pytest.mark.spec("serve:chat:streamed-text-cleaned")
@pytest.mark.parametrize("guarded", [True, False], ids=["cleaned", "twin-uncleaned"])
def test_streamed_text_is_cleaned_and_kept_as_streamed(
    guarded: bool, model: ModelServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    streamed = "\x1b]52;c;b3du\x07two\n\tlines"
    model.parts = [streamed]
    written: list[str] = []

    def write(text: str) -> None:
        written.append(text)
        model.written.release()

    if not guarded:
        # The twin: without the cleaning, the clipboard escape reaches the terminal.
        monkeypatch.setattr(log, "clean", lambda text, keep="": text)
    chat.run(
        model.base_url,
        KEY,
        "qwen3-4b",
        False,
        reader("hi", "again"),
        write,
        opener=OPENER,
    )

    assert (written[0] == "]52;c;b3dutwo\n\tlines") is guarded
    assert model.requests[1][2]["messages"] == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": streamed},
        {"role": "user", "content": "again"},
    ]
