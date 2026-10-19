# Tasks — 0016 readme and docs

The license and the metadata, the gate workflow, the move into `docs/`, the front page, then GitHub by hand, per
[design](design.md). Every new test carries `@pytest.mark.spec` with the key its task names.

## Progress

- [x] 1 — The license and the metadata
- [x] 2 — The gate workflow
- [x] 3 — The move
- [ ] 4 — The front page
- [ ] 5 — ⚠️ **HUMAN** — GitHub's fields and the first CI run

## 1 — The license and the metadata

- [x] 1.1 **HALT CHECK** — none of this change exists yet, and README is the guide [design](design.md#context) read.
  Verify: `test -e LICENSE; echo $?` prints `1`, `grep -c '^keywords' pyproject.toml` prints `0`, `test -e .github/workflows/gate.yml; echo $?` prints `1`, `test -e docs/usage.md; echo $?` prints `1`, `grep -c '' README.md` prints `432`, and `grep -c '^- \*\*0015·R7 ' .minions/backlog.md` prints `1`.
- [x] 1.2 Add `LICENSE`, and `license`, `license-files` and the hatchling floor to `pyproject.toml`, per [D1](design.md#d1).
  Verify: `grep -c 'Apache License' LICENSE` prints a number of at least `1`, `grep -c -x 'license = "Apache-2.0"' pyproject.toml` prints `1`, `grep -c -x 'license-files = \["LICENSE"\]' pyproject.toml` prints `1`, `grep -c '"hatchling>=1.27"' pyproject.toml` prints `1`, and `uv build -q -o .minions/dist` exits 0.
- [x] 1.3 Set `description` and add `keywords` in `pyproject.toml`, per [D2](design.md#d2); add `0016·D1` to D1's *Made by* in `docs/decisions.md`, per [D8](design.md#d8).
  Verify: `grep -c -x 'description = "Rent a cloud GPU, use it, and tear it down on every way out."' pyproject.toml` prints `1`, `grep -c '^keywords = \["gpu", "cloud-gpu", "runpod"' pyproject.toml` prints `1`, `grep -c '0016·D1' docs/decisions.md` prints `1`, and `uv run pytest -q` exits 0.

## 2 — The gate workflow

- [x] 2.1 Write `.github/workflows/gate.yml` per [D3](design.md#d3); add D53 to `docs/decisions.md` per [D8](design.md#d8); edit the OpenSpec row of `docs/pins.md` per [D3](design.md#d3).
  Verify: `grep -c -x '      - run: make gate' .github/workflows/gate.yml` prints `1`, `grep -c '^### D53 · ' docs/decisions.md` prints `1`, `grep -c 'gate.yml' docs/pins.md` prints a number of at least `1`, and `uv run pytest -q tests/test_docs.py tests/test_serve_image.py` exits 0.
- [x] 2.2 Write `tests/test_ci.py` per [D9](design.md#d9), each test with its twin; bind `architecture:ci:runs-the-gate` and `architecture:ci:actions-pinned`.
  Verify: `grep -o -E '"architecture:ci:(runs-the-gate|actions-pinned)"' tests/test_ci.py | sort -u | wc -l | tr -d ' '` prints `2`, and `uv run pytest -q tests/test_ci.py` exits 0.

## 3 — The move

- [x] 3.1 Write `docs/usage.md` from README's user's guide, per [D5](design.md#d5); README stays as it is until phase 4.
  Verify: `grep -c -x -E '## (Use it from a project|Use it from Python|Serve a model|Working window|What it cost|Security and privacy|The verbs|The spend rules)' docs/usage.md` prints `8`, and `uv run pytest -q tests/test_docs.py` exits 0.
- [x] 3.2 Write `docs/proofs.md` from README's proof section and the tails, per [D6](design.md#d6).
  Verify: ``grep -c -x -E '## (The latest runs|`make live`|`make live-volume`|`make live-serve`|`make live-dead`|`make live-serve-dead`)' docs/proofs.md`` prints `6`, `grep -c -F -e 'live/last_run.txt' -e 'live/serve_last_run.txt' -e 'live/spend_last_run.txt' docs/proofs.md` prints a number of at least `3`, and `uv run pytest -q tests/test_docs.py` exits 0.
- [x] 3.3 Re-point every README citation in `docs/threat-model.md`, `docs/extending.md`, `docs/pins.md` and `docs/README.md`, per [D7](design.md#d7); add D52 to `docs/decisions.md`, per [D8](design.md#d8).
  Verify: `cat docs/threat-model.md docs/extending.md docs/pins.md | grep -c 'README'` prints `0`, `grep -o -E '\]\((usage|proofs)\.md' docs/README.md | sort -u | wc -l | tr -d ' '` prints `2`, `grep -c 'docs/proofs.md' docs/extending.md` prints a number of at least `1`, `grep -c '^### D52 · ' docs/decisions.md` prints `1`, and `uv run pytest -q tests/test_docs.py` exits 0.

## 4 — The front page

- [ ] 4.1 Rewrite `README.md` as the front page, per [D4](design.md#d4).
  Verify: `test "$(grep -c '' README.md)" -le 60; echo $?` prints `0`, `grep -o -E 'decisions\.md#d(1|5|20|22|23|25|35|46|49|50)-' README.md | sort -u | wc -l | tr -d ' '` prints `10`, `grep -c 'actions/workflows/gate.yml/badge.svg' README.md` prints `1`, `grep -c '](docs/usage.md)' README.md` prints a number of at least `1`, and `grep -c '](docs/proofs.md)' README.md` prints a number of at least `1`.
- [ ] 4.2 Add `test_the_front_page_fits_one_screen` and its twin to `tests/test_docs.py`, bound to `architecture:readme:one-screen`, per [D9](design.md#d9).
  Verify: `grep -c '"architecture:readme:one-screen"' tests/test_docs.py` prints a number of at least `1`, and `uv run pytest -q` exits 0.

## 5 — ⚠️ **HUMAN** — GitHub's fields and the first CI run

- [ ] 5.1 **HUMAN** — run `gh repo edit alxb1t/gpunit --description "Rent a cloud GPU, use it, and tear it down on every way out — a stdlib-only Python CLI and library. Serves open models over vLLM, proves the host key, and enforces a spend ceiling on the pod itself." --add-topic gpu,cloud-gpu,runpod,vllm,llm-inference,openai-compatible,python,cli,ssh,mlops,self-hosted,cost-control`, per [D11](design.md#d11).
  Verify: `gh repo view alxb1t/gpunit --json repositoryTopics --jq '.repositoryTopics | length'` prints `12`, and `gh repo view alxb1t/gpunit --json description --jq .description | grep -c 'tear it down on every way out'` prints `1`.
- [ ] 5.2 **HUMAN** · **HALT CHECK** — run `git push -u origin v0.11.1_readme_and_docs`, then `gh run watch "$(gh run list --workflow gate.yml --branch v0.11.1_readme_and_docs --limit 1 --json databaseId --jq '.[0].databaseId')"`, per [D11](design.md#d11). A red run is a halt: keep its log.
  Verify: `gh run list --workflow gate.yml --branch v0.11.1_readme_and_docs --status success --limit 1 --json databaseId --jq length` prints `1`.
