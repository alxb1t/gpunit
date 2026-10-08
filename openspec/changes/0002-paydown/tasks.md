# Tasks — 0002 paydown

The ssh line, the provider, `run`, the boot, the README, then the one metered proof, per [design](design.md).
Every new test carries `@pytest.mark.spec` with the key its task names.

## Progress

- [x] 1 — The ssh line
- [x] 2 — The provider
- [x] 3 — Run
- [x] 4 — The boot
- [x] 5 — The handover
- [ ] 6 — ⚠️ **HUMAN · METERED** — make live

## 1 — The ssh line

- [x] 1.1 **HALT CHECK** — none of this change's fixes is built yet.
  Verify: `cat gpunit/*.py boot/boot.sh | grep -c -E 'IdentitiesOnly|UsePAM|_NoRedirect|LOG_IDLE_S|_Backoff'` prints `0`.
- [x] 1.2 In `gpunit/session.py`, open `ssh_command`'s argv with `-F none -o IdentitiesOnly=yes` per [D1](design.md#d1); in `tests/test_ssh.py` add a test bound to `session:ssh:own-config-only`, and in `tests/test_run.py` add that mark and asserts for `-F none` and `IdentitiesOnly=yes` on `opened[0]` to `test_a_dead_tunnel_is_reopened`.
  Verify: `grep -c 'session:ssh:own-config-only' tests/test_ssh.py tests/test_run.py` prints `1` for each file, and `uv run pytest -q tests/test_ssh.py tests/test_run.py` exits 0.
- [x] 1.3 In `gpunit/session.py`, check `ssh`, `ssh-keygen` and `ssh-keyscan` in `up`, and refuse on the exec's `OSError` in `ssh()`, per [D2](design.md#d2); rewrite the comment at `gpunit/cli.py:95`. Update `test_no_ssh_keygen_refuses_before_any_request` in `tests/test_up.py` for the new message; add `session:tools:missing-refuses` there (a `PATH` of stubs for `ssh` and `ssh-keygen` alone) and `session:ssh:no-ssh-refuses` in `tests/test_ssh.py` (an `execvp` that raises `FileNotFoundError`).
  Verify: `grep -c 'reached only when the exec failed' gpunit/cli.py` prints `0`, and `grep -c -E 'session:(tools:missing-refuses|ssh:no-ssh-refuses)' tests/test_up.py tests/test_ssh.py` prints `1` for each file.
- [x] 1.4 In `gpunit/spec.py`, refuse a port outside 1–65535 in `_port` per [D3](design.md#d3); in `tests/test_spec.py` bind `spec:file:port-out-of-range` to `ports = [70000]` and to `{ remote = 8188, local = 0 }`.
  Verify: `grep -c '65535' gpunit/spec.py` prints a number of at least `1`, and `grep -c 'spec:file:port-out-of-range' tests/test_spec.py` prints a number of at least `1`.

## 2 — The provider

- [x] 2.1 In `gpunit/runpod.py`, add `_NoRedirect` and build the default opener with it per [D4](design.md#d4); in `tests/test_runpod.py` bind `spec:secrets:redirect-not-followed` to the opener's handler, `redirect_request` answering `None`, and a scripted 302 on create raising `Lost`.
  Verify: `grep -c 'build_opener(_NoRedirect)' gpunit/runpod.py` prints `1`, and `grep -c 'spec:secrets:redirect-not-followed' tests/test_runpod.py` prints a number of at least `1`.
- [x] 2.2 Add `DELETED = (200, 204)` to `gpunit/provider.py`, and use it in `RunPod.delete` and at the recorded pod's and the sweep's delete checks of `down` in `gpunit/session.py`, per [D5](design.md#d5); in `tests/test_down.py` bind `session:down:200-is-success`.
  Verify: `grep -c 'code == 204' gpunit/session.py` prints `0`, and `grep -c 'session:down:200-is-success' tests/test_down.py` prints `1`.
- [x] 2.3 In `gpunit/runpod.py`, add `LOG_IDLE_S = 3` and open the log stream with it per [D6](design.md#d6); in `tests/test_runpod.py` bind `session:hostkey:quiet-stream-ends-read` to a stream that sends an earlier boot's host-key line and this boot's, then raises `TimeoutError`.
  Verify: `grep -c 'timeout=LOG_IDLE_S' gpunit/runpod.py` prints `1`, and `grep -c 'session:hostkey:quiet-stream-ends-read' tests/test_runpod.py` prints `1`.

## 3 — Run

- [x] 3.1 In `gpunit/run.py`, map a negative code from `wait()` to `128 - code` per [D7](design.md#d7); in `tests/test_run.py` bind `run:teardown:signalled-command` to `gpunit run -- bash -c 'kill -9 $$'` exiting `137`.
  Verify: `grep -c 'run:teardown:signalled-command' tests/test_run.py` prints `1`, and `uv run pytest -q tests/test_run.py` exits 0.
- [x] 3.2 In `gpunit/run.py`, add `REOPEN_FIRST_S`, `REOPEN_CAP_S` and `_Backoff`, and reopen the tunnel only when it is due, per [D8](design.md#d8); in `tests/test_run.py` bind `run:tunnel:backoff` to `_Backoff` driven with explicit times, and set `REOPEN_FIRST_S` to `0.1` in `test_a_dead_tunnel_is_reopened`.
  Verify: `grep -c 'class _Backoff' gpunit/run.py` prints `1`, and `grep -c 'run:tunnel:backoff' tests/test_run.py` prints `1`.

## 4 — The boot

- [x] 4.1 Add `UsePAM yes` to boot's sshd config in `boot/boot.sh` per [D9](design.md#d9); in `tests/test_boot.py` bind `boot:sshd:pam-on` to a test that reads the config sshd was started with.
  Verify: `grep -c '^UsePAM yes$' boot/boot.sh` prints `1`, and `grep -c 'boot:sshd:pam-on' tests/test_boot.py` prints `1`.
- [x] 4.2 Split `test_a_missing_tool_refuses` in `tests/test_boot.py` into `test_no_sshd_refuses` and `test_no_curl_refuses` over one helper, per [D10](design.md#d10).
  Verify: `grep -c 'def test_a_missing_tool_refuses' tests/test_boot.py` prints `0`, and `grep -c 'boot:refuse:no-curl' tests/test_boot.py` prints `1`.

## 5 — The handover

- [x] 5.1 In `README.md`, point the design link at the archive, pin `v0.1.1` in the `ADD` URL and `uv add`, add the spend-rule bullet on gpunit's own ssh, and widen the `128+n` row, per [D11](design.md#d11).
  Verify: `grep -c 'v0.1.0' README.md` prints `0`, `grep -c 'changes/archive/0001-core/design.md' README.md` prints a number of at least `1`, and `grep -c 'ssh_config' README.md` prints a number of at least `1`.

## 6 — ⚠️ **HUMAN · METERED** — make live

- [ ] 6.1 **HUMAN · METERED** — rebuild `live/Dockerfile` for `linux/amd64` from the repository root, push `ghcr.io/alxb1t/gpunit-live`, write its new digest into `live/gpunit.toml`, run `make live` with `RUNPOD_API_KEY` set, confirm with `gpunit status --spec live/gpunit.toml` and the RunPod console that no pod is left, and append the run's tail to `live/last_run.txt` under a header `<date> — make live, 0002-paydown`, per [D13](design.md#d13).
  Verify: `git diff main -- live/gpunit.toml | grep -c '^+image = '` prints `1`, and `grep -c '^2026-.*0002' live/last_run.txt` prints a number of at least `1`.
