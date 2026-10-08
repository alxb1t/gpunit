# Tasks — 0003 consumer-fit

The interrupt's teardown, the host-key read, the boot, the README, then the one metered proof, per
[design](design.md). Every new test carries `@pytest.mark.spec` with the key its task names.

## Progress

- [x] 1 — The interrupt
- [x] 2 — The host-key read
- [x] 3 — The boot
- [ ] 4 — The handover
- [ ] 5 — ⚠️ **HUMAN · METERED** — make live

## 1 — The interrupt

- [x] 1.1 **HALT CHECK** — none of this change's fixes is built yet.
  Verify: `cat gpunit/*.py boot/boot.sh | grep -c -E 'env -u RUNPOD_API_KEY|no create began|cannot stop this pod|since: str'` prints `0`.
- [x] 1.2 In `gpunit/run.py`, tear down in `_run`'s `finally` only when a create began, per [D1](design.md#d1); in `tests/test_run.py` bind `run:teardown:interrupt-before-create` to a `FakeProvider` whose `gpu()` sends `SIGINT`.
  Verify: `grep -c 'no create began' gpunit/run.py` prints `1`, and `grep -c 'run:teardown:interrupt-before-create' tests/test_run.py` prints `1`.

## 2 — The host-key read

- [x] 2.1 Add `since` to `Provider.log` in `gpunit/provider.py`, to `RunPod.log` in `gpunit/runpod.py` and to `FakeProvider.log` in `tests/fakes.py`, per [D2](design.md#d2); in `tests/test_runpod.py` assert a `since` read queries `since=<since>&source=container` and sends no `tail`.
  Verify: `grep -c 'since: str | None = None' gpunit/provider.py gpunit/runpod.py tests/fakes.py` prints `1` for each file.
- [x] 2.2 In `gpunit/session.py`, stamp `created` before `_create` and read the log again from it when the tail holds no key, per [D2](design.md#d2); in `tests/test_hostkey.py` bind `session:hostkey:since-fallback`.
  Verify: `grep -c 'since=record.created' gpunit/session.py` prints `1`, and `grep -c 'session:hostkey:since-fallback' tests/test_hostkey.py` prints `1`.

## 3 — The boot

- [x] 3.1 In `boot/boot.sh`, refuse without `env` and run the command under `env -u RUNPOD_API_KEY`, per [D3](design.md#d3); in `tests/test_boot.py` add `test_no_env_refuses` bound to `boot:refuse:no-env`, and a test bound to `boot:child:no-key`.
  Verify: `grep -c 'env -u RUNPOD_API_KEY "\$@" &' boot/boot.sh` prints `1`, and `grep -c -E 'boot:(refuse:no-env|child:no-key)' tests/test_boot.py` prints `2`.
- [x] 3.2 In `boot/boot.sh`'s `stop()`, name the key on a 401 and on a 403, and keep retrying, per [D4](design.md#d4); in `tests/test_boot.py` bind `boot:stop:refused-key-named` to `CURL_CODES` of `401`, `403`, `200`.
  Verify: `grep -c 'the key cannot stop this pod' boot/boot.sh` prints `1`, and `grep -c 'boot:stop:refused-key-named' tests/test_boot.py` prints `1`.

## 4 — The handover

- [ ] 4.1 In `README.md`, name coreutils' `env` in step 2, say in step 3 that the command on the pod does not see `RUNPOD_API_KEY`, and pin `v0.1.2` in the `ADD` URL and `uv add`, per [D5](design.md#d5).
  Verify: `grep -c 'v0.1.1' README.md` prints `0`, and `grep -c 'coreutils' README.md` prints a number of at least `1`.

## 5 — ⚠️ **HUMAN · METERED** — make live

- [ ] 5.1 **HUMAN · METERED** — rebuild `live/Dockerfile` for `linux/amd64` from the repository root, push `ghcr.io/alxb1t/gpunit-live`, write its new digest into `live/gpunit.toml`, run `make live` with `RUNPOD_API_KEY` set, confirm with `gpunit status --spec live/gpunit.toml` and the RunPod console that no pod is left, and append the run's tail to `live/last_run.txt` under a header `<date> — make live, 0003-consumer-fit`, per [D7](design.md#d7).
  Verify: `git diff main -- live/gpunit.toml | grep -c '^+image = '` prints `1`, and `grep -c '^2026-.*0003-consumer-fit' live/last_run.txt` prints a number of at least `1`.
