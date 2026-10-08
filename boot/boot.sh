#!/usr/bin/env bash
# The pod's half of a gpunit session: arm the ceiling, serve sshd on a fresh host
# key, print its fingerprint, run the command, and stop the pod however it ends.
# Why each step: openspec 0001-core design D11.
#
#   ENTRYPOINT ["/opt/gpunit/boot.sh", "--"]

set -uo pipefail

API="https://api.runpod.io/v2"
RETRY_S=30
MAX_RETRY_S=300

say() { echo "$(date -u +%FT%TZ) $*" >&2; }
refuse() { say "refused: $*"; exit 1; }

# A stop that gave up would leave the pod billing, so it retries until RunPod
# answers 200. The key reaches curl on a file descriptor, never on its argv.
stop() {
  local code wait_s=$RETRY_S
  while :; do
    code=$(curl -s --max-time 30 -o /dev/null -w '%{http_code}' -X POST \
      -H @<(printf 'Authorization: Bearer %s\n' "$RUNPOD_API_KEY") \
      -H "Content-Type: application/json" \
      -d '{"action":"stop"}' "$API/pods/$RUNPOD_POD_ID/action") || true
    if [ "$code" = "200" ]; then
      say "the pod is stopping"
      return 0
    fi
    say "the stop answered HTTP ${code:-000}; trying again in ${wait_s}s"
    sleep "$wait_s"
    wait_s=$((wait_s * 2 < MAX_RETRY_S ? wait_s * 2 : MAX_RETRY_S))
  done
}

# 1. Check: nothing is armed yet, so a refusal here stops nothing.
[ "${1:-}" = "--" ] && shift
command -v sshd >/dev/null || refuse "sshd is not on PATH; install openssh-server in the image"
# Without curl every stop fails, and the ceiling would retry while the pod bills.
command -v curl >/dev/null || refuse "curl is not on PATH; install curl in the image"
for name in RUNPOD_API_KEY RUNPOD_POD_ID PUBLIC_KEY GPUNIT_CEILING; do
  [ -n "${!name:-}" ] || refuse "$name is unset or empty"
done
[[ "$GPUNIT_CEILING" =~ ^[0-9]+$ ]] || refuse "GPUNIT_CEILING is not a number of seconds"
[ $# -gt 0 ] || refuse "no command after --; use boot.sh -- <command>"

# 2. Arm: the pod stops at its ceiling whatever happens to the machine that made it,
#    and on any exit, since an exit restarts the container and arms a fresh ceiling.
say "step: the ceiling, ${GPUNIT_CEILING}s"
(
  sleep "$GPUNIT_CEILING"
  say "the ceiling of ${GPUNIT_CEILING}s is reached"
  stop
) &
trap stop EXIT

# 3. sshd: the session's key alone, and a host key made on this pod at each boot,
#    in a new directory: never one the image baked in, as openssh-server's install does.
say "step: sshd"
mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"
(umask 077 && printf '%s\n' "$PUBLIC_KEY" > "$HOME/.ssh/authorized_keys")
chmod 600 "$HOME/.ssh/authorized_keys"
mkdir -p /run/sshd 2>/dev/null
SSHD_DIR="$(mktemp -d)" || refuse "sshd's directory could not be made"
HOST_KEY="$SSHD_DIR/ssh_host_ed25519_key"
ssh-keygen -q -t ed25519 -N '' -f "$HOST_KEY" || refuse "the host key could not be made"
# sshd's config is boot's own, not the image's: HostKey is a list, so a key the image's
# sshd_config names would be served beside the fresh one, and -o HostKey only adds.
# UsePAM: without it, sshd refuses a root whose password is locked with `!`.
# AllowUsers: root alone, so a key the image baked in for another account is not served.
cat > "$SSHD_DIR/sshd_config" <<EOF || refuse "sshd's config could not be written"
HostKey "$HOST_KEY"
PermitRootLogin prohibit-password
AuthorizedKeysFile .ssh/authorized_keys
PasswordAuthentication no
KbdInteractiveAuthentication no
UsePAM yes
AllowUsers root
Subsystem sftp internal-sftp
EOF
# sshd re-execs itself, so it is started by its absolute path.
"$(command -v sshd)" -f "$SSHD_DIR/sshd_config" || refuse "sshd did not start"

# 4. Print: the line the laptop checks the scanned key against, over the API's log.
echo "gpunit host key: $(ssh-keygen -lf "$HOST_KEY.pub" | awk '{print $2}')"

# 5. Run: the command as a child, so a SIGTERM reaches it and its code is ours.
say "step: the command"
"$@" &
child=$!
trap 'kill -TERM "$child" 2>/dev/null' TERM
wait "$child"
code=$?
# A trapped signal ends `wait` early; wait again for the child's own end.
while kill -0 "$child" 2>/dev/null; do
  wait "$child"
  code=$?
done
say "the command exited $code"
exit "$code"
