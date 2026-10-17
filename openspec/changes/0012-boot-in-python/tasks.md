# Tasks — 0012 boot in Python

`boot.py` and its unit tests, the proof that lets `boot.sh` go, the launch, the live scripts and the handover, then the
images and the metered runs, per [design](design.md). Every new test carries `@pytest.mark.spec` with the key its
task names.

## Progress

- [x] 1 — boot.py
- [x] 2 — The proof
- [x] 3 — The launch
- [x] 4 — The live scripts
- [x] 5 — The handover
- [x] 6 — ⚠️ **HUMAN** — the images
- [x] 7 — ⚠️ **HUMAN · METERED** — make live, make live-dead, make live-volume, make live-serve

## 1 — boot.py

- [x] 1.1 **HALT CHECK** — none of this change exists yet, and the card it closes is still in the backlog.
  Verify: `test -e boot/boot.py; echo $?` prints `1`, `test -e serve/launch.py; echo $?` prints `1`, `grep -c 'pytest-cov' pyproject.toml` prints `0`, and `grep -c -E '^- \*\*0011·R4 ' .minions/backlog.md` prints `1`.
- [x] 1.2 Write `boot/boot.py` per [D1](design.md#d1), [D2](design.md#d2), [D3](design.md#d3) and [D4](design.md#d4); add `[tool.ruff] per-file-target-version = { "boot/boot.py" = "py310" }` to `pyproject.toml`, per [D7](design.md#d7).
  Verify: `grep -c -E '^def (main|check|arm|sshd|run|stop)\(' boot/boot.py` prints `6`, `grep -c -E 'curl|import gpunit|from gpunit' boot/boot.py` prints `0`, `grep -c 'per-file-target-version' pyproject.toml` prints `1`, and `uv run ty check --python-version 3.10 boot/boot.py` exits 0.
- [x] 1.3 Write `tests/test_boot_steps.py` per [D5](design.md#d5), binding every key of `openspec/specs/boot/spec.md` and of [the boot delta](specs/boot/spec.md), `boot:stop:own-error` and `boot:file:stdlib-only` among them.
  Verify: `for k in $(grep -o -h -E 'boot:[a-z]+:[a-z0-9-]+' openspec/specs/boot/spec.md openspec/changes/0012-boot-in-python/specs/boot/spec.md | grep -v -x -E 'boot:refuse:no-(curl|env)' | sort -u); do grep -q "\"$k\"" tests/test_boot_steps.py || echo "$k"; done | wc -l | tr -d ' '` prints `0`, and `uv run pytest -q tests/test_boot_steps.py` exits 0.

## 2 — The proof

- [x] 2.1 Run `uv add --dev 'pytest-cov>=7.1,<8'`; add `[tool.coverage.run]` and `[tool.coverage.report]` to `pyproject.toml`, and `.coverage` to `.gitignore`, per [D7](design.md#d7).
  Verify: `grep -c '"pytest-cov>=7.1,<8"' pyproject.toml` prints `1`, `grep -c '^fail_under = 100$' pyproject.toml` prints `1`, `grep -c -x '.coverage' .gitignore` prints `1`, and `uv run pytest -q tests/test_boot_steps.py --cov` exits 0.
- [x] 2.2 In the `Makefile`'s `gate` recipe, `uv run pytest` → `uv run pytest --cov`, and add `uv run ty check --python-version 3.10 boot/boot.py` after `uv run ty check`, per [D7](design.md#d7).
  Verify: `make -n gate | grep -c -x 'uv run pytest --cov'` prints `1`, and `make -n gate | grep -c -x 'uv run ty check --python-version 3.10 boot/boot.py'` prints `1`.
- [x] 2.3 Port `tests/test_boot.py` to run `boot/boot.py` per [D6](design.md#d6), keeping every key it binds and `test_the_commands_end_stops_the_pod`'s name.
  Verify: `grep -c 'boot\.sh' tests/test_boot.py` prints `0`, `for k in $(grep -o -h -E 'boot:[a-z]+:[a-z0-9-]+' openspec/specs/boot/spec.md openspec/changes/0012-boot-in-python/specs/boot/spec.md | grep -v -x -E 'boot:refuse:no-(curl|env)' | sort -u); do grep -q "\"$k\"" tests/test_boot.py || echo "$k"; done | wc -l | tr -d ' '` prints `0`, and `uv run pytest -q tests/test_boot.py` exits 0.
- [x] 2.4 Make `serve/Dockerfile` copy and enter `boot.py` with `ca-certificates` in place of `curl`, its `CMD` unchanged; in `tests/test_serve_image.py`, assert [D2](design.md#d2)'s `ENTRYPOINT`, the `COPY` of `boot.py`, and no `curl` in the install line; per [D8](design.md#d8).
  Verify: `grep -c -E 'boot\.sh|curl' serve/Dockerfile` prints `0`, and `uv run pytest -q tests/test_serve_image.py` exits 0.
- [x] 2.5 Make `live/Dockerfile` and `live/Dockerfile.dead` copy and enter `boot.py`, with the install lines of [D12](design.md#d12), per [D8](design.md#d8).
  Verify: `grep -c -E 'boot\.sh|curl' live/Dockerfile live/Dockerfile.dead | grep -v ':0$' | wc -l | tr -d ' '` prints `0`, `grep 'apt-get install' live/Dockerfile | grep -c -w 'python3'` prints `1`, `grep -c 'python3-minimal' live/Dockerfile` prints `0`, `grep 'apt-get install' live/Dockerfile.dead | grep -c 'python3'` prints `0`, and `grep -c -F 'ENTRYPOINT ["python3", "/opt/gpunit/boot.py", "--"]' live/Dockerfile live/Dockerfile.dead | grep -c ':1$'` prints `2`.
- [x] 2.6 Delete `boot/boot.sh`, per [D8](design.md#d8).
  Verify: `test -e boot/boot.sh; echo $?` prints `1`, and `uv run pytest -q tests/test_boot.py tests/test_boot_steps.py tests/test_serve_image.py` exits 0.

## 3 — The launch

- [x] 3.1 Write `serve/launch.py`, and make it `serve/Dockerfile`'s `COPY` and `CMD`, per [D9](design.md#d9); in `tests/test_serve_image.py`, run it with a stub `vllm` under `serve:volume:weights-on-the-volume`, the twin an empty `GPUNIT_VOLUME_PATH`.
  Verify: `grep -c '"sh", "-c"' serve/Dockerfile` prints `0`, `grep -c -F 'CMD ["python3", "/opt/gpunit/launch.py"]' serve/Dockerfile` prints `1`, and `uv run pytest -q tests/test_serve_image.py` exits 0.

## 4 — The live scripts

- [x] 4.1 Write `live/window.py`, `live/volume.py` and `live/dead.py`, and make the `Makefile`'s `live-volume` and `live-dead` one line each, per [D10](design.md#d10).
  Verify: `make -n live-volume` prints `uv run python live/volume.py`, and `make -n live-dead` prints `uv run python live/dead.py`.
- [x] 4.2 Write `live/serve.py`, move `live-serve-dead`'s window into `live/serve_dead.py` through `live/window.py`, and make the `Makefile`'s `live-serve` and `live-serve-dead` one line each, per [D10](design.md#d10).
  Verify: `make -n live-serve` prints `uv run python live/serve.py qwen3-4b`, `make -n live-serve-dead` prints `uv run python live/serve_dead.py`, and `uv run pytest -q tests/test_serve_dead.py` exits 0.
- [x] 4.3 Write `tests/test_live.py` per [D10](design.md#d10), binding `session:volume:window-mounted`, `session:wait:dead-pod-tears-down`, `serve:api:prints-the-endpoint` and `volume:down:deletes`.
  Verify: `grep -o -E 'session:volume:window-mounted|session:wait:dead-pod-tears-down|serve:api:prints-the-endpoint|volume:down:deletes' tests/test_live.py | sort -u | wc -l | tr -d ' '` prints `4`, and `uv run pytest -q tests/test_live.py` exits 0.

## 5 — The handover

- [x] 5.1 In `README.md`, rewrite step 2 and every present-tense `boot.sh`, per [D14](design.md#d14).
  Verify: `grep -c 'gpunit/v0.8.0/boot/boot.py /opt/gpunit/boot.py' README.md` prints `1`, `grep -c -F 'ENTRYPOINT ["python3", "/opt/gpunit/boot.py", "--"]' README.md` prints `1`, and `grep 'boot\.sh' README.md | grep -c -v -E 'v0\.6\.0|v0\.7\.0'` prints `0`.
- [x] 5.2 In `CLAUDE.md`, name `boot/boot.py`, `serve/launch.py`, `live/*.py`, `tests/test_boot_steps.py` beside `tests/test_boot.py`, and the coverage the gate holds, per [D14](design.md#d14).
  Verify: `grep -c 'boot\.sh' CLAUDE.md` prints `0`, and `grep -c -E 'serve/launch\.py|tests/test_boot_steps\.py' CLAUDE.md` prints a number of at least `2`.
- [x] 5.3 In `openspec/specs/boot/spec.md`'s `## Purpose`, "one shell file" → "one Python file", per [D14](design.md#d14).
  Verify: `grep -c 'one shell file' openspec/specs/boot/spec.md` prints `0`, and `grep -c 'one Python file' openspec/specs/boot/spec.md` prints `1`.

## 6 — ⚠️ **HUMAN** — the images

- [x] 6.1 **HUMAN** — push the branch, run `.github/workflows/build-serve-image.yml` on it with the tag `v0.8-rc1`, and write its digest into `gpunit/serve/models.toml`'s `image` line, per [D12](design.md#d12).
  Verify: `grep -c '2fbfee03334addadf57a39a6f71dd7f13e7c59160b8714eb0128ecbc32bc72e2' gpunit/serve/models.toml` prints `0`.
- [x] 6.2 **HUMAN** — build `live/Dockerfile` and `live/Dockerfile.dead` for `linux/amd64` from the repository root, push them as `ghcr.io/alxb1t/gpunit-live` and `ghcr.io/alxb1t/gpunit-live-dead`, and write their digests into `live/gpunit.toml`, `live/gpunit.volume.toml` and `live/gpunit.dead.toml`, per [D12](design.md#d12).
  Verify: `grep -c '7b5285e8cef998b5c0a39da5b2912d65010910929f8beb36d25a07315c87384d' live/gpunit.toml live/gpunit.volume.toml | grep -v ':0$' | wc -l | tr -d ' '` prints `0`, and `grep -c '1cc99d82a4f47bbbfb2d4e832fb3b46be8208cd72c1609b8e13a9c3ebbe0aa71' live/gpunit.dead.toml` prints `0`.

## 7 — ⚠️ **HUMAN · METERED** — make live, make live-dead, make live-volume, make live-serve

- [x] 7.1 **HUMAN · METERED** — with `RUNPOD_API_KEY` set, run `make live`, `make live-dead`, `make live-volume` and `make live-serve`; confirm through the RunPod console that no pod and no `gpunit-` volume is left; append the tails per [D13](design.md#d13), each under `<date> — make <target>, 0012-boot-in-python`. A failed target is a halt: say so and keep its lines.
  Verify: `grep -c -E '^[0-9]{4}-[0-9]{2}-[0-9]{2} — make live(-dead|-volume)?, 0012-boot-in-python$' live/last_run.txt` prints `3`, and `grep -c -E '^[0-9]{4}-[0-9]{2}-[0-9]{2} — make live-serve, 0012-boot-in-python$' live/serve_last_run.txt` prints `1`.
