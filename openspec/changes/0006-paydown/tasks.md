# Tasks — 0006 paydown

The host key, the `serve` fixes, the wait, the handover, then the metered proof of the dead path, per
[design](design.md). Every new test carries `@pytest.mark.spec` with the key its task names.

## Progress

- [x] 1 — The host key
- [x] 2 — Serve
- [x] 3 — The wait
- [ ] 4 — The handover
- [ ] 5 — ⚠️ **HUMAN · METERED** — make live-dead, make live

## 1 — The host key

- [x] 1.1 **HALT CHECK** — none of this change's fixes exists yet, and every card it closes is still in the backlog.
  Verify: `grep -c -E '_BOOT_STEP|DEAD = |local_port' gpunit/provider.py gpunit/lifecycle.py gpunit/serve/table.py | grep -v ':0$' | wc -l | tr -d ' '` prints `0`, and `grep -c -E '^- \*\*(0003·(R2|R3|R4|R5|S2)|0005·(R2|R3|R4|R5|R6|R7|R8|R9|R10)) ' .minions/backlog.md` prints `14`.
- [x] 1.2 In `gpunit/provider.py`, make `fingerprint` accept a key line only when boot's step line follows it, per [D1](design.md#d1); add `STEP_LINE` to `tests/fakes.py` and give `FakeProvider`'s default `logs` the key line then the step line.
  Verify: `grep -c '^_BOOT_STEP' gpunit/provider.py` prints `1`, and `grep -c 'STEP_LINE' tests/fakes.py` prints a number of at least `2`.
- [x] 1.3 Add the step line to the log lines of `tests/test_hostkey.py`, `tests/test_runpod.py`, `tests/test_library.py`, `tests/test_up.py` and `tests/test_serve_session.py`, and in `tests/test_hostkey.py` bind `session:hostkey:echoed-line-is-ignored` and `session:hostkey:key-without-step-waits`.
  Verify: `grep -c -E 'session:hostkey:(echoed-line-is-ignored|key-without-step-waits)' tests/test_hostkey.py` prints `2`, and `uv run pytest -q tests/test_hostkey.py tests/test_runpod.py tests/test_library.py tests/test_up.py tests/test_serve_session.py` exits 0.
- [x] 1.4 Reword `boot/boot.sh`'s step-5 comment and `gpunit/state.py`'s docstring, per [D4](design.md#d4).
  Verify: `grep -c 'never sees it' boot/boot.sh` prints `0`, and `grep -c 'working directory' gpunit/state.py` prints `0`.

## 2 — Serve

- [x] 2.1 Give `Row.spec` a `local_port` in `gpunit/serve/table.py`, pick a free one in `serve` before the price, pass `PORT` from `down`, and cut `NVIDIA RTX A4500` from `gpunit/serve/models.toml`, per [D3](design.md#d3); update `tests/test_serve_table.py` and bind `serve:wait:busy-local-port-is-skipped` in `tests/test_serve_session.py`.
  Verify: `grep -c 'A4500' gpunit/serve/models.toml` prints `0`, and `grep -c 'serve:wait:busy-local-port-is-skipped' tests/test_serve_session.py` prints `1`.
- [x] 2.2 Make `_agree` say `not rented` on `KeyboardInterrupt` and re-raise it, and `outcome` in `gpunit/run.py` return `130` for it, per [D3](design.md#d3); in `tests/test_serve_session.py` bind `serve:price:interrupt-is-no` and `cli:exits:serve-signal-is-128-plus-n`.
  Verify: `grep -c 'except KeyboardInterrupt' gpunit/run.py` prints `1`, and `grep -c -E 'serve:price:interrupt-is-no|cli:exits:serve-signal-is-128-plus-n' tests/test_serve_session.py` prints `2`.
- [x] 2.3 In `gpunit/serve/chat.py`, end the chat with `log.refuse` when a request cannot connect and keep dropping the turn on an HTTP error, per [D3](design.md#d3); in `tests/test_serve_chat.py` bind `serve:chat:stopped-server-ends` and `serve:chat:server-error-drops-the-turn`.
  Verify: `grep -c 'the server stopped answering' gpunit/serve/chat.py` prints `1`, and `grep -c -E 'serve:chat:(stopped-server-ends|server-error-drops-the-turn)' tests/test_serve_chat.py` prints `2`.

## 3 — The wait

- [x] 3.1 In `gpunit/lifecycle.py`, add `DEAD` and make `_wait` tear down on two terminal polls in a row, per [D2](design.md#d2); in `tests/test_up.py` bind `session:wait:dead-pod-tears-down` and `session:wait:one-dead-poll-is-not-yet`.
  Verify: `grep -c '^DEAD = ' gpunit/lifecycle.py` prints `1`, and `grep -c -E 'session:wait:(dead-pod-tears-down|one-dead-poll-is-not-yet)' tests/test_up.py` prints `2`.

## 4 — The handover

- [ ] 4.1 Add the patch rule to `CLAUDE.md`'s *Invariants*, per [D5](design.md#d5).
  Verify: `grep -c 'A patch closes cards and fixes' CLAUDE.md` prints `1`.
- [ ] 4.2 Correct README's serve diagram and its two `live-serve` figures, the `live-serve` comment in the `Makefile`, and make `live/price.py` count `ceiling + timeout` and take an optional spec path, per [D4](design.md#d4).
  Verify: `grep -c 'or the ceiling' README.md` prints `0`, and `grep -c 'spec.timeout_s' live/price.py` prints `1`.
- [ ] 4.3 Write `live/Dockerfile.dead`, `live/gpunit.dead.toml` and the `live-dead` target of the `Makefile`, per [D6](design.md#d6).
  Verify: `grep -c -E 'install .*curl' live/Dockerfile.dead` prints `0`, and `make -n live-dead | grep -c 'gpunit.dead.toml'` prints a number of at least `1`.

## 5 — ⚠️ **HUMAN · METERED** — make live-dead, make live

- [ ] 5.1 **HUMAN · METERED** — build `live/Dockerfile.dead` for `linux/amd64` from the repository root, push it as `ghcr.io/alxb1t/gpunit-live-dead`, and write its digest into `live/gpunit.dead.toml`, per [D6](design.md#d6).
  Verify: `grep -c '@sha256:0000' live/gpunit.dead.toml` prints `0`.
- [ ] 5.2 **HUMAN · METERED** — run `make live-dead`, then `make live`, with `RUNPOD_API_KEY` set; confirm through the RunPod console that no pod is left; append both tails to `live/last_run.txt` under a header `<date> — make live-dead, 0006-paydown` and `<date> — make live, 0006-paydown`. If `make live-dead` ends at its `timeout` with no `EXITED`, `ERROR` or `TERMINATED` line, halt and say so: the abort is unproven.
  Verify: `grep -c -E 'is (EXITED|ERROR|TERMINATED): the container is not running' live/last_run.txt` prints a number of at least `1`, and `grep -c '^2026-.*0006-paydown' live/last_run.txt` prints `2`.
