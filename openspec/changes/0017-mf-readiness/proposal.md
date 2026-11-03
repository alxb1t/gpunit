---
bump: patch
---

# 0017 — mf readiness

**gpunit made ready for `mf-ship`: a gate that passes inside a sandboxed worker, the root documents MinionsFactory's
review reads by name, and a protected `main`.** No behaviour of gpunit changes.

| read | for |
|---|---|
| this file | why, and what changes |
| [design](design.md) | the decisions, the tests moved, the root documents, the GitHub side |
| [tasks](tasks.md) | the phases, in build order |
| `specs/` | `architecture` |

## Why

**`mf-ship` runs every phase's `make gate` inside an OS sandbox that refuses a bind on loopback.** Measured under a
real worker at `55fdae3`, the gate exits 2: 34 tests fail at `gpunit/serve/session.py::_free_port`'s bind, 31 error at
a loopback server, and the redirect tests fail through the sandbox's proxy. MinionsFactory's `0056-loopback-removal`
takes loopback away from every worker for good.

**MinionsFactory's review reads `THREAT_MODEL.md`, `ARCHITECTURE.md`, `CODING_STANDARDS.md` and `CONTRIBUTING.md` at
the root.** gpunit keeps the first two in `docs/` and lacks the last two, so their review sections read `inconclusive`.
`main` has no protection, and an unattended release pushes to it.

## What Changes

- **The gate runs sandbox-safe:** `_free_port` is faked in the tests that only pass through it
  ([D1](design.md#d1)); the tests whose proof is a real loopback socket carry an `e2e` mark and run in `make e2e`,
  out of the gate ([D2](design.md#d2)); the redirect tests clear the proxy variables ([D3](design.md#d3)).
- **CI runs both:** `.github/workflows/gate.yml` runs `make e2e` after `make gate` ([D4](design.md#d4)).
- **D54** records the rule in `docs/decisions.md` ([D5](design.md#d5)).
- **`docs/threat-model.md` becomes `THREAT_MODEL.md`**, and gains the worker and the accepted `.env`
  ([D6](design.md#d6)). **`docs/README.md` becomes `ARCHITECTURE.md`** ([D7](design.md#d7)).
- **`CODING_STANDARDS.md` and `CONTRIBUTING.md`** from MinionsFactory's templates; the rules for a change move from
  `AGENTS.md` into `CONTRIBUTING.md` ([D8](design.md#d8)).
- **`AGENTS.md` names its mandatory context**, and the links test holds the root documents ([D9](design.md#d9)).
- **A ruleset on `main`**, by a person; GitHub's push protection is on already ([D10](design.md#d10)).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `architecture`:
  - *The guide's citations resolve*: the links checked are `docs/`, `README.md` and the root documents
    `AGENTS.md`, `ARCHITECTURE.md`, `THREAT_MODEL.md`, `CODING_STANDARDS.md` and `CONTRIBUTING.md`, in place of
    `CLAUDE.md`.
  - *Every push runs the gate*: the gate workflow also runs `make e2e`, and the OpenSpec version is the one
    `CONTRIBUTING.md` records.

## Impact

- **Tests:** `tests/conftest.py`, `tests/test_library.py`, `tests/test_run.py`, `tests/test_serve_chat.py`,
  `tests/test_tool_call.py`, `tests/test_serve_session.py`, `tests/test_runpod.py`, `tests/test_boot_steps.py`,
  `tests/test_docs.py`, `tests/test_ci.py`. None deleted; the moved ones run in `make e2e`.
- **Build:** `Makefile` (`e2e`, and the gate's `pytest` line), `pyproject.toml` (the `e2e` marker),
  `.github/workflows/gate.yml`.
- **Docs:** `AGENTS.md`, `THREAT_MODEL.md` and `ARCHITECTURE.md` (moved), `CODING_STANDARDS.md` and `CONTRIBUTING.md`
  (new), `README.md`, `docs/decisions.md`, `docs/extending.md`, `docs/pins.md`, `docs/principles.md`, `docs/usage.md`.
- **GitHub:** a ruleset on `main`. Secret scanning and push protection stay as they are, on.
- **Consumers:** none break. No verb, `gpunit.toml` key, message or exit code moves.
- **Dependencies:** none ([Dependencies](design.md#dependencies)).
- **Spend:** none. No live run.

## Not in this change

- **A behaviour change of gpunit**: no spec scenario of a verb, message or exit code moves (decision D8).
- **Reading the docs again for currency and style.** Trigger: the next version that opens the root documents.
- **A conductor-side guard against a secret in a commit.** MinionsFactory's, not gpunit's.
- **Dropping the `CLAUDE.md` link to `AGENTS.md`.** It stays, so Claude Code still loads the context.
- **A Codex station.** Trigger: a converge on Codex behind gpunit.
