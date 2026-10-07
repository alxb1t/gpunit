# Tasks — 0001 core

The package, then the provider, the session, `run`, the boot, the handover, and the one metered proof, per
[design](design.md). Every new test carries `@pytest.mark.spec` with the key its task names.

## Progress

- [ ] 1 — The skeleton
- [ ] 2 — The provider
- [ ] 3 — The session
- [ ] 4 — Run and ssh
- [ ] 5 — The boot
- [ ] 6 — The handover
- [ ] 7 — ⚠️ **HUMAN · METERED** — make live

## 1 — The skeleton

- [ ] 1.1 **HALT CHECK** — the repo holds the bootstrap alone, and `uv`, `openspec`, `ssh-keygen` are on `PATH`.
  Verify: `ls pyproject.toml gpunit 2>&1 | grep -c 'No such file'` prints `2`, and `command -v uv openspec ssh-keygen | wc -l` prints `3`.
- [ ] 1.2 Write `pyproject.toml` per [D1](design.md#d1): hatchling, `requires-python = ">=3.11"`, no dependencies, the `dev` group from [Dependencies](design.md#dependencies), `[project.scripts] gpunit = "gpunit.cli:main"`, ruff's `select`, the `spec` marker; then `uv sync` to write `uv.lock`.
  Verify: `grep -c '^dependencies = \[\]' pyproject.toml` prints `1`, and `uv run python -c 'import tomllib'` exits 0.
- [ ] 1.3 Write `gpunit/__init__.py`, `__main__.py`, `log.py` and `cli.py` with the parser for `up`, `status`, `down`, `ssh`, `run -- <cmd>` and `--spec`, each verb a stub that exits `2` for usage faults per [D12](design.md#d12); tests in `tests/test_cli.py` for `cli:verbs:unknown-verb-exits-2` and `cli:verbs:run-without-command-exits-2`.
  Verify: `uv run gpunit frobnicate; echo $?` prints `2`, and `grep -c 'cli:verbs:' tests/test_cli.py` prints `2`.
- [ ] 1.4 Write `gpunit/spec.py` per [D4](design.md#d4) and `tests/test_spec.py` binding every `spec:file:*`, `spec:image:*` and `spec:ceiling:required` scenario.
  Verify: `grep -c 'mark.spec("spec:' tests/test_spec.py` prints `6`.
- [ ] 1.5 Write `gpunit/state.py` per [D5](design.md#d5) and `tests/test_state.py`: the record round-trips, the key files are `0600`.
  Verify: `grep -c '0o600' tests/test_state.py` prints `1`.
- [ ] 1.6 Replace the `gate` recipe in `Makefile` with the commands of [D13](design.md#d13), in that order; add `.gpunit/` and `.venv/` to `.gitignore`.
  Verify: `make -n gate | grep -c 'uv run'` prints `4`, and `make gate` exits 0.

## 2 — The provider

- [ ] 2.1 Write `gpunit/provider.py` per [D2](design.md#d2): the protocol, `GpuInfo`, `VolumeInfo`, `PodInfo`, and the exceptions `Lost`, `Refused`, `Unknown`, `NoImage`.
  Verify: `grep -c '^class ' gpunit/provider.py` prints `8`.
- [ ] 2.2 Write `tests/fixtures/` — `gpu.json`, `volume.json`, `pod_created.json`, `pod_running.json`, `pod_pending.json`, `pods_page.json`, `log.txt`, `problem.json` — in RunPod's v2 shape as [Context](design.md#context) lists it.
  Verify: `ls tests/fixtures | wc -l` prints `8`.
- [ ] 2.3 Write `gpunit/runpod.py` per [D3](design.md#d3) with `urllib`'s opener injectable, and `tests/test_runpod.py` on a fake opener: each verb against its fixture; a 400 create raises `Refused`; a 503, a transport failure and a 201 without an id raise `Lost`; a 404 gpu raises `Unknown`; a listed pod with no image raises `NoImage`; the log's last fingerprint wins; a cursor answered twice refuses; `RUNPOD_API_KEY` unset refuses at construction (`spec:secrets:no-key-refused`).
  Verify: `grep -c 'def test_' tests/test_runpod.py` prints a number of at least `12`, and `grep -c 'Authorization' gpunit/runpod.py` prints `1`.
- [ ] 2.4 Write `tests/fakes.py`: `FakeProvider` implementing the protocol from scripted answers, recording every call with its arguments.
  Verify: `grep -c 'class FakeProvider' tests/fakes.py` prints `1`.
- [ ] 2.5 Test `spec:secrets:dotenv-ignored`: a `.env` beside the spec with the key set and the variable unset refuses.
  Verify: `grep -l 'spec:secrets:dotenv-ignored' tests/*.py | wc -l` prints `1`.

## 3 — The session

- [ ] 3.1 Write `up` in `gpunit/session.py` per [D7](design.md#d7) and [D8](design.md#d8) with `cli.main(argv, provider=…)` wiring; `tests/test_up.py` binds every `session:one:*`, `session:place:*`, `session:lost:*`, `session:wait:*`, `session:volume:*`, `session:key:fresh-per-session`, `session:create:secure-and-22`, `spec:ceiling:reaches-the-pod` and `cli:exits:refusal-exits-1`, with `ssh-keygen`, `ssh-keyscan` stubbed on `PATH` and the sleeps injectable.
  Verify: `grep -c '@pytest.mark.spec' tests/test_up.py` prints a number of at least `17`.
- [ ] 3.2 Add the host-key verification and `tests/test_hostkey.py` binding `session:hostkey:match-recorded`, `session:hostkey:mismatch-tears-down`, `session:hostkey:no-line-tears-down`.
  Verify: `grep -c 'session:hostkey:' tests/test_hostkey.py` prints `3`.
- [ ] 3.3 Write `down` per [D9](design.md#d9) and `tests/test_down.py` binding every `session:down:*` and `session:key:deleted-at-teardown`.
  Verify: `grep -c 'session:down:' tests/test_down.py` prints `4`.
- [ ] 3.4 Write `status` and `tests/test_status.py` binding `cli:status:json` and `cli:status:no-record`.
  Verify: `grep -c 'cli:status:' tests/test_status.py` prints `2`.

## 4 — Run and ssh

- [ ] 4.1 Write `ssh` in `gpunit/session.py` and bind `session:ssh:uses-record` in `tests/test_ssh.py`, with `os.execvp` injectable.
  Verify: `grep -c 'session:ssh:uses-record' tests/test_ssh.py` prints `1`.
- [ ] 4.2 Write `gpunit/run.py` per [D10](design.md#d10) and `tests/test_run.py` binding every `run:*` scenario but `run:ports:busy-refuses`, and `cli:exits:stdout-is-the-commands`, the tunnel a stub `ssh` on `PATH`, the signals sent to the process under test.
  Verify: `grep -c '@pytest.mark.spec' tests/test_run.py` prints a number of at least `7`.
- [ ] 4.3 Add the busy-port check before any request and the one `up` warning when `.gpunit/` is not gitignored, per [D5](design.md#d5).
  Verify: `grep -c 'run:ports:busy-refuses' tests/test_run.py` prints `1`.

## 5 — The boot

- [ ] 5.1 Write `boot/boot.sh` per [D11](design.md#d11) from isekai's `start.sh:12-32` and `tools/stop_pod.sh`.
  Verify: `bash -n boot/boot.sh` exits 0, and `grep -c 'gpunit host key: ' boot/boot.sh` prints `1`.
- [ ] 5.2 Write `tests/test_boot.py`: `boot.sh` run under `bash` in `tmp_path` with stub `sshd`, `ssh-keygen`, `curl` and `sleep` on `PATH`, binding every `boot:*` scenario.
  Verify: `grep -c '@pytest.mark.spec("boot:' tests/test_boot.py` prints `8`.

## 6 — The handover

- [ ] 6.1 Write `README.md`: what gpunit is, the consumer's steps (`gpunit.toml`, the Dockerfile lines of [D11](design.md#d11), `uv add --dev … && uv run gpunit run -- …`), the verbs and exit codes, the spend rules, `make live`.
  Verify: `grep -c 'ADD --checksum' README.md` prints `1`, and `grep -c 'gpunit run --' README.md` prints a number of at least `1`.
- [ ] 6.2 Rewrite `CLAUDE.md`'s *Layout* for the package of [D1](design.md#d1) and its gate line for [D13](design.md#d13); add the invariants: no runtime dependency, the key never on argv, the ceiling required, a 404 never gone, `make live` never in CI.
  Verify: `grep -c 'no code yet' CLAUDE.md` prints `0`, and `grep -c 'make live' CLAUDE.md` prints `1`.

## 7 — ⚠️ **HUMAN · METERED** — make live

- [ ] 7.1 Write `live/Dockerfile` and `live/gpunit.toml` per [D14](design.md#d14), and the `live` recipe in `Makefile` that prints the price and the maximum before `gpunit run`.
  Verify: `grep -c 'ceiling = "10m"' live/gpunit.toml` prints `1`, and `make -n live | grep -c 'gpunit run'` prints `1`.
- [ ] 7.2 **HUMAN · METERED** — build and push `ghcr.io/alxb1t/gpunit-live` for `linux/amd64`, write its digest into `live/gpunit.toml`, run `make live` with `RUNPOD_API_KEY` set, confirm with `gpunit status` and the RunPod console that no pod is left, and append the run's last lines with the date to `live/last_run.txt`.
  Verify: `grep -c '@sha256:' live/gpunit.toml` prints `1`, and `grep -c 'NVIDIA-SMI' live/last_run.txt` prints a number of at least `1`.
