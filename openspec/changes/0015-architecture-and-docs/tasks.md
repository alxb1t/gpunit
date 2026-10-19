# Tasks — 0015 architecture and docs

The layer test and the moves, one metered run, then the links test, the citations and the pages of the guide, per
[design](design.md). Every new test carries `@pytest.mark.spec` with the key its task names.

## Progress

- [x] 1 — The layers
- [x] 2 — The renames
- [x] 3 — The boot contract
- [x] 4 — ⚠️ **HUMAN · METERED** — make live after the moves
- [ ] 5 — The citations
- [ ] 6 — Decisions and principles
- [ ] 7 — The pages
- [ ] 8 — The map and the handover

## 1 — The layers

- [x] 1.1 **HALT CHECK** — none of this change exists yet, and the code is as [design](design.md#context) read it.
  Verify: `grep -c '^from gpunit import __version__, log$' gpunit/runpod.py` prints `1`, `ls docs` prints `threat-model.md`, `test -e gpunit/version.py; echo $?` prints `1`, `test -e tests/test_layers.py; echo $?` prints `1`, `grep -c '^def _open(' gpunit/library.py` prints `1`, `grep -c '^class Refused' gpunit/provider.py` prints `1`, and `grep -c '^def fingerprint' gpunit/provider.py` prints `1`.
- [x] 1.2 Write `tests/test_layers.py` per [D9](design.md#d9): `LAYERS` keyed by dotted module name, `gpunit.version` in it; the repo tests `test_the_package_holds_its_layers`, `test_runpod_is_built_in_library_and_cli_alone`, `test_the_package_imports_the_stdlib_alone` and `test_only_the_cli_exits`; a `_caught` twin for each rule under `tmp_path`.
  Bind `architecture:layers:` `hold`, `upward-caught`, `cycle-caught`, `provider-built`, `stdlib-only` and `exit-in-cli`.
  Verify: `grep -o -E '"architecture:layers:(hold|upward-caught|cycle-caught|provider-built|stdlib-only|exit-in-cli)"' tests/test_layers.py | sort -u | wc -l | tr -d ' '` prints `6`, `uv run pytest -q tests/test_layers.py -k caught` exits 0, and `uv run pytest -q tests/test_layers.py -k test_the_package_holds_its_layers` exits 1.
- [x] 1.3 Add `gpunit/version.py`, and point `gpunit/__init__.py`, `gpunit/runpod.py` and `pyproject.toml`'s `[tool.hatch.version]` at it, per [D2](design.md#d2).
  Verify: `grep -c 'path = "gpunit/version.py"' pyproject.toml` prints `1`, `uv run python -c "import gpunit; print(gpunit.__version__)"` prints `0.10.0`, and `uv run pytest -q tests/test_layers.py` exits 0.
- [x] 1.4 Move `from gpunit.serve import table` into `_known` in `gpunit/cli.py`, per [D3](design.md#d3).
  Verify: `grep -c '^from gpunit.serve import table' gpunit/cli.py` prints `0`, and `uv run pytest -q` exits 0.

## 2 — The renames

- [x] 2.1 Rename `library._open` to `library.open_session` in `gpunit/library.py`, `gpunit/run.py`, `gpunit/serve/session.py` and `tests/test_library.py`, per [D4](design.md#d4).
  Verify: `cat gpunit/library.py gpunit/run.py gpunit/serve/session.py tests/test_library.py | grep -c -E 'library\._open|^def _open\('` prints `0`, `grep -c '^def open_session(' gpunit/library.py` prints `1`, and `uv run pytest -q tests/test_library.py tests/test_run.py tests/test_serve_session.py` exits 0.
- [x] 2.2 Rename `provider.Refused` to `provider.Unplaceable` in `gpunit/provider.py`, `gpunit/runpod.py`, `gpunit/lifecycle.py`, `gpunit/volume.py`, `tests/test_up.py`, `tests/test_volume.py` and `tests/test_runpod.py`, per [D5](design.md#d5).
  Verify: `cat gpunit/provider.py gpunit/runpod.py gpunit/lifecycle.py gpunit/volume.py tests/test_up.py tests/test_volume.py tests/test_runpod.py | grep -c -w 'Refused'` prints `0`, `grep -c '^class Unplaceable' gpunit/provider.py` prints `1`, and `uv run pytest -q` exits 0.
- [x] 2.3 Add `lifecycle.delete_volume` and call it from `lifecycle.sweep_window`, `volume.down` and `volume._sweep`, per [D6](design.md#d6).
  Verify: `cat gpunit/lifecycle.py gpunit/volume.py | grep -c 'ledger.record_deleted('` prints `1`, `grep -c '^def delete_volume(' gpunit/lifecycle.py` prints `1`, and `uv run pytest -q` exits 0.

## 3 — The boot contract

- [x] 3.1 Add `gpunit/contract.py` per [D7](design.md#d7): move the boot-log patterns, `fingerprint` and `old_boot` from `gpunit/provider.py`; `RunPod.create` calls `contract.pod_env`; `gpunit/lifecycle.py`, `tests/test_runpod.py` and `tests/test_boot.py` import from `gpunit.contract`; `LAYERS` gains `"gpunit.contract": "model"`.
  Verify: `grep -c -E '^(_HOST_KEY|_OLD_KEY|_BOOT_STEP|_BOOT_START) = |^def (fingerprint|old_boot)\(' gpunit/provider.py` prints `0`, `grep -c -E '^(_HOST_KEY|_OLD_KEY|_BOOT_STEP|_BOOT_START) = |^def (fingerprint|old_boot)\(' gpunit/contract.py` prints `6`, `grep -c '"PUBLIC_KEY"' gpunit/runpod.py` prints `0`, `grep -c 'contract.pod_env(' gpunit/runpod.py` prints `1`, `grep -c '"gpunit.contract": "model"' tests/test_layers.py` prints `1`, and `uv run pytest -q` exits 0.
- [x] 3.2 Add `gpunit/hostkey.py` per [D8](design.md#d8): move `LOG_WAIT_S`, `SCAN_WAIT_S`, `LOG_TAIL`, `_scan` and `_fingerprint_of` from `gpunit/lifecycle.py`; `_verify_host_key` becomes `hostkey.verify`; `LAYERS` gains `"gpunit.hostkey": "lifecycle"`.
  Verify: `grep -c -E '^def (_verify_host_key|_scan|_fingerprint_of)\(|^(LOG_WAIT_S|SCAN_WAIT_S|LOG_TAIL) = ' gpunit/lifecycle.py` prints `0`, `grep -c '^def verify(' gpunit/hostkey.py` prints `1`, `grep -c 'hostkey.verify(' gpunit/lifecycle.py` prints `1`, `grep -c '"gpunit.hostkey": "lifecycle"' tests/test_layers.py` prints `1`, and `uv run pytest -q` exits 0.

## 4 — ⚠️ **HUMAN · METERED** — make live after the moves

- [x] 4.1 **HUMAN · METERED** — with `RUNPOD_API_KEY` set, run `mkdir -p .minions && make live 2>&1 | tee .minions/live-0015.txt`, per [D17](design.md#d17). A failed run is a halt: say so and keep its lines.
  Then run `{ echo; echo "$(date -u +%F) — make live, 0015-architecture-and-docs"; cat .minions/live-0015.txt; } >> live/last_run.txt`.
  Verify: `grep -c -E '^[0-9]{4}-[0-9]{2}-[0-9]{2} — make live, 0015-architecture-and-docs$' live/last_run.txt` prints `1`, and `sed -n '/make live, 0015-architecture-and-docs/,$p' live/last_run.txt | grep -c 'host key verified: SHA256:'` prints a number of at least `1`.

## 5 — The citations

- [ ] 5.1 Write `docs/decisions.md`'s opening and a `### Dn · <title>` heading for each decision of [Seed: decisions](design.md#seed-decisions), each with its bold choice line, per [D12](design.md#d12).
  Verify: `grep -c -E '^### D[0-9]+ · ' docs/decisions.md` prints `51`.
- [ ] 5.2 Write `tests/test_docs.py` per [D10](design.md#d10), the link, decision and archive rules, each with a `_caught` twin; bind `architecture:docs:` `links-resolve`, `link-caught`, `decisions-resolve` and `archive-caught`.
  Verify: `grep -o -E '"architecture:docs:(links-resolve|link-caught|decisions-resolve|archive-caught)"' tests/test_docs.py | sort -u | wc -l | tr -d ' '` prints `4`, and `uv run pytest -q tests/test_docs.py -k caught` exits 0.
- [ ] 5.3 Rewrite each archived citation in the scanned files of [D10](design.md#d10) as `decision Dn`, per [D11](design.md#d11).
  Verify: `grep -rnE "[0-9]{4} (design )?D[0-9]+" gpunit boot serve live tests Makefile pyproject.toml .github docs README.md CLAUDE.md | grep -v -e last_run.txt -e '^docs/decisions.md:' | wc -l | tr -d ' '` prints `0`, and `uv run pytest -q` exits 0.

## 6 — Decisions and principles

- [ ] 6.1 Write each decision's body in `docs/decisions.md`, re-read against the code, per [D12](design.md#d12).
  Verify: `grep -c '^- \*\*Why:\*\* ' docs/decisions.md` prints `51`, `grep -c '^- \*\*Made by:\*\* ' docs/decisions.md` prints `51`, and `uv run pytest -q tests/test_docs.py` exits 0.
- [ ] 6.2 Write `docs/principles.md` with `## The words` and `## The rules`, from [Seed: principles](design.md#seed-principles), per [D13](design.md#d13).
  Verify: `grep -c -x -E '## (The words|The rules)' docs/principles.md` prints `2`, `grep -o -E '0015·F[0-9]+' docs/principles.md | sort -u | grep -c -x -E '0015·F(2|3|5|20|23)'` prints `5`, and `uv run pytest -q tests/test_docs.py` exits 0.

## 7 — The pages

- [ ] 7.1 Write `docs/modules.md` per [D14](design.md#d14), its layer table `| layer | modules |` with backticked dotted names; add `test_the_modules_page_names_every_module` and its twin to `tests/test_layers.py`, bound to `architecture:layers:modules-named`, per [D9](design.md#d9).
  Verify: `grep -c '"architecture:layers:modules-named"' tests/test_layers.py` prints a number of at least `1`, and `uv run pytest -q tests/test_layers.py tests/test_docs.py` exits 0.
- [ ] 7.2 Write `docs/data-flow.md` per [D14](design.md#d14), with the sections `## A session`, `## The boot contract`, `## The state files`, `## Serve`, `## The window volume`, `## Spend` and `## Exit codes`.
  Verify: `grep -c -x -E '## (A session|The boot contract|The state files|Serve|The window volume|Spend|Exit codes)' docs/data-flow.md` prints `7`, and `uv run pytest -q tests/test_docs.py` exits 0.
- [ ] 7.3 Write `docs/extending.md` per [D14](design.md#d14), with the sections `## A verb`, `## A gpunit.toml key`, `## A serve row`, `## A provider`, `## A boot.py change`, `## A pin bump`, `## A live proof` and `## The rules`.
  Verify: `grep -c -x -E '## (A verb|A gpunit\.toml key|A serve row|A provider|A boot\.py change|A pin bump|A live proof|The rules)' docs/extending.md` prints `8`, and `uv run pytest -q tests/test_docs.py` exits 0.
- [ ] 7.4 Write `docs/pins.md` per [D14](design.md#d14).
  Verify: `grep -c -F -e 'serve/Dockerfile' -e 'gpunit/serve/models.toml' -e 'uv.lock' -e '.github/workflows/build-serve-image.yml' docs/pins.md` prints a number of at least `4`, and `uv run pytest -q tests/test_docs.py` exits 0.
- [ ] 7.5 In `docs/threat-model.md`, turn every line citation into a symbol or file citation, set T13 and T30 to `partly` wherever their status is listed, and edit *Counts*, line 3 and *Sources*, per [D15](design.md#d15). Add the symbol rule and its twin to `tests/test_docs.py`, bound to `architecture:docs:symbols-resolve`.
  Verify: `grep -E '^\| T(13|30) ' docs/threat-model.md | grep -c '| partly |'` prints `2`, `grep -c 'mitigated 26 · partly 16' docs/threat-model.md` prints `1`, `grep -c '"architecture:docs:symbols-resolve"' tests/test_docs.py` prints a number of at least `1`, and `uv run pytest -q` exits 0.

## 8 — The map and the handover

- [ ] 8.1 Write `docs/README.md` per [D16](design.md#d16).
  Verify: `grep -o -E '\]\((principles|decisions|data-flow|modules|extending|pins|threat-model)\.md' docs/README.md | sort -u | wc -l | tr -d ' '` prints `7`, and `uv run pytest -q tests/test_docs.py` exits 0.
- [ ] 8.2 Cut `README.md` to the user's guide, per [D16](design.md#d16).
  Verify: `grep -c 'openspec/changes/archive' README.md` prints `0`, `grep -c '](docs/README.md)' README.md` prints a number of at least `1`, and `uv run pytest -q tests/test_docs.py` exits 0.
- [ ] 8.3 Rewrite `CLAUDE.md` per [D16](design.md#d16).
  Verify: `grep -c -x -E '## (Layout — where things live here|Invariants)' CLAUDE.md` prints `0`, `grep -c -x '## The rules for a change' CLAUDE.md` prints `1`, `grep -c 'docs/README.md' CLAUDE.md` prints a number of at least `1`, `grep -c 'gpunit/version.py' CLAUDE.md` prints a number of at least `1`, and `uv run pytest -q tests/test_docs.py` exits 0.
