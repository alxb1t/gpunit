# Tasks — 0014 your own rows

The lookup, the rows' checks, the launcher, the flag, the docs and the `0013` cards, then the image and the metered
proof, per [design](design.md). Every new test carries `@pytest.mark.spec` with the key its task names.

## Progress

- [x] 1 — The lookup
- [ ] 2 — The rows
- [ ] 3 — The launcher
- [ ] 4 — The CLI
- [ ] 5 — The handover
- [ ] 6 — The cards
- [ ] 7 — ⚠️ **HUMAN** — the serve image
- [ ] 8 — ⚠️ **HUMAN · METERED** — make live-serve on live/models.toml

## 1 — The lookup

- [x] 1.1 **HALT CHECK** — none of this change exists yet, and the cards it closes are in the backlog.
  Verify: `grep -c -E 'GPUNIT_MODELS|XDG_CONFIG_HOME' gpunit/serve/table.py` prints `0`, `grep -c '"--no-enable-log-requests"' gpunit/serve/models.toml` prints `2`, `grep -c 'no-enable-log-requests' serve/launch.py` prints `0`, `test -e live/models.toml; echo $?` prints `1`, and `grep -c -E '^- \*\*0013·(R1|R2|R3|R5|R6|R7|S4|S5) ' .minions/backlog.md` prints `8`.
- [x] 1.2 In `tests/conftest.py`'s `isolated_home`, delete `GPUNIT_MODELS` and `XDG_CONFIG_HOME` from the environment, per [D1](design.md#d1).
  Verify: `grep -c -E 'delenv\("(GPUNIT_MODELS|XDG_CONFIG_HOME)"' tests/conftest.py` prints `2`.
- [x] 1.3 Add `user_file` and `rows`, `Row.source`, `Table.user` and `Table.replaced` to `gpunit/serve/table.py`, per [D1](design.md#d1) and [D2](design.md#d2); bind the `serve:rows:` keys `models-flag-first`, `env-before-xdg`, `xdg-default`, `no-file-bundled-only`, `named-file-missing-refused` and `merged` in `tests/test_serve_table.py`.
  Verify: `grep -c -E '"serve:rows:(models-flag-first|env-before-xdg|xdg-default|no-file-bundled-only|named-file-missing-refused|merged)"' tests/test_serve_table.py` prints a number of at least `6`, and `uv run pytest -q tests/test_serve_table.py` exits 0.
- [x] 1.4 Make `_known` in `gpunit/cli.py`, and `serve`, `down` and `_window_spec` in `gpunit/serve/session.py`, read `table.rows(None)`; `_known` prints [D2](design.md#d2)'s replace line; bind `serve:rows:same-name-replaces` in `tests/test_cli.py`.
  Verify: `cat gpunit/cli.py gpunit/serve/session.py | grep -c 'table\.load('` prints `0`, `grep -c 'replaces the bundled' gpunit/cli.py` prints `1`, `grep -c '"serve:rows:same-name-replaces"' tests/test_cli.py` prints `1`, and `uv run pytest -q` exits 0.

## 2 — The rows

- [ ] 2.1 Refuse a user file's top-level key other than `models` in `gpunit/serve/table.py`, per [D3](design.md#d3); bind `serve:rows:image-refused` and `serve:rows:checked-as-bundled` in `tests/test_serve_table.py`.
  Verify: `grep -c 'a user file holds' gpunit/serve/table.py` prints `1`, `grep -c -E '"serve:rows:(image-refused|checked-as-bundled)"' tests/test_serve_table.py` prints a number of at least `2`, and `uv run pytest -q tests/test_serve_table.py` exits 0.
- [ ] 2.2 Refuse `--enable-log-requests` in `_args`, `gpunit/serve/table.py`, per [D4](design.md#d4); bind `serve:rows:logging-on-refused` in `tests/test_serve_table.py`.
  Verify: `grep -c 'request logging stays off' gpunit/serve/table.py` prints `1`, `grep -c '"serve:rows:logging-on-refused"' tests/test_serve_table.py` prints a number of at least `1`, and `uv run pytest -q tests/test_serve_table.py` exits 0.
- [ ] 2.3 Name each row's source in `_known`'s usage error, `gpunit/cli.py`, per [D5](design.md#d5); in `tests/test_cli.py`, `test_an_unknown_model_exits_2_naming_the_tables_models` expects `it holds qwen3-4b (bundled), qwen3.8-27b (bundled)`, and a user row's case is added under `cli:verbs:serve-unknown-model-exits-2`.
  Verify: `grep -c 'qwen3-4b (bundled), qwen3.8-27b (bundled)' tests/test_cli.py` prints a number of at least `1`, and `uv run pytest -q tests/test_cli.py` exits 0.

## 3 — The launcher

- [ ] 3.1 In `serve/launch.py`, set `DO_NOT_TRACK`, `HF_HUB_DISABLE_TELEMETRY` and `VLLM_NO_USAGE_STATS` to `1` and pass `--no-enable-log-requests` last, per [D6](design.md#d6); in `tests/test_serve_image.py`, `ARGS` gains ` --no-enable-log-requests`, and a new test binds `serve:image:launcher-forces-quiet`.
  Verify: `grep -o -E 'DO_NOT_TRACK|HF_HUB_DISABLE_TELEMETRY|VLLM_NO_USAGE_STATS' serve/launch.py | sort -u | wc -l | tr -d ' '` prints `3`, `grep -c '"--no-enable-log-requests"' serve/launch.py` prints `1`, `grep -c '"serve:image:launcher-forces-quiet"' tests/test_serve_image.py` prints `1`, and `uv run pytest -q tests/test_serve_image.py` exits 0.
- [ ] 3.2 Drop `"--no-enable-log-requests"` from the `qwen3-4b` and `qwen3.8-27b` rows' `args` in `gpunit/serve/models.toml`; in `tests/test_serve_table.py`, drop it from `SERVE_ARGS`'s expected string, and make `test_no_row_logs_requests` assert only that no row holds `--enable-log-requests` or `--enable-log-outputs`, per [D6](design.md#d6).
  Verify: `grep -c 'enable-log-requests' gpunit/serve/models.toml` prints `0`, and `uv run pytest -q tests/test_serve_table.py tests/test_serve_image.py` exits 0.

## 4 — The CLI

- [ ] 4.1 Give `serve`, `down`, `volume_up`, `volume_down` and `_window_spec` in `gpunit/serve/session.py` the parameter `models: Path | None = None`, read through `table.rows(models)`, per [D7](design.md#d7).
  Verify: `grep -c 'table.rows(models)' gpunit/serve/session.py` prints `3`, and `uv run pytest -q tests/test_serve_session.py` exits 0.
- [ ] 4.2 Add `--models` to `serve`, `down`, `volume up` and `volume down` in `gpunit/cli.py`, refuse it without a model, pass it to `_known` and the session, and update `USAGE`, per [D7](design.md#d7); bind `cli:verbs:models-without-serve-exits-2` and `cli:verbs:models-on-each-serve-verb` in `tests/test_cli.py`.
  Verify: `grep -c -e '--models goes with --serve' gpunit/cli.py` prints `1`, `grep -o -e '\[--models PATH\]' gpunit/cli.py | wc -l | tr -d ' '` prints `4`, `grep -c -E '"cli:verbs:(models-without-serve-exits-2|models-on-each-serve-verb)"' tests/test_cli.py` prints a number of at least `2`, and `uv run pytest -q` exits 0.

## 5 — The handover

- [ ] 5.1 In `README.md`, add `### Your own rows` and the edits to *Serve a model*'s intro, *The verbs* and *The proof*, per [D8](design.md#d8).
  Verify: `grep -c '^### Your own rows$' README.md` prints `1`, `grep -c 'GPUNIT_MODELS=live/models.toml make live-serve MODEL=granite-4.0-micro' README.md` prints `1`, `grep -o -e '\[--models PATH\]' README.md | wc -l | tr -d ' '` prints a number of at least `3`, and `grep -c 'read the bundled model table instead' README.md` prints `0`.
- [ ] 5.2 In `CLAUDE.md`'s layout, edit the `table.py`, `serve/launch.py` and `live/` entries, per [D8](design.md#d8); keep `lookup and merge` and `logging and telemetry off` each on one line.
  Verify: `grep -c 'lookup and merge' CLAUDE.md` prints `1`, `grep -c 'logging and telemetry off' CLAUDE.md` prints `1`, and `grep -c 'live/models.toml' CLAUDE.md` prints `1`.
- [ ] 5.3 Write `live/models.toml` holding [D3](design.md#d3)'s row, per [D12](design.md#d12); in `tests/test_live.py`, a test under `serve:rows:merged` reads it through `table.rows` and finds `granite-4.0-micro`, sourced from the file, beside the bundled rows.
  Verify: `grep -c -x -F '[models."granite-4.0-micro"]' live/models.toml` prints `1`, `grep -c -x -F 'revision = "56111ae135df9c53a78c99028e7bc24035a9e979"' live/models.toml` prints `1`, `grep -c '"serve:rows:merged"' tests/test_live.py` prints `1`, and `uv run pytest -q tests/test_live.py` exits 0.
- [ ] 5.4 In `docs/threat-model.md`, add F13 and T55, edit T13, the *Counts* line and the STRIDE index, per [D8](design.md#d8).
  Verify: `grep -c -E '^\| T[0-9]+ ' docs/threat-model.md` prints `55`, `grep -E '^\| T55 ' docs/threat-model.md | grep -c '| partly |'` prints `1`, `grep -c '^13\. \*\*F13, the user file' docs/threat-model.md` prints `1`, `grep -c 'Counts: 55 threats. \*\*mitigated 28 · partly 14 · gap 0 · accepted 13.\*\*' docs/threat-model.md` prints `1`, `grep -c '^| F13 user file ' docs/threat-model.md` prints `1`, and `grep -E '^\| T13 ' docs/threat-model.md | grep -c 'a user row may'` prints `1`.
- [ ] 5.5 In `docs/threat-model.md`, move the quiet's citations to `serve/launch.py` in F3, T30, T42 and G9, set T34's status to `partly`, and set line 3 and *Sources* to `v0.10`, per [D8](design.md#d8).
  Verify: `grep -E '^\| T(30|42) ' docs/threat-model.md | grep -c 'serve/launch.py'` prints `2`, `grep -E '^\| T34 ' docs/threat-model.md | grep -c '| partly |'` prints `1`, `grep -c 'gpunit/serve/models.toml:9' docs/threat-model.md` prints `0`, `grep -c 'what holds at .v0.10.' docs/threat-model.md` prints `1`, and `grep -c '^\*\*gpunit at .v0.10.\*\*$' docs/threat-model.md` prints `1`.

## 6 — The cards

- [ ] 6.1 Re-cite `gpunit/spec.py` and `gpunit/volume.py` in `docs/threat-model.md`, row by row, per [D9](design.md#d9)'s table (`0013·R1`).
  Verify: `grep -v -E '^(\| T55 |13\. )' docs/threat-model.md | grep -c -E ':103-104|:75-83|:198-206|:202-203|:200-216|:219-235|:107-110|spec\.py:25., .:105.'` prints `0`, and `grep -v -E '^(\| T55 |13\. )' docs/threat-model.md | grep -o -E ':107-108|:111-116|:101-103|:79-87|volume\.py:194|volume\.py:216-232|:199-207|:203-204' | wc -l | tr -d ' '` prints a number of at least `10`.
- [ ] 6.2 In `README.md`'s laptop bullet, the ledger's text → [D9](design.md#d9)'s, with `card, image and times` on one line (`0013·R2`).
  Verify: `grep -c 'ids and times alone' README.md` prints `0`, and `grep -c -F 'card, image and times' README.md` prints `1`.
- [ ] 6.3 Reword `_free_port`'s comment in `gpunit/serve/session.py`, per [D9](design.md#d9) (`0013·R3`).
  Verify: `grep -c 'a port busy on 127.0.0.1 is never refused after a yes' gpunit/serve/session.py` prints `1`.
- [ ] 6.4 Give `log.clean` its `keep` parameter in `gpunit/log.py`, clean each streamed part in `gpunit/serve/chat.py`, and name the chat in T39, per [D9](design.md#d9) (`0013·S4`); bind `serve:chat:streamed-text-cleaned` in `tests/test_serve_chat.py`.
  Verify: `grep -c 'log.clean(part, keep=' gpunit/serve/chat.py` prints `1`, `grep -c '"serve:chat:streamed-text-cleaned"' tests/test_serve_chat.py` prints `1`, `grep -E '^\| T39 ' docs/threat-model.md | grep -c 'gpunit/serve/chat.py'` prints `1`, and `uv run pytest -q tests/test_serve_chat.py tests/test_serve_session.py` exits 0.
- [ ] 6.5 Add [D9](design.md#d9)'s `serve` sentence to T34's mitigation in `docs/threat-model.md` and to README's *Placement* bullet (`0013·S5`).
  Verify: `grep -c 'takes no .datacenters. yet' README.md` prints `1`, and `grep -E '^\| T34 ' docs/threat-model.md | grep -c 'takes no .datacenters. yet'` prints `1`.

## 7 — ⚠️ **HUMAN** — the serve image

- [ ] 7.1 **HUMAN** — `git push -u origin v0.10_your_own_rows`, then `gh workflow run build-serve-image.yml --ref v0.10_your_own_rows -f tag=v0.10-rc1`, and `gh run watch` on its run, per [D11](design.md#d11).
  Verify: `gh run list --workflow build-serve-image.yml --branch v0.10_your_own_rows --status success --limit 1 --json databaseId --jq length` prints `1`.
- [ ] 7.2 **HUMAN** — print the digest with `docker buildx imagetools inspect ghcr.io/alxb1t/gpunit-vllm:v0.10-rc1 | sed -n 's/^Digest: *//p'`, then set `gpunit/serve/models.toml:2` to `image = "ghcr.io/alxb1t/gpunit-vllm@<that digest>"`, per [D11](design.md#d11).
  Verify: `grep -c '1a83cf6c73421810210eabb14772c892bbf3086359486c1676da02725dd8ee8b' gpunit/serve/models.toml` prints `0`, and `uv run pytest -q tests/test_serve_table.py` exits 0.

## 8 — ⚠️ **HUMAN · METERED** — make live-serve on live/models.toml

- [ ] 8.1 **HUMAN · METERED** — on [D12](design.md#d12)'s restricted key as `RUNPOD_API_KEY`, run `GPUNIT_MODELS=live/models.toml make live-serve MODEL=granite-4.0-micro`, then `uv run gpunit spend --days 1`; confirm in the console that no pod and no `gpunit-` volume is left.
  Append the tail to `live/serve_last_run.txt` under `<date> — make live-serve granite-4.0-micro, 0014-your-own-rows`. A failed run is a halt: say so and keep its lines.
  Verify: `grep -c -E '^[0-9]{4}-[0-9]{2}-[0-9]{2} — make live-serve granite-4\.0-micro, 0014-your-own-rows$' live/serve_last_run.txt` prints `1`.
- [ ] 8.2 **HUMAN** — in `README.md`'s `- **Measured minimum:**` line and `docs/threat-model.md`'s `- **G6 measured:**` line, "made in the console at its narrowest settings" → "made in the console with <8.1's per-API settings, as the console names them>", dated as 8.1, per [D9](design.md#d9) (`0013·R5`).
  Verify: `cat README.md docs/threat-model.md | grep -c 'at its narrowest settings'` prints `0`, and `grep -c '^- \*\*Measured minimum:\*\* ' README.md` prints `1`.
