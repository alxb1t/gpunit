# Tasks — 0017 mf readiness

The tests made sandbox-safe, then the root documents, then the ruleset and CI by a person, per [design](design.md). Paths are
relative to the repository's root.

## Progress

- [ ] 1 — The sandbox-safe gate
- [ ] 2 — The root documents
- [ ] 3 — **HUMAN** — The ruleset and CI

## 1 — The sandbox-safe gate

- [ ] 1.1 **HALT CHECK** The redirect tests pass with the proxy variables unset, per [D3](design.md#d3). No file changes.
  Verify: `env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy uv run pytest -q --no-cov tests/test_runpod.py::test_a_redirect_is_not_followed tests/test_boot_steps.py::test_a_redirect_is_a_failed_stop_never_followed` exits 0.
- [ ] 1.2 Add the `no_proxy` fixture of [D3](design.md#d3) to `tests/conftest.py`, and request it in
  `test_a_redirect_is_not_followed` (`tests/test_runpod.py`) and `test_a_redirect_is_a_failed_stop_never_followed`
  (`tests/test_boot_steps.py`).
  Verify: `grep -c 'def no_proxy' tests/conftest.py` prints `1`, and `uv run pytest -q --no-cov tests/test_runpod.py tests/test_boot_steps.py` exits 0.
- [ ] 1.3 Register the `e2e` mark in `pyproject.toml` and reword its coverage comment, per
  [The tests moved](design.md#the-tests-moved). Add the autouse `fixed_port` fixture of [D1](design.md#d1) to
  `tests/conftest.py`, and mark `test_a_busy_local_port_is_skipped_before_the_price` `e2e`.
  Verify: `grep -c '"e2e: ' pyproject.toml` prints `1`, `grep -c 'end-to-end' pyproject.toml` prints `0`, and `grep -c 'def fixed_port' tests/conftest.py` prints `1`.
- [ ] 1.4 **HALT CHECK** Serve's tests pass past the faked probe under this build's sandbox, per [D1](design.md#d1).
  A failure past the bind means D1 is wrong. No file changes.
  Verify: `uv run pytest -q --no-cov -m "not e2e" tests/test_serve_session.py tests/test_cli.py` exits 0.
- [ ] 1.5 Mark `e2e` every test of [The tests moved](design.md#the-tests-moved): `pytestmark` in
  `tests/test_tool_call.py`, `@pytest.mark.e2e` on each named test in `tests/test_library.py`, `tests/test_run.py` and
  `tests/test_serve_chat.py`.
  Verify: `uv run pytest --collect-only -q -m e2e | grep -c '::'` prints `32`, and `uv run pytest --collect-only -q -m "not e2e" | grep -c '::'` prints `535`.
- [ ] 1.6 In `Makefile`, the gate's `pytest` line takes `-m "not e2e"`, and the `e2e` target joins it and `.PHONY`,
  per [The tests moved](design.md#the-tests-moved).
  Verify: `make -n e2e` prints `uv run pytest -m e2e`, `grep -c -F 'uv run pytest --cov -m "not e2e"' Makefile` prints `1`, and `make e2e` exits 0.
- [ ] 1.7 Add `      - run: make e2e` after `      - run: make gate` in `.github/workflows/gate.yml`, per
  [D4](design.md#d4). In `tests/test_ci.py`, `test_the_gate_workflow_runs_the_gate` also asserts a `make e2e` step
  after the `make gate` step.
  Verify: `grep -c -x '      - run: make e2e' .github/workflows/gate.yml` prints `1`, `grep -c 'make e2e' tests/test_ci.py` prints a number of at least `1`, and `uv run pytest -q --no-cov tests/test_ci.py` exits 0.
- [ ] 1.8 Add D54 to the end of `docs/decisions.md`, per [D54's text](design.md#d54s-text).
  Verify: `grep -c '^### D54 · The gate runs inside a sandboxed worker$' docs/decisions.md` prints `1`, and `uv run pytest -q --no-cov tests/test_docs.py` exits 0.

## 2 — The root documents

- [ ] 2.1 `git mv docs/threat-model.md THREAT_MODEL.md`, per [D6](design.md#d6). Re-point its own links into `docs/`
  (`usage.md#…` → `docs/usage.md#…`, `principles.md#…` → `docs/principles.md#…`). Re-point each link and path to it in
  `README.md`, `AGENTS.md`, `docs/README.md`, `docs/decisions.md`, `docs/extending.md`, `docs/pins.md` and
  `docs/usage.md`. Add `THREAT_MODEL.md` to `tests/test_docs.py`'s `guide` and `SCANNED_FILES`.
  Verify: `test -e docs/threat-model.md; echo $?` prints `1`, `git grep -n 'threat-model.md' -- . ':!openspec/changes' ':!CHANGELOG.md' | wc -l | tr -d ' '` prints `0`, and `uv run pytest -q --no-cov tests/test_docs.py` exits 0.
- [ ] 2.2 Rewrite D9 in `docs/decisions.md` per [D9's text](design.md#d9s-text), and its anchor in
  `docs/extending.md` and `docs/principles.md`.
  Verify: `grep -c '^### D9 · The threat model is ' docs/decisions.md` prints `1`, `git grep -c 'the-threat-model-lives-in-docs' -- docs | wc -l | tr -d ' '` prints `0`, and `uv run pytest -q --no-cov tests/test_docs.py` exits 0.
- [ ] 2.3 Add the actor row and G17 of [The threat model's additions](design.md#the-threat-models-additions) to
  `THREAT_MODEL.md`.
  Verify: `grep -c '^| a MinionsFactory worker in the checkout |' THREAT_MODEL.md` prints `1`, and `grep -c '^| G17 |' THREAT_MODEL.md` prints `1`.
- [ ] 2.4 `git mv docs/README.md ARCHITECTURE.md`, per [D7](design.md#d7): its title, and its links re-pointed into
  `docs/` and to `THREAT_MODEL.md`. Re-point the links to it in `README.md` and `AGENTS.md`. Add `ARCHITECTURE.md` to
  `tests/test_docs.py`'s `guide` and `SCANNED_FILES`.
  Verify: `test -e docs/README.md; echo $?` prints `1`, `head -1 ARCHITECTURE.md` prints `# gpunit — architecture`, `git grep -n 'docs/README.md' -- . ':!openspec/changes' ':!CHANGELOG.md' | wc -l | tr -d ' '` prints `0`, and `uv run pytest -q --no-cov tests/test_docs.py` exits 0.
- [ ] 2.5 Write `CODING_STANDARDS.md` and `CONTRIBUTING.md` per [The root documents](design.md#the-root-documents),
  moving `## How a change is cut here` and `## The rules for a change` out of `AGENTS.md`, per [D8](design.md#d8).
  `docs/extending.md`'s `## The rules` becomes one line linking `CONTRIBUTING.md`'s. `tests/test_ci.py` reads the
  OpenSpec version from `CONTRIBUTING.md`; `docs/pins.md`'s OpenSpec row and `gate.yml`'s step name say
  `CONTRIBUTING.md`. Add both files to `tests/test_docs.py`'s `guide` and `SCANNED_FILES`.
  Verify: `grep -c '@fission-ai/openspec@1.11.0' CONTRIBUTING.md` prints `1`, `grep -c '^## The rules for a change$' CONTRIBUTING.md` prints `1`, `grep -c -E '^## (How a change is cut here|The rules for a change)$' AGENTS.md` prints `0`, `grep -c 'CLAUDE.md' tests/test_ci.py docs/pins.md .github/workflows/gate.yml` prints `0` for each file, and `uv run pytest -q --no-cov tests/test_ci.py tests/test_docs.py` exits 0.
- [ ] 2.6 Rewrite `AGENTS.md` per [The root documents](design.md#the-root-documents): its title, the mandatory lines,
  the gate's `make e2e` sentence, the template's `## Tests`, the guardrail's line. In `tests/test_docs.py`, `AGENTS.md`
  takes `CLAUDE.md`'s place in `guide`, `SCANNED_FILES` and `guide`'s docstring, per [D9](design.md#d9).
  Verify: `head -1 AGENTS.md` prints `# gpunit — shared context for coding agents`, `grep -c -E 'CODING_STANDARDS.md|THREAT_MODEL.md|ARCHITECTURE.md' AGENTS.md` prints a number of at least `3`, `grep -c '^## Tests$' AGENTS.md` prints `1`, `grep -c 'CLAUDE.md' tests/test_docs.py` prints `0`, `test -L CLAUDE.md` exits 0, and `uv run pytest -q --no-cov tests/test_docs.py` exits 0.

## 3 — **HUMAN** — The ruleset and CI

- [ ] 3.1 Create the ruleset of [D10](design.md#d10):

  ```sh
  gh api -X POST repos/alxb1t/gpunit/rulesets --input - <<'JSON'
  {"name":"protect main","target":"branch","enforcement":"active",
   "conditions":{"ref_name":{"include":["~DEFAULT_BRANCH"],"exclude":[]}},
   "rules":[{"type":"deletion"},{"type":"non_fast_forward"}]}
  JSON
  ```

  Verify: `gh api repos/alxb1t/gpunit/rulesets --jq '.[].name'` prints `protect main`.
- [ ] 3.2 Push the version branch, so CI runs `make gate` and `make e2e`, and wait for it:

  ```sh
  git push origin 0017-mf-readiness
  gh run watch --repo alxb1t/gpunit "$(gh run list --repo alxb1t/gpunit --branch 0017-mf-readiness --workflow gate.yml --limit 1 --json databaseId --jq '.[0].databaseId')"
  ```

  Verify: `gh run list --repo alxb1t/gpunit --branch 0017-mf-readiness --workflow gate.yml --limit 1 --json conclusion --jq '.[0].conclusion'` prints `success`.
