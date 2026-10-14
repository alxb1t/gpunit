# Tasks — 0009 paydown

The dead-pod rule, the kept log, the nonce and the grace, the drift, the live proof's script, the handover, then the
images and the metered runs, per [design](design.md). Every new test carries `@pytest.mark.spec` with the key its task
names.

## Progress

- [x] 1 — The wait
- [x] 2 — The log
- [x] 3 — The boot
- [x] 4 — The drift
- [x] 5 — The proof
- [ ] 6 — The handover
- [ ] 7 — ⚠️ **HUMAN** — the images
- [ ] 8 — ⚠️ **HUMAN · METERED** — make live, make live-dead, make live-serve, make live-serve-dead

## 1 — The wait

- [x] 1.1 **HALT CHECK** — none of this change's fixes exists yet, and every card it closes is still in the backlog.
  Verify: `grep -c -E 'class DeadPod|GPUNIT_NONCE|pod\.log' gpunit/lifecycle.py boot/boot.sh gpunit/serve/session.py | grep -v ':0$' | wc -l | tr -d ' '` prints `0`, and `grep -c -E '^- \*\*(0006·S1|0007·R6|0007·R7|0008·R5) ' .minions/backlog.md` prints `4`.
- [x] 1.2 Add `DeadPod` to `gpunit/lifecycle.py` and make `_wait`'s `mapped()` use it, per [D1](design.md#d1).
  Verify: `grep -c '^class DeadPod' gpunit/lifecycle.py` prints `1`, and `uv run pytest -q tests/test_up.py` exits 0.
- [x] 1.3 In `gpunit/serve/session.py`, make `_wait` and `_hold` read the pod's status each poll and refuse on `DeadPod.seen`, per [D1](design.md#d1); in `tests/test_serve_session.py` bind `serve:wait:dead-pod-ends-the-wait`, `serve:wait:running-pod-waits` and `serve:api:dead-pod-ends-the-hold`.
  Verify: `grep -c -E 'the pod stopped while (the model loaded|serving)' gpunit/serve/session.py` prints `2`, and `grep -o -E 'serve:(wait:dead-pod-ends-the-wait|wait:running-pod-waits|api:dead-pod-ends-the-hold)' tests/test_serve_session.py | sort -u | wc -l | tr -d ' '` prints `3`.

## 2 — The log

- [x] 2.1 In `gpunit/serve/session.py`, add `_Kept`, remove the last session's `pod.log`, read the log since the create in `_wait`'s tick and each `_hold` poll, and print the kept tail before a dead-pod refusal, per [D2](design.md#d2).
  Verify: `grep -c '^class _Kept' gpunit/serve/session.py` prints `1`, and `grep -c "the pod's log is kept at" gpunit/serve/session.py` prints `1`.
- [x] 2.2 In `tests/test_serve_session.py`, move `test_a_model_that_never_answers_is_refused_and_torn_down` to the since-read, bind `serve:wait:log-kept`, and assert the `pod:` lines in the dead-pod tests of 1.3.
  Verify: `grep -c 'serve:wait:log-kept' tests/test_serve_session.py` prints `1`, and `uv run pytest -q tests/test_serve_session.py` exits 0.

## 3 — The boot

- [x] 3.1 In `boot/boot.sh`, require `GPUNIT_NONCE`, print it in the key line, keep it from the command, and sleep `GRACE_S` after the command exits, per [D3](design.md#d3) and [D4](design.md#d4).
  Verify: `grep -c '^GRACE_S=60' boot/boot.sh` prints `1`, and `grep -c 'env -u RUNPOD_API_KEY -u GPUNIT_NONCE' boot/boot.sh` prints `1`.
- [x] 3.2 In `gpunit/provider.py`, `gpunit/runpod.py` and `gpunit/lifecycle.py`, add the nonce to `fingerprint`, `Provider.create`, `RunPod.create` and `up`, add `old_boot`, and refuse an older `boot.sh` in `_verify_host_key`, per [D3](design.md#d3).
  Verify: `grep -c '^def old_boot' gpunit/provider.py` prints `1`, and `grep -c 'GPUNIT_NONCE' gpunit/runpod.py` prints `1`.
- [x] 3.3 Carry the nonce into `tests/fakes.py`, `tests/conftest.py` (`lifecycle.NONCE` replaced), `tests/test_cli.py` (`ON_THE_FAKES`), `tests/fixtures/log.txt`, `tests/test_runpod.py` and `tests/test_boot.py`; in `tests/test_boot.py` keep the grace out of the stop's waits and bind `boot:refuse:no-nonce`, `boot:stop:refusal-no-grace` and `boot:child:no-nonce`; in `tests/test_hostkey.py` bind `session:hostkey:other-nonce-ignored`, `session:hostkey:nonce-per-pod` and `session:hostkey:old-boot-refused`.
  Verify: `grep -o -E 'boot:(refuse:no-nonce|stop:refusal-no-grace|child:no-nonce)' tests/test_boot.py | sort -u | wc -l | tr -d ' '` prints `3`, `grep -o -E 'session:hostkey:(other-nonce-ignored|nonce-per-pod|old-boot-refused)' tests/test_hostkey.py | sort -u | wc -l | tr -d ' '` prints `3`, and `uv run pytest -q tests/test_boot.py tests/test_hostkey.py tests/test_runpod.py tests/test_up.py tests/test_library.py tests/test_run.py tests/test_serve_session.py` exits 0.

## 4 — The drift

- [x] 4.1 Make `README.md`'s exit row for `2` read "`spend --days` under 1 or over 3660", per [D5](design.md#d5).
  Verify: `grep -c 'under 1 or over 3660 |' README.md` prints `1`.
- [x] 4.2 Retag `tests/test_spend.py`'s ledger test with `spend:report:unreadable-ledger-fails`, and make `spend`'s docstring in `gpunit/spend.py` name the ledger, per [D5](design.md#d5).
  Verify: `grep -c 'spend:report:unreadable-ledger-fails' tests/test_spend.py` prints `1`, and `grep -c 'the billing or the ledger cannot be read' gpunit/spend.py` prints `1`.

## 5 — The proof

- [x] 5.1 Write `live/serve_dead.py` with its `check`, and `tests/test_serve_dead.py` binding `check` under `serve:wait:dead-pod-ends-the-wait`, per [D7](design.md#d7).
  Verify: `grep -c '^def check' live/serve_dead.py` prints `1`, and `uv run pytest -q tests/test_serve_dead.py` exits 0.
- [x] 5.2 Add `live-serve-dead` to the `Makefile`'s targets and its `.PHONY`, per [D7](design.md#d7).
  Verify: `make -n live-serve-dead | grep -c 'serve_dead.py'` prints a number of at least `1`.

## 6 — The handover

- [ ] 6.1 In `README.md`, make step 2's `ADD` line name `v0.6.0` and say an older `boot.sh` is refused; in *Serve a model* name `pod.log`, the dead-pod refusal and boot's 60 s grace; name `make live-serve-dead` beside the other live runs.
  Verify: `grep -c 'gpunit/v0.6.0/boot/boot.sh' README.md` prints `1`, `grep -c 'pod.log' README.md` prints a number of at least `1`, and `grep -c 'live-serve-dead' README.md` prints a number of at least `1`.
- [ ] 6.2 Add `make live-serve-dead` to `CLAUDE.md`'s invariant on the live runs.
  Verify: `grep -c 'make live-serve-dead' CLAUDE.md` prints `1`.

## 7 — ⚠️ **HUMAN** — the images

- [ ] 7.1 **HUMAN** — run `.github/workflows/build-serve-image.yml` with the tag `v0.6-rc1`, and write its digest into `gpunit/serve/models.toml`'s `image` line, per [D8](design.md#d8).
  Verify: `grep -c '8e75d9e846eb9d88c8137b3f83a06b7c351aed6ce5522002917ae804a740a49e' gpunit/serve/models.toml` prints `0`.
- [ ] 7.2 **HUMAN** — build `live/Dockerfile` and `live/Dockerfile.dead` for `linux/amd64` from the repository root, push them as `ghcr.io/alxb1t/gpunit-live` and `ghcr.io/alxb1t/gpunit-live-dead`, and write their digests into `live/gpunit.toml` and `live/gpunit.dead.toml`, per [D8](design.md#d8).
  Verify: `grep -c '29b07f3b0a06b59d6e5a870d32fa4590165f98195a018be81c5fbd9a1d4e946e' live/gpunit.toml` prints `0`, and `grep -c 'c30b3cdad7f149b1d3ca5f3f7c33fa19fc23880cc4f070fe2210da562d8a117f' live/gpunit.dead.toml` prints `0`.

## 8 — ⚠️ **HUMAN · METERED** — make live, make live-dead, make live-serve, make live-serve-dead

- [ ] 8.1 **HUMAN · METERED** — with `RUNPOD_API_KEY` set, run `make live`, `make live-dead`, `make live-serve` and `make live-serve-dead`; confirm through the RunPod console that no pod is left; append the tails of `make live` and `make live-dead` to `live/last_run.txt`, and those of `make live-serve` and `make live-serve-dead` to `live/serve_last_run.txt`, each under a header `<date> — make <target>, 0009-paydown`, per [D7](design.md#d7). A failed `check` in `make live-serve-dead` is a halt: say so and keep its lines.
  Verify: `grep -c '^2026-.*0009-paydown' live/last_run.txt` prints `2`, `grep -c '^2026-.*0009-paydown' live/serve_last_run.txt` prints `2`, and `grep -c 'refused: the pod stopped while the model loaded' live/serve_last_run.txt` prints a number of at least `1`.
