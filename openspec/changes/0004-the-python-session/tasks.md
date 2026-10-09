# Tasks — 0004 the Python session

The log's sink and the volume's names, the lifecycle's new name, then the library, `run` on top, the README, and the
metered proof, per [design](design.md). Every new test carries `@pytest.mark.spec` with the key its task names.

## Progress

- [x] 1 — The log and the volume's names
- [x] 2 — The lifecycle's name
- [x] 3 — The library
- [ ] 4 — Run on the library
- [ ] 5 — The handover
- [ ] 6 — ⚠️ **HUMAN · METERED** — make live

## 1 — The log and the volume's names

- [x] 1.1 **HALT CHECK** — no library exists yet, and the log writes straight to stderr.
  Verify: `ls gpunit/library.py 2>&1 | grep -c 'No such file'` prints `1`, and `grep -c '_sink' gpunit/log.py` prints `0`.
- [x] 1.2 In `gpunit/log.py`, add the sink, `redirect` and the default sink that swallows a closed stderr, per [D5](design.md#d5); in `tests/test_cli.py` bind `cli:exits:closed-stderr`.
  Verify: `grep -c 'def redirect' gpunit/log.py` prints `1`, and `grep -c 'cli:exits:closed-stderr' tests/test_cli.py` prints `1`.
- [x] 1.3 In `gpunit/runpod.py`, add `GPUNIT_VOLUME_ID` and `GPUNIT_VOLUME_PATH` to the create's environment; in `gpunit/spec.py`, refuse a `GPUNIT_` key in `[env]`; per [D7](design.md#d7). Bind `session:volume:the-pod-is-told` in `tests/test_runpod.py` and `spec:file:env-gpunit-refused` in `tests/test_spec.py`.
  Verify: `grep -c 'GPUNIT_VOLUME_PATH' gpunit/runpod.py` prints `1`, and `grep -c 'spec:file:env-gpunit-refused' tests/test_spec.py` prints `1`.

## 2 — The lifecycle's name

- [x] 2.1 `git mv gpunit/session.py gpunit/lifecycle.py`; import it as `lifecycle` in `gpunit/cli.py`, `gpunit/run.py`, `tests/conftest.py` and `tests/test_ssh.py`; in `CLAUDE.md`'s *Layout*, name `lifecycle.py` for `up · status · down · ssh`; per [D10](design.md#d10).
  Verify: `ls gpunit/session.py 2>&1 | grep -c 'No such file'` prints `1`, `grep -rlE 'from gpunit import .*\bsession\b' gpunit tests | wc -l | tr -d ' '` prints `0`, and `grep -c 'lifecycle.py' CLAUDE.md` prints `1`.

## 3 — The library

- [x] 3.1 Write `gpunit/library.py` per [D1](design.md#d1), [D2](design.md#d2), [D3](design.md#d3) and [D4](design.md#d4), moving `_tunnel`, `_kill`, `_Backoff`, `_refuse_busy_ports`, `TUNNEL_POLL_S`, `REOPEN_FIRST_S` and `REOPEN_CAP_S` from `gpunit/run.py`, which imports them back; repoint the patches and `_Backoff` call in `tests/test_run.py` to `library`.
  Verify: `grep -c 'class _Backoff' gpunit/library.py` prints `1`, and `grep -c 'class _Backoff' gpunit/run.py` prints `0`.
- [x] 3.2 Export `session`, `Session`, `Refused`, `Lost`, `TeardownFailed`, `Interrupted` and `load_spec` from `gpunit/__init__.py`, per [D2](design.md#d2).
  Verify: `uv run python -c 'import gpunit; print(sorted(n for n in ("session","Session","Refused","Lost","TeardownFailed","Interrupted","load_spec") if hasattr(gpunit, n)))'` prints `['Interrupted', 'Lost', 'Refused', 'Session', 'TeardownFailed', 'load_spec', 'session']`.
- [x] 3.3 Write `tests/test_library.py` binding every `library:*` scenario of the change's `library` spec, through `_open` with a `FakeProvider` and the OpenSSH stubs.
  Verify: `grep -o 'library:[a-z-]*:[a-z-]*' tests/test_library.py | sort -u | wc -l | tr -d ' '` prints `13`.

## 4 — Run on the library

- [ ] 4.1 Rewrite `run.run` in `gpunit/run.py` on `library._open`, per [D6](design.md#d6), deleting `_Children`, `_Interrupted` and `_supervise`'s tunnel loop.
  Verify: `grep -c -E 'class _Children|class _Interrupted' gpunit/run.py` prints `0`, and `uv run pytest -q tests/test_run.py` exits 0.

## 5 — The handover

- [ ] 5.1 In `README.md`, add *Use it from Python* and say in *The verbs* that `run` is the same session; in `CLAUDE.md`'s *Layout*, name `library.py`; per [D8](design.md#d8).
  Verify: `grep -c 'Use it from Python' README.md` prints `1`, and `grep -c 'library.py' CLAUDE.md` prints `1`.

## 6 — ⚠️ **HUMAN · METERED** — make live

- [ ] 6.1 **HUMAN · METERED** — run `make live` with `RUNPOD_API_KEY` set on the image `live/gpunit.toml` pins, confirm with `gpunit status --spec live/gpunit.toml` and the RunPod console that no pod is left, and append the run's tail to `live/last_run.txt` under a header `<date> — make live, 0004-the-python-session`, per [D9](design.md#d9).
  Verify: `grep -c '^2026-.*0004-the-python-session' live/last_run.txt` prints a number of at least `1`.
