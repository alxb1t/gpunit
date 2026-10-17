import ast
import http.client
import io
import os
import runpy
import signal
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import urllib.response
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from email.message import Message
from pathlib import Path
from types import FrameType
from typing import Any

import pytest

from boot import boot
from tests.fakes import FakeOpener

BOOT = Path(boot.__file__)
KEY = "rpa_pod_key"
POD = "pod-xyz"
NONCE = "0123456789abcdef0123456789abcdef"
FINGERPRINT = "SHA256:fromTheFake+/0"
SSHD = "/usr/sbin/sshd"
CEILING = "7"
GRACE = f"sleep {boot.GRACE_S}"
KEY_GAP = f"sleep {boot.KEY_GAP_S}"
# urllib's own, taken before the `pod` fixture fakes it.
BUILD_OPENER = urllib.request.build_opener


class Exited(Exception):
    """`os._exit`, faked: the watchdog leaves the test instead of the process."""


@dataclass
class Child:
    """A command `Popen` started: it ends with `code`, and logs its signals."""

    code: int
    terminated: int = 0

    def wait(self) -> int:
        return self.code

    def terminate(self) -> None:
        self.terminated += 1


@dataclass
class Pod:
    """What boot reached outside its process, faked, and what it asked of each."""

    # The stops' answers, in turn; a 200 once the script runs out.
    api: FakeOpener = field(default_factory=FakeOpener)
    # The stops and the waits, in the order they ran.
    order: list[str] = field(default_factory=list)
    runs: list[list[str]] = field(default_factory=list)
    started: list[tuple[list[str], dict[str, str]]] = field(default_factory=list)
    handlers: dict[int, Callable[[int, FrameType | None], Any]] = field(
        default_factory=dict
    )
    fork: int = 4242
    sshd: str | None = SSHD
    failing: set[str] = field(default_factory=set)
    child: Child | Exception = field(default_factory=lambda: Child(0))

    def answer(self, *answers: int | Exception) -> None:
        """Script the stops' answers: an HTTP code, or the exception to raise."""
        self.api.answers = [
            a if isinstance(a, Exception) else (a, b"") for a in answers
        ]

    @property
    def stops(self) -> list[tuple[urllib.request.Request, float]]:
        return list(zip(self.api.requests, self.api.timeouts, strict=True))

    def build_opener(self, *handlers: object) -> "Pod":
        return self

    def open(self, request: urllib.request.Request, timeout: float) -> object:
        self.order.append("stop")
        if not self.api.answers:
            self.api.answers.append((200, b""))
        return self.api.open(request, timeout=timeout)

    def run(
        self, argv: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        self.runs.append(argv)
        program = Path(argv[0]).name
        if f"{program}:raise" in self.failing:
            raise FileNotFoundError(argv[0])
        if argv[:2] == ["ssh-keygen", "-lf"]:
            if "listing" in self.failing:
                raise subprocess.CalledProcessError(1, argv)
            return subprocess.CompletedProcess(argv, 0, f"256 {FINGERPRINT} root@pod\n")
        if program == "ssh-keygen" and "config" in self.failing:
            # A directory where the config goes: the config's write fails.
            (Path(argv[-1]).parent / "sshd_config").mkdir()
        return subprocess.CompletedProcess(argv, int(program in self.failing))

    def popen(self, argv: list[str], env: dict[str, str]) -> Child:
        self.started.append((argv, env))
        if isinstance(self.child, Exception):
            raise self.child
        return self.child

    def sleep(self, seconds: float) -> None:
        self.order.append(f"sleep {seconds}")

    def which(self, name: str) -> str | None:
        return self.sshd if name == "sshd" else None

    def exit(self, code: int) -> None:
        raise Exited(code)

    def signal(
        self, signum: int, handler: Callable[[int, FrameType | None], Any]
    ) -> None:
        self.handlers[signum] = handler

    def after_the_ceiling(self) -> list[str]:
        """Return the stops and the waits, but the ceiling's own and the key's pause."""
        return [
            step for step in self.order if step not in (f"sleep {CEILING}", KEY_GAP)
        ]


@pytest.fixture
def pod(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, isolated_home: Path) -> Pod:
    fake = Pod()
    monkeypatch.setattr(os, "fork", lambda: fake.fork)
    monkeypatch.setattr(os, "_exit", fake.exit)
    monkeypatch.setattr(boot.time, "sleep", fake.sleep)
    monkeypatch.setattr(urllib.request, "build_opener", fake.build_opener)
    monkeypatch.setattr(subprocess, "run", fake.run)
    monkeypatch.setattr(subprocess, "Popen", fake.popen)
    monkeypatch.setattr(boot.shutil, "which", fake.which)
    monkeypatch.setattr(signal, "signal", fake.signal)
    monkeypatch.setattr(boot, "RUN_SSHD", tmp_path / "run" / "sshd")
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    # A CA store the stop's TLS can trust, whatever this machine holds.
    store = tmp_path / "ca.pem"
    store.write_text("", encoding="utf-8")
    monkeypatch.setenv("SSL_CERT_FILE", str(store))
    isolated_home.mkdir()
    for name, value in {
        "RUNPOD_API_KEY": KEY,
        "RUNPOD_POD_ID": POD,
        "PUBLIC_KEY": "ssh-ed25519 AAAAsession gpunit-isekai",
        "GPUNIT_CEILING": CEILING,
        "GPUNIT_NONCE": NONCE,
    }.items():
        monkeypatch.setenv(name, value)
    return fake


def config_of(pod: Pod) -> list[str]:
    """Return the lines of the config sshd was started on."""
    [started] = [argv for argv in pod.runs if argv[0] == SSHD]
    return (
        Path(started[started.index("-f") + 1]).read_text(encoding="utf-8").splitlines()
    )


@pytest.mark.spec("boot:refuse:no-sshd")
def test_no_sshd_refuses(pod: Pod, capsys: pytest.CaptureFixture[str]) -> None:
    pod.sshd = None

    assert boot.main(["--", "true"]) == 1

    assert (
        "refused: sshd is not on PATH; install openssh-server"
        in capsys.readouterr().err
    )
    assert pod.started == []
    assert pod.order == []


def no_ca_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *roots: str) -> None:
    """Leave OpenSSL no CA file, and a CA directory holding `roots`."""
    monkeypatch.setenv("SSL_CERT_FILE", str(tmp_path / "no-ca.pem"))
    certs = tmp_path / "certs"
    certs.mkdir()
    for name in roots:
        (certs / name).write_text("", encoding="utf-8")
    monkeypatch.setenv("SSL_CERT_DIR", str(certs))


@pytest.mark.spec("boot:refuse:no-sshd")
@pytest.mark.parametrize("directory", ["missing", "empty"])
def test_no_ca_store_refuses_before_the_arm(
    pod: Pod,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    directory: str,
) -> None:
    # An image without ca-certificates: every stop would fail its certificate check.
    no_ca_file(tmp_path, monkeypatch)
    if directory == "missing":
        (tmp_path / "certs").rmdir()

    assert boot.main(["--", "true"]) == 1

    said = "refused: no CA store for the stop's TLS; install ca-certificates"
    assert said in capsys.readouterr().err
    # Nothing is armed yet: no watchdog, no stop.
    assert pod.order == []
    assert pod.started == []


@pytest.mark.spec("boot:refuse:no-sshd")
def test_a_ca_directory_alone_is_a_store(
    pod: Pod, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    no_ca_file(tmp_path, monkeypatch, "5ed36f99.0")

    assert boot.main(["--", "true"]) == 0

    assert pod.after_the_ceiling() == [GRACE, "stop"]


@pytest.mark.spec("boot:refuse:no-sshd")
def test_the_main_guard_runs_main(
    pod: Pod, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    pod.sshd = None
    monkeypatch.setattr(sys, "argv", [str(BOOT), "--", "true"])

    with pytest.raises(SystemExit) as exited:
        runpy.run_path(str(BOOT), run_name="__main__")

    assert exited.value.code == 1
    assert "install openssh-server" in capsys.readouterr().err


@pytest.mark.spec("boot:refuse:no-ceiling")
@pytest.mark.parametrize(
    ("name", "value", "said"),
    [
        ("GPUNIT_CEILING", None, "GPUNIT_CEILING is unset or empty"),
        ("GPUNIT_CEILING", "", "GPUNIT_CEILING is unset or empty"),
        ("GPUNIT_CEILING", "7m", "GPUNIT_CEILING is not a number of seconds"),
        ("RUNPOD_API_KEY", None, "RUNPOD_API_KEY is unset or empty"),
        ("RUNPOD_POD_ID", None, "RUNPOD_POD_ID is unset or empty"),
        ("PUBLIC_KEY", None, "PUBLIC_KEY is unset or empty"),
    ],
)
def test_a_gap_before_the_arm_refuses(
    pod: Pod,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    name: str,
    value: str | None,
    said: str,
) -> None:
    if value is None:
        monkeypatch.delenv(name)
    else:
        monkeypatch.setenv(name, value)

    assert boot.main(["--", "true"]) == 1

    assert f"refused: {said}" in capsys.readouterr().err
    # Nothing is armed yet: no watchdog, no stop.
    assert pod.order == []
    assert pod.started == []


@pytest.mark.spec("boot:refuse:no-ceiling")
def test_no_command_refuses(pod: Pod, capsys: pytest.CaptureFixture[str]) -> None:
    assert boot.main(["--"]) == 1

    said = "refused: no command after --; use boot.py -- <command>"
    assert said in capsys.readouterr().err
    assert pod.order == []


@pytest.mark.spec("boot:refuse:no-nonce")
@pytest.mark.spec("boot:stop:refusal-no-grace")
@pytest.mark.parametrize("nonce", [None, ""], ids=["unset", "empty"])
def test_no_nonce_refuses_and_stops(
    pod: Pod,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    nonce: str | None,
) -> None:
    if nonce is None:
        monkeypatch.delenv("GPUNIT_NONCE")
    else:
        monkeypatch.setenv("GPUNIT_NONCE", nonce)

    assert boot.main(["--", "true"]) == 1

    out, err = capsys.readouterr()
    assert "refused: GPUNIT_NONCE is unset or empty" in err
    assert "gpunit host key" not in out
    assert pod.started == []
    # Checked once armed: an older gpunit's pod stops, not restarts.
    assert pod.after_the_ceiling() == ["stop"]


@pytest.mark.spec("boot:stop:refusal-no-grace")
@pytest.mark.parametrize(
    ("failing", "said"),
    [
        ("sshd", "sshd did not start"),
        ("sshd:raise", "sshd did not start"),
        ("ssh-keygen", "the host key could not be made"),
        ("ssh-keygen:raise", "the host key could not be made"),
        ("config", "sshd's config could not be written"),
    ],
)
def test_a_refusal_in_sshd_stops_without_the_grace(
    pod: Pod, capsys: pytest.CaptureFixture[str], failing: str, said: str
) -> None:
    pod.failing.add(failing)

    assert boot.main(["--", "true"]) == 1

    assert f"refused: {said}" in capsys.readouterr().err
    assert pod.started == []
    assert pod.after_the_ceiling() == ["stop"]


@pytest.mark.spec("boot:stop:refusal-no-grace")
def test_no_directory_for_sshd_refuses(
    pod: Pod, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def full() -> str:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(tempfile, "mkdtemp", full)

    assert boot.main(["--", "true"]) == 1

    assert "refused: sshd's directory could not be made" in capsys.readouterr().err
    assert pod.after_the_ceiling() == ["stop"]


@pytest.mark.spec("boot:stop:own-error")
@pytest.mark.parametrize(
    "fault", ["listing", "popen"], ids=["fingerprint-unread", "popen-raises"]
)
def test_an_error_of_boots_own_stops_the_pod(pod: Pod, fault: str) -> None:
    if fault == "listing":
        pod.failing.add("listing")
    else:
        pod.child = RuntimeError("boot's own")

    with pytest.raises((subprocess.CalledProcessError, RuntimeError)):
        boot.main(["--", "true"])

    assert pod.after_the_ceiling() == ["stop"]


@pytest.mark.spec("boot:stop:ceiling")
def test_the_watchdog_stops_the_pod_at_the_ceiling(
    pod: Pod, capsys: pytest.CaptureFixture[str]
) -> None:
    pod.fork = 0

    with pytest.raises(Exited) as exited:
        boot.arm(CEILING, os.environ)

    assert exited.value.args == (0,)
    assert pod.order == [f"sleep {CEILING}", "stop"]
    assert "the ceiling of 7s is reached" in capsys.readouterr().err
    [(request, _)] = pod.stops
    assert request.full_url == f"{boot.API}/pods/{POD}/action"


@pytest.mark.spec("boot:stop:ceiling")
@pytest.mark.parametrize("guarded", [True, False], ids=["guard", "twin-unguarded"])
def test_the_watchdog_never_returns_into_the_main_flow(
    pod: Pod, monkeypatch: pytest.MonkeyPatch, guarded: bool
) -> None:
    pod.fork = 0
    pod.answer(ValueError("an answer boot cannot read"))
    if not guarded:
        # The twin: without the guard's `except BaseException` and `os._exit`, a failed
        # stop returns the child into main.
        def unguarded(ceiling: str, environ: Mapping[str, str]) -> None:
            if os.fork() == 0:
                boot.time.sleep(int(ceiling))
                boot.stop(environ)
                os._exit(0)

        monkeypatch.setattr(boot, "arm", unguarded)

    with pytest.raises((Exited, ValueError)) as left:
        boot.arm(CEILING, os.environ)

    assert isinstance(left.value, Exited) is guarded


@pytest.mark.spec("boot:stop:ceiling")
def test_a_watchdog_whose_stop_fails_says_so(
    pod: Pod, capsys: pytest.CaptureFixture[str]
) -> None:
    pod.fork = 0
    pod.answer(ValueError("a header urllib refuses"))

    with pytest.raises(Exited) as exited:
        boot.arm(CEILING, os.environ)

    assert exited.value.args == (1,)
    err = capsys.readouterr().err
    assert "the ceiling's stop failed; delete the pod by hand" in err
    assert "Traceback" in err
    assert "ValueError: a header urllib refuses" in err


@pytest.mark.spec("boot:stop:ceiling")
def test_the_arm_returns_at_once_in_boot(pod: Pod) -> None:
    boot.arm(CEILING, os.environ)

    assert pod.order == []


@pytest.mark.spec("boot:stop:command-end")
@pytest.mark.spec("boot:needs:no-curl")
def test_the_commands_end_stops_the_pod(
    pod: Pod, capsys: pytest.CaptureFixture[str]
) -> None:
    assert boot.main(["--", "true"]) == 0

    err = capsys.readouterr().err
    assert pod.after_the_ceiling() == [GRACE, "stop"]
    assert err.index("the command exited 0") < err.index("the pod is stopping")
    [(request, timeout)] = pod.stops
    assert request.full_url == f"https://api.runpod.io/v2/pods/{POD}/action"
    assert request.get_method() == "POST"
    assert request.data == b'{"action":"stop"}'
    assert request.get_header("Authorization") == f"Bearer {KEY}"
    assert request.get_header("Content-type") == "application/json"
    # Not urllib's default agent, which RunPod's Cloudflare refuses with a 403.
    assert request.get_header("User-agent") == "gpunit-boot"
    assert timeout == 30
    # The fake PATH holds sshd alone: the stop needs no curl.
    assert not any("curl" in argv[0] for argv in pod.runs)


class Redirecting(urllib.request.BaseHandler):
    """Answer the first stop with a 302 to a host that answers 200; log its calls."""

    handler_order = 100  # before urllib's own HTTPS handler, so no socket opens
    ELSEWHERE = "https://elsewhere.example/stop"

    def __init__(self) -> None:
        self.stops = 0
        self.elsewhere: list[dict[str, str]] = []

    def https_open(self, request: urllib.request.Request) -> "Answered":
        headers = Message()
        code = 200
        if request.host != "api.runpod.io":
            self.elsewhere.append(dict(request.header_items()))
        else:
            self.stops += 1
            if self.stops == 1:
                headers["Location"] = self.ELSEWHERE
                code = 302
        return Answered(request.full_url, code, headers)


class Answered(urllib.response.addinfourl):
    """An HTTPS answer of no body, as urllib's handler returns one."""

    def __init__(self, url: str, code: int, headers: Message) -> None:
        super().__init__(io.BytesIO(b""), headers, url, code)
        # Read by urllib's error processor on a 3xx.
        self.msg = "Found" if code == 302 else "OK"


@pytest.mark.spec("boot:needs:no-curl")
@pytest.mark.spec("boot:stop:retries")
def test_a_redirect_is_a_failed_stop_never_followed(
    pod: Pod, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    api = Redirecting()
    # urllib's own opener and redirect handling, on a faked HTTPS answer.
    monkeypatch.setattr(
        urllib.request, "build_opener", lambda *h: BUILD_OPENER(*h, api)
    )

    boot.stop(os.environ)

    assert api.elsewhere == []
    assert api.stops == 2
    assert pod.order == ["sleep 30"]
    err = capsys.readouterr().err
    assert "the stop answered HTTP 302; trying again in 30s" in err
    assert err.count("the pod is stopping") == 1


@pytest.mark.spec("boot:stop:command-end")
def test_the_lines_open_with_the_utc_time(
    pod: Pod, capsys: pytest.CaptureFixture[str]
) -> None:
    boot.main(["--", "true"])

    first = capsys.readouterr().err.splitlines()[0]
    assert first.endswith(" step: the ceiling, 7s")
    stamp = first.split(" ", 1)[0]
    assert len(stamp) == len("2026-10-17T09:00:00Z") and stamp.endswith("Z")


@pytest.mark.spec("boot:stop:retries")
def test_a_failed_stop_retries_with_backoff(
    pod: Pod, capsys: pytest.CaptureFixture[str]
) -> None:
    pod.answer(500, 500, 200)

    assert boot.main(["--", "true"]) == 0

    assert pod.after_the_ceiling() == [
        GRACE,
        "stop",
        "sleep 30",
        "stop",
        "sleep 60",
        "stop",
    ]
    err = capsys.readouterr().err
    assert "the stop answered HTTP 500; trying again in 30s" in err
    assert "the stop answered HTTP 500; trying again in 60s" in err
    assert "the pod is stopping" in err


@pytest.mark.spec("boot:stop:retries")
def test_the_backoff_stops_doubling_at_300s(pod: Pod) -> None:
    pod.answer(*[500] * 7)

    boot.stop(os.environ)

    waits = [step for step in pod.order if step != "stop"]
    assert waits == [f"sleep {s}" for s in (30, 60, 120, 240, 300, 300, 300)]


@pytest.mark.spec("boot:stop:retries")
@pytest.mark.parametrize(
    "answer",
    [
        urllib.error.URLError("no route to host"),
        TimeoutError("timed out"),
        http.client.BadStatusLine(""),
    ],
    ids=["no-route", "timeout", "bad-status"],
)
def test_no_answer_is_000_and_retried(
    pod: Pod, capsys: pytest.CaptureFixture[str], answer: Exception
) -> None:
    pod.answer(answer)

    boot.stop(os.environ)

    assert pod.order == ["stop", "sleep 30", "stop"]
    assert "the stop answered HTTP 000 (" in capsys.readouterr().err


@pytest.mark.spec("boot:stop:retries")
def test_no_ca_store_names_the_cause(
    pod: Pod, capsys: pytest.CaptureFixture[str]
) -> None:
    # What urllib raises on an image without ca-certificates: no root to trust RunPod's.
    unverified = ssl.SSLCertVerificationError(
        1,
        "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
        "unable to get local issuer certificate (_ssl.c:1006)",
    )
    pod.answer(urllib.error.URLError(unverified))

    boot.stop(os.environ)

    err = capsys.readouterr().err
    assert (
        "the stop answered HTTP 000 ([SSL: CERTIFICATE_VERIFY_FAILED] certificate "
        "verify failed: unable to get local issuer certificate (_ssl.c:1006)); "
        "trying again in 30s"
    ) in err
    assert KEY not in err


@pytest.mark.spec("boot:stop:refused-key-named")
def test_a_refused_key_is_named(pod: Pod, capsys: pytest.CaptureFixture[str]) -> None:
    pod.answer(401, 403, 200)

    assert boot.main(["--", "true"]) == 0

    err = capsys.readouterr().err
    for code in ("401", "403"):
        assert (
            f"the stop answered HTTP {code}: the key cannot stop this pod; "
            "delete it by hand" in err
        )
    assert pod.after_the_ceiling() == [
        GRACE,
        "stop",
        "sleep 30",
        "stop",
        "sleep 60",
        "stop",
    ]
    assert "the pod is stopping" in err


@pytest.mark.spec("boot:sshd:fingerprint-printed")
def test_the_fingerprint_line(pod: Pod, capsys: pytest.CaptureFixture[str]) -> None:
    boot.main(["--", "true"])

    out = capsys.readouterr().out
    assert out.splitlines() == [f"gpunit host key {NONCE}: {FINGERPRINT}"]
    # The served key is the one made on this boot, in a new directory, and it alone.
    [made] = [argv for argv in pod.runs if "-t" in argv]
    assert made[:7] == ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f"]
    host_key = made[7]
    assert not host_key.startswith("/etc/ssh/")
    assert ["ssh-keygen", "-lf", f"{host_key}.pub"] in pod.runs
    hostkeys = [line for line in config_of(pod) if line.lower().startswith("hostkey")]
    assert hostkeys == [f'HostKey "{host_key}"']


@pytest.mark.spec("boot:sshd:fingerprint-printed")
@pytest.mark.parametrize(
    ("gap", "paused"),
    [(boot.KEY_GAP_S, True), (0, False)],
    ids=["pause", "twin-no-pause"],
)
def test_a_pause_parts_the_key_line_from_the_step(
    pod: Pod,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    gap: int,
    paused: bool,
) -> None:
    # RunPod merges stdout and stderr out of order when lines come together.
    monkeypatch.setattr(boot, "KEY_GAP_S", gap)
    waits: list[tuple[float, str, str]] = []

    def sleep(seconds: float) -> None:
        if not waits:
            out, err = capsys.readouterr()
            waits.append((seconds, out, err))

    monkeypatch.setattr(boot.time, "sleep", sleep)

    boot.main(["--", "true"])

    # The first wait in boot: the key line is out, the step not yet.
    [(seconds, out, err)] = waits
    assert f"gpunit host key {NONCE}: " in out
    assert "step: the command" not in err
    # The twin: with no pause, the two lines are written together.
    assert (seconds >= 1) is paused


@pytest.mark.spec("boot:sshd:authorized-key")
def test_the_authorized_key(pod: Pod, isolated_home: Path) -> None:
    before = os.umask(0o022)
    try:
        boot.main(["--", "true"])
        assert os.umask(0o022) == 0o022
    finally:
        os.umask(before)

    keys = isolated_home / ".ssh"
    authorized = keys / "authorized_keys"
    assert authorized.read_text(encoding="utf-8") == f"{os.environ['PUBLIC_KEY']}\n"
    assert authorized.stat().st_mode & 0o777 == 0o600
    assert keys.stat().st_mode & 0o777 == 0o700


@pytest.mark.spec("boot:sshd:pam-on")
@pytest.mark.spec("boot:sshd:root-only")
def test_sshds_config_is_boots_own(pod: Pod) -> None:
    boot.main(["--", "true"])

    config = config_of(pod)
    assert "UsePAM yes" in config
    assert "AllowUsers root" in config
    assert "PasswordAuthentication no" in config
    assert not any("include" in line.lower() for line in config)
    # sshd re-execs itself, so it is started by its absolute path.
    [started] = [argv for argv in pod.runs if argv[0] == SSHD]
    assert started[1] == "-f"
    assert boot.RUN_SSHD.is_dir()


@pytest.mark.spec("boot:sshd:root-only")
def test_an_unmakeable_run_sshd_is_ignored(
    pod: Pod, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "run").write_text("a file", encoding="utf-8")
    monkeypatch.setattr(boot, "RUN_SSHD", tmp_path / "run" / "sshd")

    assert boot.main(["--", "true"]) == 0

    assert [argv for argv in pod.runs if argv[0] == SSHD]


@pytest.mark.spec("boot:child:code")
@pytest.mark.parametrize(
    ("argv", "child", "code"),
    [
        (["--", "sh", "-c", "exit 3"], Child(3), 3),
        (["sh", "-c", "exit 3"], Child(3), 3),
        (["--", "sleep", "600"], Child(-signal.SIGTERM), 128 + signal.SIGTERM),
    ],
    ids=["exit-3", "no-dashes", "sigterm"],
)
def test_the_childs_code(
    pod: Pod,
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
    child: Child,
    code: int,
) -> None:
    pod.child = child

    assert boot.main(argv) == code

    err = capsys.readouterr().err
    assert err.index(f"the command exited {code}") < err.index("the pod is stopping")
    [(started, _)] = pod.started
    assert started == [arg for arg in argv if arg != "--"]
    assert pod.after_the_ceiling() == [GRACE, "stop"]


@pytest.mark.spec("boot:child:code")
def test_sigterm_reaches_the_command(pod: Pod) -> None:
    child = Child(0)
    pod.child = child

    boot.main(["--", "true"])
    pod.handlers[signal.SIGTERM](signal.SIGTERM, None)

    assert child.terminated == 1


@pytest.mark.spec("boot:child:code")
def test_a_command_that_cannot_start_gives_127(
    pod: Pod, capsys: pytest.CaptureFixture[str]
) -> None:
    pod.child = FileNotFoundError(2, "No such file or directory", "nope")

    assert boot.main(["--", "nope"]) == 127

    err = capsys.readouterr().err
    assert "the command could not start: " in err
    assert "the command exited 127" in err
    # The grace and the stop follow, as after any command's end.
    assert pod.after_the_ceiling() == [GRACE, "stop"]


@pytest.mark.spec("boot:child:no-key")
@pytest.mark.spec("boot:child:no-nonce")
@pytest.mark.spec("boot:needs:no-env")
def test_the_child_holds_no_key_and_no_nonce(pod: Pod) -> None:
    boot.main(["--", "/bin/true"])

    # The command itself is started, not `env` around it.
    [(argv, env)] = pod.started
    assert argv == ["/bin/true"]
    assert env["RUNPOD_POD_ID"] == POD
    assert "RUNPOD_API_KEY" not in env
    assert "GPUNIT_NONCE" not in env
    # The stop still carries the key.
    [(request, _)] = pod.stops
    assert request.get_header("Authorization") == f"Bearer {KEY}"


def foreign(source: str) -> list[str]:
    """Return each top-level module `source` imports outside the stdlib, or gpunit."""
    names = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names += [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names.append((node.module or "").split(".")[0])
    return [
        name
        for name in names
        if name not in sys.stdlib_module_names or name == "gpunit"
    ]


@pytest.mark.spec("boot:file:stdlib-only")
@pytest.mark.parametrize(
    ("source", "found"),
    [
        (BOOT.read_text(encoding="utf-8"), []),
        (
            "import gpunit.log\nfrom requests import get\nimport os\n",
            ["gpunit", "requests"],
        ),
    ],
    ids=["boot", "twin-foreign"],
)
def test_boot_imports_the_stdlib_alone(source: str, found: list[str]) -> None:
    assert foreign(source) == found
