"""The laptop's half of the boot contract: the pod's env, and the lines it prints."""

import re

from gpunit.spec import Spec

# Only a whole line counts, so nothing logged later can echo a key line in. The nonce
# is the session's, so a command's echo cannot match it: 0009 design D3.
_HOST_KEY = re.compile(r"^gpunit host key ([0-9a-f]{32}): (SHA256:[A-Za-z0-9+/]+)\s*$")
# What a boot.sh older than v0.6.0 prints: the key line with no nonce.
_OLD_KEY = re.compile(r"^gpunit host key: SHA256:[A-Za-z0-9+/]+\s*$")
# Boot says this after its key line, before the command starts; see 0006 design D1.
_BOOT_STEP = re.compile(r"^\S+ step: the command\s*$")
# Boot's first line: a read that opens with it holds the log from its start.
_BOOT_START = re.compile(r"^\S+ step: the ceiling, \d+s\s*$")


def pod_env(
    spec: Spec, pubkey: str, ceiling_s: int, nonce: str, *, volume_path: str
) -> dict[str, str]:
    """Return the pod's environment: the spec's, then gpunit's own names, which win.

    e.g. a spec with `[env] A = "1"` and no volume → {"A": "1", "PUBLIC_KEY": …,
    "GPUNIT_CEILING": "3600", "GPUNIT_NONCE": …}
    """
    env = {
        **spec.env,
        "PUBLIC_KEY": pubkey,
        "GPUNIT_CEILING": str(ceiling_s),
        "GPUNIT_NONCE": nonce,
    }
    if spec.volume is not None:
        # The pod reads its volume in gpunit's words, not the provider's (0004 D7).
        env |= {"GPUNIT_VOLUME_ID": spec.volume, "GPUNIT_VOLUME_PATH": volume_path}
    return env


def fingerprint(lines: list[str], nonce: str) -> str | None:
    """Return the last fingerprint printed with `nonce` before boot's command, or None.

    e.g. ["gpunit host key <nonce>: SHA256:abc", "<UTC> step: the command"]
        → "SHA256:abc"
    """
    # The last boot wins: a restarted container prints a new key.
    pending = accepted = None
    for line in lines:
        if (match := _HOST_KEY.match(line)) and match[1] == nonce:
            pending = match[2]
        elif _BOOT_STEP.match(line):
            accepted = pending
    return accepted


def old_boot(lines: list[str]) -> bool:
    """Return True when a read from boot's first line holds an old key, then a step.

    e.g. ["<UTC> step: the ceiling, 3600s", "gpunit host key: SHA256:abc",
    "<UTC> step: the command"] → True
    """
    # A read cut before boot's lines judges nothing: 0011 design D8.
    if not lines or not _BOOT_START.match(lines[0]):
        return False
    keyed = False
    for line in lines:
        if _OLD_KEY.match(line):
            keyed = True
        elif keyed and _BOOT_STEP.match(line):
            return True
    return False
