# Design — 0016 readme and docs

How gpunit gets a license, a front page, a CI badge and its GitHub metadata, and where README's guide and proofs go.
**Verdict: feasible.** Every piece is a file placed or moved. The one unknown is whether the gate passes on Linux, and
the first CI run answers it ([D11](#d11)).

## Context

See [proposal](proposal.md) — *Why*. Terms used throughout:

- **the front page** — `README.md` after this change: one screen, linking out.
- **the user's guide** — README's content today, from *Use it from a project* through *The spend rules*.
- **the proof section** — README's *The proof — `make live`*.

What holds at the cut, `main` at `4510f70` (`v0.11.0`):

- **No license:** no `LICENSE` file in the history (`git log --all -- LICENSE` prints nothing); `pyproject.toml` names
  none; `gh repo view --json licenseInfo` prints `null`.
- **`pyproject.toml`:** `description = "Open, use and close a RunPod GPU session from any project."`, no `keywords`,
  `readme = "README.md"`, `[build-system] requires = ["hatchling"]`.
- **GitHub:** `gh repo view --json description,repositoryTopics` prints an empty description and `null` topics.
- **The one workflow:** `.github/workflows/build-serve-image.yml`, on `workflow_dispatch` alone. Its actions are pinned
  by commit, held by `tests/test_serve_image.py::test_each_action_is_pinned_by_commit` on that file alone.
- **README:** 432 lines. Headings: *Use it from a project*, *Use it from Python*, *Serve a model* (with *Your own
  rows*, *From a container*), *Working window*, *What it cost*, *Security and privacy* (with *Where your data lands*,
  *Secrets*, *The account key*, *Accepted risks*), *The verbs*, *The spend rules*, *The proof — `make live`*. Its links
  are relative to the root: `docs/threat-model.md`, `live/tool_call.py`, `live/serve_dead.py`.
- **Who cites README:** `docs/threat-model.md` on 27 lines (`grep -c README docs/threat-model.md`) — *README step 2*,
  *step 3*, and its section names; `docs/extending.md` (*The verbs*, *Use it from a project*, *Serve a model*);
  `docs/pins.md` (*Use it from a project*); `docs/README.md`'s opening line.
- **`tests/test_docs.py`** scans `docs/` for links, backticked paths, `path::symbol` citations and line citations,
  and `README.md` and `CLAUDE.md` for links. Text moved into `docs/` meets the stricter rules.
- **The tails:** `live/last_run.txt`, `live/serve_last_run.txt` and `live/spend_last_run.txt`, each run under a dated
  heading naming its change.
- **The backlog:** `0015·R7`, `drift`, targets the archived `0015` design.

## Goals / Non-Goals

**Goals:** a stranger learns what gpunit is, why to trust it, and how to try it, in one screen; every claim is one click
from what holds it; the gate's result is visible without a clone.

**Non-Goals:** new behaviour; the write-up; PyPI; a recording; Releases for older tags.

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| [D1](#d1) | Apache-2.0: `LICENSE`, `license = "Apache-2.0"`, `license-files = ["LICENSE"]` | open source, as isekai is | no license |
| [D2](#d2) | `pyproject.toml`'s `description` and `keywords` are the text; GitHub mirrors it | Infra as Config: the text is versioned | editing GitHub alone |
| [D3](#d3) | `.github/workflows/gate.yml`: one `ubuntu-latest` job, uv, the OpenSpec CLI by npm, `make gate` | the gate's result shows without a clone | a matrix; the live proofs in CI |
| [D4](#d4) | README is a one-screen front page | the operator's call: terse, one screen | a showcase section above the guide |
| [D5](#d5) | `docs/usage.md` takes the user's guide whole | each depth one link away; the guide survives | trimming the guide |
| [D6](#d6) | `docs/proofs.md` takes the proof section and the dated runs | the evidence in one place, not on the front page | proofs on README; proofs in usage |
| [D7](#d7) | every README citation follows its section | the move must break no reference | — |
| [D8](#d8) | D52 and D53 in `docs/decisions.md` | A7: a decision made edits the page | — |
| [D9](#d9) | tests hold the front page's length and the workflows | a rule no test holds drifts | — |
| [D10](#d10) | `0015·R7` closes won't-fix | an archived change is a record (decision D7) | editing the archive |
| [D11](#d11) | GitHub's fields set by hand from `pyproject.toml`; the first green CI run is the halt check | the settings live on GitHub; the gate has run on macOS alone | — |

### D1

`LICENSE` is the Apache License 2.0 text, unmodified, from <https://www.apache.org/licenses/LICENSE-2.0.txt>. In
`pyproject.toml`'s `[project]`: `license = "Apache-2.0"` and `license-files = ["LICENSE"]`. These need hatchling
1.27 or later: `[build-system]` becomes `requires = ["hatchling>=1.27"]`.

### D2

```toml
description = "Rent a cloud GPU, use it, and tear it down on every way out."
keywords = ["gpu", "cloud-gpu", "runpod", "vllm", "llm-inference", "openai-compatible", "python", "cli", "ssh", "mlops", "self-hosted", "cost-control"]
```

The GitHub description is the long form:

> Rent a cloud GPU, use it, and tear it down on every way out — a stdlib-only Python CLI and library. Serves open
> models over vLLM, proves the host key, and enforces a spend ceiling on the pod itself.

The GitHub topics are the `keywords`, in order. No homepage URL.

### D3

```yaml
# Run the gate on every push and pull request: the offline tests, never a live proof. Why: decision D53.
name: gate

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0
      - name: Install the OpenSpec CLI at the version CLAUDE.md records
        run: npm install -g @fission-ai/openspec@1.11.0
      - run: make gate
```

`docs/pins.md`'s OpenSpec row becomes: declared in `CLAUDE.md` and `.github/workflows/gate.yml`; checked by
`tests/test_ci.py`; moved by editing both.

### D4

The front page, at most 60 lines:

```
 # gpunit                                    [gate badge] [license badge]
 one line: D2's description
 ┌ the diagram: laptop ⇄ pod — up · tunnel · command · down; the ceiling ┐
 ## Why          two sentences: the RunPod scripts copied between projects, drifted apart
 ## Built so     a table, one row a claim, linking the decision that holds it
 ## Try it       a gpunit.toml of a few lines; the install line; gpunit run -- nvidia-smi
 ## Read more    usage · proofs · the guide · threat model · CHANGELOG · LICENSE
```

The *Built so* rows, each linking its decisions in `docs/decisions.md`:

| claim | decisions |
|---|---|
| the host key is proven over the provider's log, with a session nonce, before anything connects | D22 |
| the pod enforces its own spend ceiling, with the laptop asleep | D25, D46 |
| teardown on every way out; a 404 is never "gone" | D20, D23 |
| nothing is rented without the price and a `y` | D35 |
| the standard library alone; `boot.py` at 100 % coverage | D1, D5 |
| the layers and the docs held by tests | D49, D50 |

No count, no price and no live run on the front page. The gate badge is
`https://github.com/alxb1t/gpunit/actions/workflows/gate.yml/badge.svg`, linking the workflow's runs. The license
badge is `https://img.shields.io/badge/license-Apache--2.0-blue`, linking `LICENSE`. *Try it*'s install line is
`docs/usage.md`'s step 3 line, `uv add --dev git+https://github.com/alxb1t/gpunit@<tag>`; the release bumps both.

### D5

`docs/usage.md` opens with one line: how to use gpunit, from a project, from Python, and through `serve`. Then come
README's sections from *Use it from a project* through *The spend rules*, whole, headings and anchors unchanged. Each
link is rewritten for its new directory: `docs/threat-model.md` → `threat-model.md`, `live/tool_call.py` →
`../live/tool_call.py`. Text that `tests/test_docs.py`'s stricter `docs/` rules fault is fixed to cite a path that
exists, or a symbol.

### D6

`docs/proofs.md` opens with what the proofs are: real pods and volumes, rented by hand, never in CI, the price
printed first (decision D6). Then:

- **The latest runs**, dated and quoted from their tails, each linking the tail:
  - `make live` — placed, host key verified, torn down: `live/last_run.txt`, 2026-10-19, `0015-architecture-and-docs`;
  - a dead container ended by the dead-pod rule: `live/last_run.txt`, its latest `make live-dead`;
  - a tool call on the `qwen3.8-27b` row, and a user-file row served: `live/serve_last_run.txt`;
  - spend matched the console to the cent: `live/spend_last_run.txt`, 2026-10-12.
- **One section a target** — `make live`, `make live-volume`, `make live-serve`, `make live-dead`,
  `make live-serve-dead`: what it proves, its ceiling as a bound, and its latest dated run. The text is README's proof
  section, moved.

Each quote is a line the tail holds, word for word.

### D7

| file | before → after |
|---|---|
| `docs/threat-model.md` | each `README step N` → `docs/usage.md` step N; each `README *Section*` → `docs/usage.md` *Section*, as a link where the cell holds one |
| `docs/extending.md` | `README.md`'s *The verbs*, *Use it from a project*, *Serve a model* → `docs/usage.md`'s; § *A live proof* adds "edit `docs/proofs.md`" |
| `docs/pins.md` | `README.md`'s *Use it from a project* → `docs/usage.md`'s; the OpenSpec row per [D3](#d3) |
| `docs/README.md` | the opening line points users to [usage](usage.md); the map gains `usage` and `proofs` rows |

### D8

`docs/decisions.md` gains, under *The guide*:

- **D52 · README is a one-screen front page.** README holds at most 60 lines: what gpunit is, why, how it is built,
  how to try it. The user's guide is `docs/usage.md`, the live proofs `docs/proofs.md`. *Why:* a reader and a user each
  find their depth one link away. *Made by:* `0016·D4`, `0016·D5`, `0016·D6`.
- **D53 · Every push runs the gate.** `.github/workflows/gate.yml` runs `make gate` on each push and pull request; the
  live proofs stay by hand (decision D6). *Why:* the gate's result shows without a clone. *Made by:* `0016·D3`.

D1's *Made by* gains `0016·D1` for the license.

### D9

| test | key |
|---|---|
| `tests/test_docs.py::test_the_front_page_fits_one_screen` and its twin at 61 lines | `architecture:readme:one-screen` |
| `tests/test_ci.py::test_the_gate_workflow_runs_the_gate` and its twin with a third trigger | `architecture:ci:runs-the-gate` |
| `tests/test_ci.py::test_every_workflow_pins_its_actions` and its twin with a tag | `architecture:ci:actions-pinned` |

`test_the_gate_workflow_runs_the_gate` reads the OpenSpec version from `CLAUDE.md`'s
`@fission-ai/openspec@<version>`, and finds it in the workflow. `tests/test_serve_image.py::test_each_action_is_pinned_by_commit`
stays: it holds the serve image's own scenario.

### D10

`0015·R7` names the archived `0015` design. An archived change is a record (decision D7), so the card closes won't-fix,
listed in this change's `backlog:`. The rules as they hold are `tests/test_layers.py` and `tests/test_docs.py`, and
`docs/decisions.md` D49 and D50.

### D11

The settings live on GitHub, so a person sets them, from the text in `pyproject.toml`:

```
gh repo edit alxb1t/gpunit --description "<D2's long form>" \
  --add-topic gpu,cloud-gpu,runpod,vllm,llm-inference,openai-compatible,python,cli,ssh,mlops,self-hosted,cost-control
```

Then the branch is pushed, and the gate workflow's first run must pass. It is the halt check: the gate has run on macOS
alone. A red run is a halt, and its log names what Linux broke.

After `mf-release`, by hand, outside this change: `gh release create v0.11.1` with CHANGELOG's `[0.11.1]` section.

## Dependencies

None. Hatchling is the build backend already; [D1](#d1) raises its floor.

## Risks / Trade-offs

- [The gate fails on Linux: a macOS-only path, `ps -E`, a stub on `PATH`] → [D11](#d11)'s halt check; the run's log
  names it, and a fix lands in this change.
- [`docs/usage.md` meets `tests/test_docs.py`'s path and symbol rules README never met] → [D5](#d5) fixes each in the
  move.
- [A reader's bookmark to a README anchor] → it lands on the front page, which links usage.
- [The OpenSpec version is recorded in two places] → `tests/test_ci.py` holds them equal.

## Verdict

Feasible. The files are placed or moved, the tests are small, and the one unknown is answered by the first CI run.
