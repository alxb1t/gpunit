# Tasks — 0020 paydown

The row arguments' rule, the threat model's worker rows, the wait mark, then the serve image by a person, per
[design](design.md). Each new test carries `@pytest.mark.spec` with the key its task names.

## Progress

- [x] 1 — The rows
- [x] 2 — The threat model
- [x] 3 — The wait mark
- [x] 4 — **HUMAN** — The serve image

## 1 — The rows

- [x] 1.1 Write the flag rule of [D1](design.md#d1) in `gpunit/serve/table.py::_args`, with `_LOGGING` beside
  `_LAUNCHERS`. Add the tests of `serve:table:launcher-flags-refused` and `serve:table:logging-families-refused`, and
  the argparse replay of [Tests](design.md#tests), to `tests/test_serve_table.py`; the `--enable-log-requests=yes`
  case of the `serve:rows:logging-on-refused` test now expects a refusal.
  Verify: `grep -c 'serve:table:launcher-flags-refused' tests/test_serve_table.py` prints `1`, `grep -c 'serve:table:logging-families-refused' tests/test_serve_table.py` prints `1`, and `uv run pytest -q --no-cov tests/test_serve_table.py` exits 0.
- [x] 1.2 Give `serve/launch.py` the same rule, per [D2](design.md#d2). Add the test of
  `serve:image:launcher-refuses-a-row` to `tests/test_serve_image.py`; `SERVE_ARGS` in
  `test_the_launcher_keeps_logging_and_telemetry_off` becomes `--max-model-len 16384 --max-num-seqs 8`.
  Verify: `grep -c 'serve:image:launcher-refuses-a-row' tests/test_serve_image.py` prints `1`, and `uv run pytest -q --no-cov tests/test_serve_image.py` exits 0.
- [x] 1.3 Rewrite T13, T30 and T55 in `THREAT_MODEL.md` and the row bullets of `docs/usage.md`'s *Your own rows*, per
  [D3](design.md#d3).
  Verify: `grep -c 'The hole' THREAT_MODEL.md` prints `0`, `grep -c 'request logging stays off\|as vLLM reads' docs/usage.md` prints a number of at least `1`, and `uv run pytest -q --no-cov tests/test_docs.py` exits 0.

## 2 — The threat model

- [x] 2.1 Rewrite the worker row, G17 and T20 in `THREAT_MODEL.md`, per [D4](design.md#d4).
  Verify: `grep -c 'only a pushed commit leaves it' THREAT_MODEL.md` prints `0`, `grep -c 'model provider' THREAT_MODEL.md` prints a number of at least `2`, `grep '^| T20 ' THREAT_MODEL.md | grep -c '| accepted |'` prints `1`, and `uv run pytest -q --no-cov tests/test_docs.py` exits 0.

## 3 — The wait mark

- [x] 3.1 Add `State.waiting`, `State.mark_waiting` and `State.clear_waiting` to `gpunit/state.py`, per
  [D5](design.md#d5), with their test in `tests/test_state.py`.
  Verify: `grep -c 'def mark_waiting' gpunit/state.py` prints `1`, and `uv run pytest -q --no-cov tests/test_state.py` exits 0.
- [x] 3.2 Mark in `gpunit/lifecycle.py::stock_round`, clear in `lifecycle.up`'s and `gpunit/volume.py::up`'s wait,
  and add `lifecycle.refuse_waiting`, asked by `_guarded` and `volume.up`, per [D5](design.md#d5). Add the tests of
  `session:one:waiting-refuses`, `session:one:stale-waiting-removed` and `session:stock:waiting-marked` to
  `tests/test_up.py`, and of `volume:stock:waiting-marked` to `tests/test_volume.py`.
  Verify: `grep -c '^def refuse_waiting' gpunit/lifecycle.py` prints `1`, `grep -c 'session:one:waiting-refuses' tests/test_up.py` prints `1`, `grep -c 'volume:stock:waiting-marked' tests/test_volume.py` prints `1`, and `uv run pytest -q --no-cov -m "not e2e"` exits 0.

## 4 — **HUMAN** — The serve image

- [x] 4.1 Push the version branch and build the serve image on it, per [D6](design.md#d6):

  ```sh
  git push origin 0020-paydown
  gh workflow run build-serve-image.yml --repo alxb1t/gpunit --ref 0020-paydown -f tag=v0.12.1-rc1
  gh run list --repo alxb1t/gpunit --workflow build-serve-image.yml --branch 0020-paydown --limit 1 --json databaseId --jq '.[0].databaseId'
  gh run watch --repo alxb1t/gpunit <the id the last command printed>
  ```

  Verify: `gh run list --repo alxb1t/gpunit --workflow build-serve-image.yml --branch 0020-paydown --limit 1 --json conclusion --jq '.[0].conclusion'` prints `success`.
- [x] 4.2 Read the image's digest, then set it in `gpunit/serve/models.toml`'s line
  `image = "ghcr.io/alxb1t/gpunit-vllm@sha256:<digest>"`:

  ```sh
  gh api /users/alxb1t/packages/container/gpunit-vllm/versions --jq '.[] | select(.metadata.container.tags | index("v0.12.1-rc1")) | .name'
  ```

  Verify: `grep -c 'sha256:078df3abebbb081604e6f647091a7a04761ed44ac631148c2db47215782e08f6' gpunit/serve/models.toml` prints `0`, `grep -c '^image = "ghcr.io/alxb1t/gpunit-vllm@sha256:' gpunit/serve/models.toml` prints `1`, and `uv run pytest -q --no-cov tests/test_serve_table.py tests/test_serve_image.py` exits 0.
