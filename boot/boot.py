"""Run the pod's half of a gpunit session, and stop the pod however it ends.

Arm the ceiling, serve sshd on a fresh host key, print its fingerprint, run the
command. Why each step: openspec 0001-core design D11; why Python: 0012 design D1.

    ENTRYPOINT ["python3", "/opt/gpunit/boot.py", "--"]
"""

import contextlib
import http.client
import os
import re
import shutil
import signal
import ssl
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.request
from collections.abc import Mapping
from email.message import Message
from pathlib import Path
from typing import IO

API = "https://api.runpod.io/v2"
RETRY_S = 30
MAX_RETRY_S = 300
# The command's exit line must reach gpunit's log read, every 30s, before the stop.
GRACE_S = 60
# stdout and stderr reach RunPod's log on separate pipes, and lines written together
# can merge swapped: the pause keeps the key line before `step: the command`, which
# gpunit needs after it (0012 design D1). Remove when gpunit reads them in any order.
KEY_GAP_S = 1
NEEDED = ("RUNPOD_API_KEY", "RUNPOD_POD_ID", "PUBLIC_KEY", "GPUNIT_CEILING")
# The stop key and the nonce are boot's: the command does not inherit them, though a
# root command can still read them from boot's /proc.
WITHHELD = ("RUNPOD_API_KEY", "GPUNIT_NONCE")
RUN_SSHD = Path("/run/sshd")

# sshd's config is boot's own, not the image's: HostKey is a list, so a key the image's
# sshd_config names would be served beside the fresh one, and -o HostKey only adds.
# UsePAM: without it, sshd refuses a root whose password is locked with `!`.
# AllowUsers: root alone, so a key the image baked in for another account is not served.
SSHD_CONFIG = """\
HostKey "{host_key}"
PermitRootLogin prohibit-password
AuthorizedKeysFile .ssh/authorized_keys
PasswordAuthentication no
KbdInteractiveAuthentication no
UsePAM yes
AllowUsers root
Subsystem sftp internal-sftp
"""


class Refused(Exception):
    """A gap boot names before it exits 1."""


def say(text: str) -> None:
    """Write one line, `<UTC> <text>`, to stderr at once."""
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print(f"{stamp} {text}", file=sys.stderr, flush=True)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Follow no redirect: the host it names never stopped the pod."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: Message,
        newurl: str,
    ) -> None:
        """Return None, so the 3xx is raised as an `HTTPError` and retried."""
        return None


def _answer(environ: Mapping[str, str]) -> str:
    """Return the HTTP code of one stop request, "000 (<cause>)" when none came back."""
    request = urllib.request.Request(
        f"{API}/pods/{environ['RUNPOD_POD_ID']}/action",
        data=b'{"action":"stop"}',
        headers={
            "Authorization": f"Bearer {environ['RUNPOD_API_KEY']}",
            "Content-Type": "application/json",
            # RunPod's Cloudflare refuses urllib's default agent with a 403 (code 1010).
            "User-Agent": "gpunit-boot",
        },
        method="POST",
    )
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=30) as response:
            return str(response.status)
    except urllib.error.HTTPError as error:
        return str(error.code)
    except (OSError, http.client.HTTPException) as error:
        # The cause, a missing CA store say, holds no key.
        return f"000 ({getattr(error, 'reason', error)})"


def stop(environ: Mapping[str, str]) -> None:
    """Request the pod's stop until RunPod answers 200."""
    # A stop that gave up would leave the pod billing, so it retries until a 200.
    wait_s = RETRY_S
    while True:
        code = _answer(environ)
        if code == "200":
            say("the pod is stopping")
            return
        if code in ("401", "403"):
            say(
                f"the stop answered HTTP {code}: the key cannot stop this pod; "
                "delete it by hand"
            )
        else:
            say(f"the stop answered HTTP {code}; trying again in {wait_s}s")
        time.sleep(wait_s)
        wait_s = min(wait_s * 2, MAX_RETRY_S)


def _trusts_nothing() -> bool:
    """Return True when OpenSSL finds no CA file, nor a CA directory holding a file."""
    paths = ssl.get_default_verify_paths()
    if paths.cafile:
        return False
    return not (paths.capath and any(Path(paths.capath).iterdir()))


def check(environ: Mapping[str, str], command: list[str]) -> None:
    """Raise `Refused` naming the first gap boot cannot run with."""
    if shutil.which("sshd") is None:
        raise Refused("sshd is not on PATH; install openssh-server in the image")
    # Without a CA store every stop fails its certificate check, the ceiling's too.
    if _trusts_nothing():
        raise Refused(
            "no CA store for the stop's TLS; install ca-certificates in the image"
        )
    for name in NEEDED:
        if not environ.get(name):
            raise Refused(f"{name} is unset or empty")
    if not re.fullmatch(r"[0-9]+", environ["GPUNIT_CEILING"]):
        raise Refused("GPUNIT_CEILING is not a number of seconds")
    if not command:
        raise Refused("no command after --; use boot.py -- <command>")


def arm(ceiling: str, environ: Mapping[str, str]) -> None:
    """Fork the watchdog that stops the pod at `ceiling` seconds; return at once."""
    # A process, not a thread: it outlives a crash of boot's main flow (0012 design D3).
    sys.stdout.flush()
    sys.stderr.flush()
    if os.fork() == 0:
        # The watchdog never reaches the main flow's own stop.
        try:
            time.sleep(int(ceiling))
            say(f"the ceiling of {ceiling}s is reached")
            stop(environ)
        except BaseException:
            say("the ceiling's stop failed; delete the pod by hand")
            traceback.print_exc()
            sys.stderr.flush()
            os._exit(1)
        os._exit(0)


def sshd(home: Path, public_key: str) -> Path:
    """Serve sshd for `public_key` alone on a fresh host key; return the key's path."""
    # A host key made on this pod at each boot, in a new directory: never one the image
    # baked in, as openssh-server's install does.
    say("step: sshd")
    keys = home / ".ssh"
    keys.mkdir(parents=True, exist_ok=True)
    keys.chmod(0o700)
    authorized = keys / "authorized_keys"
    umask = os.umask(0o077)
    try:
        authorized.write_text(f"{public_key}\n", encoding="utf-8")
    finally:
        os.umask(umask)
    authorized.chmod(0o600)
    with contextlib.suppress(OSError):
        RUN_SSHD.mkdir(parents=True, exist_ok=True)
    try:
        directory = Path(tempfile.mkdtemp())
    except OSError:
        raise Refused("sshd's directory could not be made") from None
    host_key = directory / "ssh_host_ed25519_key"
    keygen = ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(host_key)]
    if _fails(keygen):
        raise Refused("the host key could not be made")
    config = directory / "sshd_config"
    try:
        config.write_text(SSHD_CONFIG.format(host_key=host_key), encoding="utf-8")
    except OSError:
        raise Refused("sshd's config could not be written") from None
    # sshd re-execs itself, so it is started by its absolute path.
    if _fails([shutil.which("sshd") or "sshd", "-f", str(config)]):
        raise Refused("sshd did not start")
    return host_key


def _fails(argv: list[str]) -> bool:
    """Return True when `argv` cannot start or exits non-zero."""
    try:
        return subprocess.run(argv).returncode != 0
    except OSError:
        return True


def _fingerprint(host_key: Path) -> str:
    """Return the host key's fingerprint, e.g. "SHA256:abc"."""
    listed = subprocess.run(
        ["ssh-keygen", "-lf", f"{host_key}.pub"],
        capture_output=True,
        text=True,
        check=True,
    )
    return listed.stdout.split()[1]


def run(command: list[str], environ: Mapping[str, str]) -> int:
    """Run the command as a child, `SIGTERM` forwarded; return its code as bash does."""
    say("step: the command")
    env = {name: value for name, value in environ.items() if name not in WITHHELD}
    try:
        child = subprocess.Popen(command, env=env)
    except OSError as error:
        say(f"the command could not start: {error}")
        code = 127
    else:
        # The wait resumes after the handler (PEP 475): boot waits for the child's end.
        signal.signal(signal.SIGTERM, lambda _signum, _frame: child.terminate())
        code = child.wait()
        code = 128 - code if code < 0 else code
    say(f"the command exited {code}")
    return code


def main(argv: list[str]) -> int:
    """Boot the pod for the command after `--`; return the command's code, or 1."""
    environ = os.environ
    command = argv[1:] if argv[:1] == ["--"] else argv
    # Nothing is armed yet, so a refusal here stops nothing.
    try:
        check(environ, command)
    except Refused as gap:
        say(f"refused: {gap}")
        return 1
    # The pod stops at its ceiling whatever happens to the machine that made it, and on
    # any end, since an exit restarts the container and arms a fresh ceiling.
    ceiling = environ["GPUNIT_CEILING"]
    say(f"step: the ceiling, {ceiling}s")
    arm(ceiling, environ)
    try:
        # Checked once armed: an older gpunit sends no nonce, and its pod must stop.
        nonce = environ.get("GPUNIT_NONCE")
        if not nonce:
            raise Refused("GPUNIT_NONCE is unset or empty")
        host_key = sshd(Path.home(), environ["PUBLIC_KEY"])
        # The line the laptop checks the scanned key against; the nonce marks it boot's.
        print(f"gpunit host key {nonce}: {_fingerprint(host_key)}", flush=True)
        time.sleep(KEY_GAP_S)
        code = run(command, environ)
        # The ceiling and a refusal stop without it: neither reaches this line.
        time.sleep(GRACE_S)
    except Refused as gap:
        say(f"refused: {gap}")
        code = 1
    finally:
        stop(environ)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
