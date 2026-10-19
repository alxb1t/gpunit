import os
import re
import shutil
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from boot.boot import KEY_GAP_S
from gpunit.contract import fingerprint
from tests.helpers import install_stubs

BOOT = Path(__file__).parent.parent / "boot" / "boot.py"
KEY = "rpa_pod_key"
POD = "pod-xyz"
FINGERPRINT = "SHA256:fromTheStub+/0"
NONCE = "0123456789abcdef0123456789abcdef"
CEILING = "7"
GRACE = "60"
KEY_GAP = f"sleep {KEY_GAP_S}"

# First on boot's PYTHONPATH: the stop answers from $STOP_CODES, one line a call (200
# when empty), and logs whether the header held the key; each wait returns at once, but
# the ceiling's own holds when asked to. boot.py holds no test knob.
SITECUSTOMIZE = """\
import email.message
import os
import time
import urllib.error
import urllib.request

_sleep = time.sleep


def _log(name, line):
    with open(os.environ[name], "a", encoding="utf-8") as log:
        log.write(line + "\\n")


def _open(request, timeout):
    key = os.environ.get("RUNPOD_API_KEY")
    header = request.get_header("Authorization") == f"Bearer {key}"
    # The order first: a command that waits on the stop's log must find it there.
    _log("ORDER_LOG", "stop")
    auth = "header-ok" if header else "no-header"
    sent = f"{request.get_method()} {request.full_url} {request.data.decode()}"
    _log("STOP_LOG", f"{auth} {sent} {timeout}")
    path = os.environ["STOP_CODES"]
    codes = open(path).read().splitlines() if os.path.exists(path) else []
    with open(path, "w") as rest:
        rest.write("".join(f"{code}\\n" for code in codes[1:]))
    code = codes[0] if codes else "200"
    if code == "200":
        return _Answered()
    raise urllib.error.HTTPError(
        request.full_url, int(code), "no", email.message.Message(), None
    )


class _Opener:
    open = staticmethod(_open)


class _Answered:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None


def _sleep_logged(seconds):
    _log("ORDER_LOG", f"sleep {seconds}")
    if os.environ.get("HOLD_CEILING") and str(seconds) == os.environ["GPUNIT_CEILING"]:
        _sleep(600)


urllib.request.build_opener = lambda *handlers: _Opener()
time.sleep = _sleep_logged
"""

# Logs its argv, then the host keys it would serve as OpenSSH does: HostKey is a list,
# so each HostKey of its config (-f, else the image's) and each -o HostKey adds one.
SSHD = """#!/bin/bash
echo "$@" >> "$SSHD_LOG"
[ -z "${SSHD_FAIL:-}" ] || exit 1
config=$SSHD_IMAGE_CONFIG
: > "$SSHD_SERVED"
while [ $# -gt 0 ]; do
  case "$1" in
    -f) config=$2; shift ;;
    -o) [ "${2#HostKey=}" = "$2" ] || echo "${2#HostKey=}" >> "$SSHD_SERVED"; shift ;;
  esac
  shift
done
awk 'tolower($1) == "hostkey" { gsub(/"/, "", $2); print $2 }' "$config" \\
  >> "$SSHD_SERVED"
"""

# The image's own sshd_config, as a base that generates its host keys at build time
# ships it. A path in the test's directory: the machine's /etc/ssh is never read.
IMAGE_CONFIG = """\
HostKey /etc/ssh/ssh_host_rsa_key
HostKey /etc/ssh/ssh_host_ed25519_key
UsePAM yes
"""

# Logs its argv; `-lf` lists the stub's fingerprint, or fails when asked to.
SSH_KEYGEN = f"""#!/bin/bash
echo "$@" >> "$KEYGEN_LOG"
if [ "$1" = "-lf" ]; then
  [ -z "${{KEYGEN_LIST_FAIL:-}}" ] || exit 1
  echo "256 {FINGERPRINT} root@pod (ED25519)"
fi
exit 0
"""


@dataclass
class Boot:
    code: int
    out: str
    err: str
    stops: list[str]
    # The stops and the waits, in the order they ran.
    order: list[str]
    sshd: list[str]
    served: list[str]
    keygen: list[str]


STUBS = {"sshd": SSHD, "ssh-keygen": SSH_KEYGEN}


@pytest.fixture(scope="module")
def pod_bin(tmp_path_factory: pytest.TempPathFactory) -> Path:
    # Shared: each stub reads its behaviour and its logs from the test's environment.
    return install_stubs(tmp_path_factory.mktemp("bin"), STUBS)


@pytest.fixture
def pod(tmp_path: Path, pod_bin: Path) -> dict[str, str]:
    (tmp_path / "home").mkdir()
    site = tmp_path / "site"
    site.mkdir()
    (site / "sitecustomize.py").write_text(SITECUSTOMIZE, encoding="utf-8")
    image_config = tmp_path / "image_sshd_config"
    image_config.write_text(IMAGE_CONFIG, encoding="utf-8")
    # A CA store boot's check finds, whatever this machine holds; the stop is faked.
    store = tmp_path / "ca.pem"
    store.write_text("", encoding="utf-8")
    return {
        "SSL_CERT_FILE": str(store),
        "PATH": f"{pod_bin}:/usr/bin:/bin",
        "HOME": str(tmp_path / "home"),
        "RUNPOD_API_KEY": KEY,
        "RUNPOD_POD_ID": POD,
        "PUBLIC_KEY": "ssh-ed25519 AAAAsession gpunit-isekai",
        "GPUNIT_CEILING": CEILING,
        "GPUNIT_NONCE": NONCE,
        "HOLD_CEILING": "1",
        "TMPDIR": str(tmp_path),
        "SSHD_IMAGE_CONFIG": str(image_config),
        "PYTHONPATH": str(site),
        **{
            name: str(tmp_path / f"{name.lower()}.txt")
            for name in (
                "STOP_LOG",
                "STOP_CODES",
                "ORDER_LOG",
                "SSHD_LOG",
                "SSHD_SERVED",
                "KEYGEN_LOG",
            )
        },
    }


def boot(env: dict[str, str], *command: str, merged: bool = False) -> Boot:
    """Run boot.py in its own process group, then kill what it left behind.

    `merged` writes stderr into `out` too, in order, as the pod's log holds both.
    """
    out, err = Path(env["HOME"]) / "out", Path(env["HOME"]) / "err"
    # Files, not pipes: the ceiling's watchdog outlives boot and would hold a pipe open.
    with out.open("w") as stdout, err.open("w") as stderr:
        process = subprocess.Popen(
            [sys.executable, str(BOOT), "--", *command],
            env=env,
            stdout=stdout,
            stderr=stdout if merged else stderr,
            start_new_session=True,
        )
        try:
            code = process.wait(timeout=20)
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def lines(name: str) -> list[str]:
        path = Path(env[name])
        return path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    return Boot(
        code=code,
        out=out.read_text(encoding="utf-8"),
        err=err.read_text(encoding="utf-8"),
        stops=lines("STOP_LOG"),
        order=lines("ORDER_LOG"),
        sshd=lines("SSHD_LOG"),
        served=lines("SSHD_SERVED"),
        keygen=lines("KEYGEN_LOG"),
    )


def after_the_ceiling(result: Boot) -> list[str]:
    """Return the stops and the waits in order, but the ceiling's and the key's."""
    return [step for step in result.order if step not in (f"sleep {CEILING}", KEY_GAP)]


def only_stubs(pod: dict[str, str], bin_dir: Path, *tools: str) -> None:
    """Put the stubs and `tools` alone on boot's PATH: the machine's own stay off it."""
    install_stubs(bin_dir, STUBS)
    for name in tools:
        (bin_dir / name).symlink_to(str(shutil.which(name)))
    pod["PATH"] = str(bin_dir)


@pytest.mark.spec("boot:refuse:no-sshd")
def test_no_sshd_refuses(pod: dict[str, str], tmp_path: Path) -> None:
    only_stubs(pod, tmp_path / "bin", "touch")
    (tmp_path / "bin" / "sshd").unlink()

    result = boot(pod, "touch", f"{pod['HOME']}/ran")

    assert result.code == 1
    assert "install openssh-server" in result.err
    assert not (Path(pod["HOME"]) / "ran").exists()
    assert result.stops == []


# The command by its absolute path: prints the names in its environment, one a line.
PRINT_NAMES = [sys.executable, "-c", "import os; print(*os.environ, sep='\\n')"]


@pytest.mark.spec("boot:needs:no-curl")
@pytest.mark.spec("boot:needs:no-env")
def test_boot_needs_neither_curl_nor_env(pod: dict[str, str], tmp_path: Path) -> None:
    # awk: the sshd stub reads its config with it.
    only_stubs(pod, tmp_path / "bin", "awk")
    assert shutil.which("curl", path=pod["PATH"]) is None
    assert shutil.which("env", path=pod["PATH"]) is None

    result = boot(pod, *PRINT_NAMES)

    assert result.code == 0
    names = result.out.splitlines()
    assert "RUNPOD_POD_ID" in names
    assert "RUNPOD_API_KEY" not in names
    assert "GPUNIT_NONCE" not in names
    [stop] = result.stops
    assert stop.startswith("header-ok ")


@pytest.mark.spec("boot:file:stdlib-only")
def test_boot_runs_on_the_stdlib_alone(pod: dict[str, str], tmp_path: Path) -> None:
    # -I -S: no site-packages, no PYTHONPATH and no repo on sys.path; every import of
    # boot.py must resolve, or it would fail before its refusal.
    only_stubs(pod, tmp_path / "bin")
    (tmp_path / "bin" / "sshd").unlink()

    result = subprocess.run(
        [sys.executable, "-I", "-S", str(BOOT), "--", "true"],
        env=pod,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 1
    assert "refused: sshd is not on PATH" in result.stderr


@pytest.mark.spec("boot:refuse:no-ceiling")
@pytest.mark.parametrize(
    ("unset", "named"),
    [
        ("GPUNIT_CEILING", "GPUNIT_CEILING"),
        ("RUNPOD_API_KEY", "RUNPOD_API_KEY"),
        ("RUNPOD_POD_ID", "RUNPOD_POD_ID"),
        ("PUBLIC_KEY", "PUBLIC_KEY"),
    ],
)
def test_a_missing_variable_refuses(
    unset: str, named: str, pod: dict[str, str]
) -> None:
    del pod[unset]

    result = boot(pod, "touch", f"{pod['HOME']}/ran")

    assert result.code == 1
    assert named in result.err
    assert not (Path(pod["HOME"]) / "ran").exists()
    assert result.stops == []


@pytest.mark.spec("boot:refuse:no-nonce")
@pytest.mark.spec("boot:stop:refusal-no-grace")
def test_no_nonce_refuses(pod: dict[str, str]) -> None:
    del pod["GPUNIT_NONCE"]

    result = boot(pod, "touch", f"{pod['HOME']}/ran")

    assert result.code == 1
    assert "GPUNIT_NONCE is unset or empty" in result.err
    assert "gpunit host key" not in result.out
    assert not (Path(pod["HOME"]) / "ran").exists()
    # Checked once the ceiling is armed: an older gpunit's pod stops, not restarts.
    assert after_the_ceiling(result) == ["stop"]
    [stop] = result.stops
    assert stop.startswith("header-ok ")
    assert f"/pods/{POD}/action" in stop


@pytest.mark.spec("boot:stop:ceiling")
def test_the_ceiling_stops_the_pod(pod: dict[str, str]) -> None:
    del pod["HOLD_CEILING"]
    # Runs until the ceiling's stop has been requested.
    wait = f'until [ -s "{pod["STOP_LOG"]}" ]; do /bin/sleep 0.05; done'

    result = boot(pod, "bash", "-c", wait)

    assert "the ceiling of 7s is reached" in result.err
    # No grace before the ceiling's stop; the command's end after it still waits.
    assert result.order[:2] == [f"sleep {CEILING}", "stop"]
    assert f"/pods/{POD}/action" in result.stops[0]
    assert '{"action":"stop"}' in result.stops[0]


@pytest.mark.spec("boot:stop:command-end")
def test_the_commands_end_stops_the_pod(pod: dict[str, str]) -> None:
    result = boot(pod, "true")

    assert result.code == 0
    assert after_the_ceiling(result) == [f"sleep {GRACE}", "stop"]
    assert "the command exited 0" in result.err
    [stop] = result.stops
    assert stop.startswith("header-ok POST ")
    assert f"https://api.runpod.io/v2/pods/{POD}/action" in stop
    assert KEY not in stop


@pytest.mark.spec("boot:stop:retries")
def test_a_failed_stop_retries_with_backoff(pod: dict[str, str]) -> None:
    Path(pod["STOP_CODES"]).write_text("500\n500\n200\n", encoding="utf-8")

    result = boot(pod, "true")

    assert result.code == 0
    assert len(result.stops) == 3
    # The grace comes before the first attempt; the stop's own waits come after it.
    assert after_the_ceiling(result) == [
        f"sleep {GRACE}",
        "stop",
        "sleep 30",
        "stop",
        "sleep 60",
        "stop",
    ]
    assert "the pod is stopping" in result.err


@pytest.mark.spec("boot:stop:refusal-no-grace")
def test_a_refusal_stops_without_the_grace(pod: dict[str, str]) -> None:
    pod["SSHD_FAIL"] = "1"

    result = boot(pod, "touch", f"{pod['HOME']}/ran")

    assert result.code == 1
    assert "refused: sshd did not start" in result.err
    assert not (Path(pod["HOME"]) / "ran").exists()
    assert after_the_ceiling(result) == ["stop"]


@pytest.mark.spec("boot:stop:own-error")
def test_an_error_of_boots_own_stops_the_pod(pod: dict[str, str]) -> None:
    pod["KEYGEN_LIST_FAIL"] = "1"

    result = boot(pod, "touch", f"{pod['HOME']}/ran")

    assert result.code == 1
    assert "Traceback" in result.err
    assert not (Path(pod["HOME"]) / "ran").exists()
    assert after_the_ceiling(result) == ["stop"]


@pytest.mark.spec("boot:stop:refused-key-named")
def test_a_refused_key_is_named(pod: dict[str, str]) -> None:
    Path(pod["STOP_CODES"]).write_text("401\n403\n200\n", encoding="utf-8")

    result = boot(pod, "true")

    assert result.code == 0
    assert len(result.stops) == 3
    for code in ("401", "403"):
        assert (
            f"the stop answered HTTP {code}: the key cannot stop this pod; "
            "delete it by hand" in result.err
        )
    assert after_the_ceiling(result) == [
        f"sleep {GRACE}",
        "stop",
        "sleep 30",
        "stop",
        "sleep 60",
        "stop",
    ]
    assert "the pod is stopping" in result.err


@pytest.mark.spec("boot:sshd:fingerprint-printed")
@pytest.mark.spec("boot:sshd:pam-on")
@pytest.mark.spec("boot:sshd:root-only")
def test_the_fingerprint_line(pod: dict[str, str]) -> None:
    result = boot(pod, "true", merged=True)

    printed = [
        line for line in result.out.splitlines() if line.startswith("gpunit host key")
    ]
    assert printed == [f"gpunit host key {NONCE}: {FINGERPRINT}"]
    assert re.fullmatch(rf"gpunit host key {NONCE}: SHA256:[A-Za-z0-9+/]+", printed[0])
    # The served key is the one made on this boot, and it alone: never one the image
    # baked in, even when the image's sshd_config names its own HostKey lines.
    [made] = [line.split() for line in result.keygen if "-t ed25519" in line]
    host_key = made[made.index("-f") + 1]
    assert not host_key.startswith("/etc/ssh/")
    assert result.served == [host_key]
    # The stub follows no Include, so boot's config must name none.
    [started] = result.sshd
    config = Path(started.removeprefix("-f ")).read_text(encoding="utf-8")
    assert "include" not in config.lower()
    assert "UsePAM yes" in config.splitlines()
    assert "AllowUsers root" in config.splitlines()
    assert f"-lf {host_key}.pub" in result.keygen
    # The pause that keeps the key line ahead of `step: the command` in RunPod's log.
    assert KEY_GAP in result.order
    # gpunit accepts a key line only once boot's `step: the command` line follows it
    # (0006 design D1): rewording that line would leave every session unverified.
    assert fingerprint(result.out.splitlines(), NONCE) == FINGERPRINT


@pytest.mark.spec("boot:sshd:authorized-key")
def test_the_authorized_key(pod: dict[str, str]) -> None:
    boot(pod, "true")

    authorized = Path(pod["HOME"]) / ".ssh" / "authorized_keys"
    assert authorized.read_text(encoding="utf-8") == f"{pod['PUBLIC_KEY']}\n"
    assert authorized.stat().st_mode & 0o777 == 0o600


@pytest.mark.spec("boot:child:code")
def test_the_childs_code(pod: dict[str, str]) -> None:
    result = boot(pod, "bash", "-c", "exit 3")

    assert result.code == 3
    assert len(result.stops) == 1
    assert result.err.index("the command exited 3") < result.err.index(
        "the pod is stopping"
    )


@pytest.mark.spec("boot:child:no-key")
@pytest.mark.spec("boot:child:no-nonce")
def test_the_child_holds_no_key_and_no_nonce(pod: dict[str, str]) -> None:
    result = boot(pod, "env")

    assert result.code == 0
    names = [line.split("=", 1)[0] for line in result.out.splitlines()]
    assert "RUNPOD_POD_ID" in names
    assert "RUNPOD_API_KEY" not in names
    assert "GPUNIT_NONCE" not in names
    [stop] = result.stops
    assert stop.startswith("header-ok ")
    # Boot's own key line still carries it.
    assert f"gpunit host key {NONCE}: {FINGERPRINT}" in result.out
