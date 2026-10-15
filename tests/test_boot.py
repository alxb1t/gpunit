import os
import re
import shutil
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from gpunit.provider import fingerprint
from tests.helpers import install_stubs

BOOT = Path(__file__).parent.parent / "boot" / "boot.sh"
KEY = "rpa_pod_key"
POD = "pod-xyz"
FINGERPRINT = "SHA256:fromTheStub+/0"
NONCE = "0123456789abcdef0123456789abcdef"
CEILING = "7"
GRACE = "60"

# Answers each call from $CURL_CODES, one line per call (200 when empty), and logs
# its argv plus whether the header file held the key.
CURL = """#!/bin/bash
header=""
while [ $# -gt 0 ]; do
  case "$1" in -H) [ "${2#@}" != "$2" ] && header=$(cat "${2#@}") ;; esac
  args+=("$1"); shift
done
auth=no-header
grep -q "Authorization: Bearer $RUNPOD_API_KEY" <<<"$header" && auth=header-ok
echo "$auth ${args[*]}" >> "$CURL_LOG"
echo curl >> "$ORDER_LOG"
code=$(head -n 1 "$CURL_CODES" 2>/dev/null)
if [ -f "$CURL_CODES" ]; then
  tail -n +2 "$CURL_CODES" > "$CURL_CODES.next" && mv "$CURL_CODES.next" "$CURL_CODES"
fi
printf '%s' "${code:-200}"
"""

# Logs each wait and returns at once; the ceiling's own wait holds when asked to.
SLEEP = """#!/bin/bash
echo "sleep $1" >> "$ORDER_LOG"
if [ -n "${HOLD_CEILING:-}" ] && [ "$1" = "$GPUNIT_CEILING" ]; then
  exec /bin/sleep 600
fi
exit 0
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

SSH_KEYGEN = f"""#!/bin/bash
echo "$@" >> "$KEYGEN_LOG"
[ "$1" = "-lf" ] && echo "256 {FINGERPRINT} root@pod (ED25519)"
exit 0
"""


@dataclass
class Boot:
    code: int
    out: str
    err: str
    curl: list[str]
    # The curl calls and the waits, in the order they ran.
    order: list[str]
    sshd: list[str]
    served: list[str]
    keygen: list[str]


STUBS = {"curl": CURL, "sleep": SLEEP, "sshd": SSHD, "ssh-keygen": SSH_KEYGEN}


@pytest.fixture(scope="module")
def pod_bin(tmp_path_factory: pytest.TempPathFactory) -> Path:
    # Shared: each stub reads its behaviour and its logs from the test's environment.
    return install_stubs(tmp_path_factory.mktemp("bin"), STUBS)


@pytest.fixture
def pod(tmp_path: Path, pod_bin: Path) -> dict[str, str]:
    (tmp_path / "home").mkdir()
    image_config = tmp_path / "image_sshd_config"
    image_config.write_text(IMAGE_CONFIG, encoding="utf-8")
    return {
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
        **{
            name: str(tmp_path / f"{name.lower()}.txt")
            for name in (
                "CURL_LOG",
                "CURL_CODES",
                "ORDER_LOG",
                "SSHD_LOG",
                "SSHD_SERVED",
                "KEYGEN_LOG",
            )
        },
    }


def boot(env: dict[str, str], *command: str, merged: bool = False) -> Boot:
    """Run boot.sh in its own process group, then kill what it left behind.

    `merged` writes stderr into `out` too, in order, as the pod's log holds both.
    """
    out, err = Path(env["HOME"]) / "out", Path(env["HOME"]) / "err"
    # Files, not pipes: the ceiling's timer outlives boot and would hold a pipe open.
    with out.open("w") as stdout, err.open("w") as stderr:
        process = subprocess.Popen(
            ["bash", str(BOOT), "--", *command],
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
        curl=lines("CURL_LOG"),
        order=lines("ORDER_LOG"),
        sshd=lines("SSHD_LOG"),
        served=lines("SSHD_SERVED"),
        keygen=lines("KEYGEN_LOG"),
    )


def after_the_ceiling(result: Boot) -> list[str]:
    """Return the curl calls and the waits in order, but the ceiling's own wait."""
    return [step for step in result.order if step != f"sleep {CEILING}"]


def refuses_without(tool: str, named: str, pod: dict[str, str], bin_dir: Path) -> None:
    """Boot without `tool`; assert it refuses naming `named` and runs nothing."""
    # A PATH of the stubs and the few tools step 1 needs: the machine's own sshd, curl
    # or env must not stand in for the missing one.
    without = {name: script for name, script in STUBS.items() if name != tool}
    install_stubs(bin_dir, without)
    for name in ("bash", "date", "touch"):
        (bin_dir / name).symlink_to(str(shutil.which(name)))
    pod["PATH"] = str(bin_dir)

    result = boot(pod, "touch", f"{pod['HOME']}/ran")

    assert result.code == 1
    assert named in result.err
    assert not (Path(pod["HOME"]) / "ran").exists()
    assert result.curl == []


@pytest.mark.spec("boot:refuse:no-sshd")
def test_no_sshd_refuses(pod: dict[str, str], tmp_path: Path) -> None:
    refuses_without("sshd", "install openssh-server", pod, tmp_path / "bin")


@pytest.mark.spec("boot:refuse:no-curl")
def test_no_curl_refuses(pod: dict[str, str], tmp_path: Path) -> None:
    refuses_without("curl", "install curl", pod, tmp_path / "bin")


@pytest.mark.spec("boot:refuse:no-env")
def test_no_env_refuses(pod: dict[str, str], tmp_path: Path) -> None:
    refuses_without("env", "install coreutils", pod, tmp_path / "bin")


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
    assert result.curl == []


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
    assert after_the_ceiling(result) == ["curl"]
    [stop] = result.curl
    assert stop.startswith("header-ok ")
    assert f"/pods/{POD}/action" in stop


@pytest.mark.spec("boot:stop:ceiling")
def test_the_ceiling_stops_the_pod(pod: dict[str, str]) -> None:
    del pod["HOLD_CEILING"]
    # Runs until the ceiling's stop has been requested.
    wait = f'until [ -s "{pod["CURL_LOG"]}" ]; do /bin/sleep 0.05; done'

    result = boot(pod, "bash", "-c", wait)

    assert "the ceiling of 7s is reached" in result.err
    # No grace before the ceiling's stop; the command's end after it still waits.
    assert result.order[:2] == [f"sleep {CEILING}", "curl"]
    assert f"/pods/{POD}/action" in result.curl[0]
    assert '{"action":"stop"}' in result.curl[0]


@pytest.mark.spec("boot:stop:command-end")
def test_the_commands_end_stops_the_pod(pod: dict[str, str]) -> None:
    result = boot(pod, "true")

    assert result.code == 0
    assert after_the_ceiling(result) == [f"sleep {GRACE}", "curl"]
    assert "the command exited 0" in result.err
    [stop] = result.curl
    assert stop.startswith("header-ok ")
    assert f"https://api.runpod.io/v2/pods/{POD}/action" in stop
    assert KEY not in stop


@pytest.mark.spec("boot:stop:retries")
def test_a_failed_stop_retries_with_backoff(pod: dict[str, str]) -> None:
    Path(pod["CURL_CODES"]).write_text("500\n500\n200\n", encoding="utf-8")

    result = boot(pod, "true")

    assert result.code == 0
    assert len(result.curl) == 3
    # The grace comes before the first attempt; the stop's own waits come after it.
    assert after_the_ceiling(result) == [
        f"sleep {GRACE}",
        "curl",
        "sleep 30",
        "curl",
        "sleep 60",
        "curl",
    ]
    assert "the pod is stopping" in result.err


@pytest.mark.spec("boot:stop:refusal-no-grace")
def test_a_refusal_stops_without_the_grace(pod: dict[str, str]) -> None:
    pod["SSHD_FAIL"] = "1"

    result = boot(pod, "touch", f"{pod['HOME']}/ran")

    assert result.code == 1
    assert "refused: sshd did not start" in result.err
    assert not (Path(pod["HOME"]) / "ran").exists()
    assert after_the_ceiling(result) == ["curl"]


@pytest.mark.spec("boot:stop:refused-key-named")
def test_a_refused_key_is_named(pod: dict[str, str]) -> None:
    Path(pod["CURL_CODES"]).write_text("401\n403\n200\n", encoding="utf-8")

    result = boot(pod, "true")

    assert result.code == 0
    assert len(result.curl) == 3
    for code in ("401", "403"):
        assert (
            f"the stop answered HTTP {code}: the key cannot stop this pod; "
            "delete it by hand" in result.err
        )
    assert after_the_ceiling(result) == [
        f"sleep {GRACE}",
        "curl",
        "sleep 30",
        "curl",
        "sleep 60",
        "curl",
    ]
    assert "the pod is stopping" in result.err


@pytest.mark.spec("boot:sshd:fingerprint-printed")
@pytest.mark.spec("boot:sshd:pam-on")
@pytest.mark.spec("boot:sshd:root-only")
def test_the_fingerprint_line(pod: dict[str, str]) -> None:
    result = boot(pod, "true")

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


@pytest.mark.spec("boot:sshd:fingerprint-printed")
def test_gpunit_reads_the_served_key_from_boots_log(pod: dict[str, str]) -> None:
    # gpunit accepts a key line only once boot's `step: the command` line follows it
    # (0006 design D1): rewording that line would leave every session unverified.
    result = boot(pod, "true", merged=True)

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
    assert len(result.curl) == 1
    assert result.err.index("the command exited 3") < result.err.index(
        "the pod is stopping"
    )


@pytest.mark.spec("boot:child:no-key")
def test_the_child_holds_no_key(pod: dict[str, str]) -> None:
    result = boot(pod, "env")

    assert result.code == 0
    names = [line.split("=", 1)[0] for line in result.out.splitlines()]
    assert "RUNPOD_POD_ID" in names
    assert "RUNPOD_API_KEY" not in names
    [stop] = result.curl
    assert stop.startswith("header-ok ")


@pytest.mark.spec("boot:child:no-nonce")
def test_the_child_holds_no_nonce(pod: dict[str, str]) -> None:
    result = boot(pod, "env")

    assert result.code == 0
    names = [line.split("=", 1)[0] for line in result.out.splitlines()]
    assert "RUNPOD_POD_ID" in names
    assert "GPUNIT_NONCE" not in names
    # Boot's own key line still carries it.
    assert f"gpunit host key {NONCE}: {FINGERPRINT}" in result.out
