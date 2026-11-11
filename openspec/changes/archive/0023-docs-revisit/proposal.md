---
bump: patch
version: 0.12.4
---

# Docs revisit

The root files and `docs/` read again after readiness's moves, the seam and gone pod: current with the code, and read well.

Reading map: [design](design.md) holds the decisions, the new page shapes and the test cost, [tasks](tasks.md) holds the phases: currency, one home, the readers' pages.

## Why

The docs fell behind the seam, the gone pod and readiness. `ARCHITECTURE.md` draws RunPod where the `Provider` seam now stands, `docs/usage.md` gives a wrong exit code and a wrong step for a crash, and the threat model names a variable `_command` no longer drops.
The same rules are said in several places and have drifted, and the longest pages put the contract last.

A test that holds the root documents' citations keeps "current with the code" true after this version.

## What Changes

- `tests/test_docs.py` reads the root documents as well as `docs/*.md` for backticked paths, `path::symbol` citations and line citations ([D4](design.md#d4)).
- Every stale claim of the brief's facts is fixed against the code ([D3](design.md#d3)); `pod_gone`'s comment cites D57 ([D1](design.md#d1)).
- A rule has one home: the gone rule in D57, the change rules in `CONTRIBUTING.md`, the key's exposure in `docs/usage.md`'s *The account key*, the install pin in `docs/usage.md` ([D5](design.md#d5), [D7](design.md#d7), [D9](design.md#d9)).
- `docs/decisions.md` keeps every id and title but the archive rule's and the patch rule's, which say what their bodies say; the gone-rule decisions move to their sections ([D7](design.md#d7)).
- `THREAT_MODEL.md` drops its version stamps and keeps a row to the threat, its mitigation, its status and its citations ([D8](design.md#d8)).
- `docs/usage.md` is reordered and its security section thinned to links ([D6](design.md#d6)).
- `README.md`, `AGENTS.md`, `ARCHITECTURE.md`, `CODING_STANDARDS.md` and `CONTRIBUTING.md` are rewritten to read well ([D10](design.md#d10), [D11](design.md#d11), [D13](design.md#d13), [D14](design.md#d14), [D15](design.md#d15)).
- `docs/principles.md` claims what its holder checks ([D16](design.md#d16)).
- Requirement *The guide's citations resolve* (MODIFIED): its path, symbol and line citations are held in the root documents too.
- Requirement *The modules import down the layers, and RunPod only through providers* (ADDED): the old requirement's rules and scenario keys, the scenario `architecture:layers:provider-built` retitled to say what it checks.
- Requirement *The modules import down the layers* (REMOVED): renamed by the line above, since a strict delta cannot retitle a scenario in place.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `architecture`: the citation requirement reaches the root documents; one scenario title is true again, through a renamed requirement.

## Impact

- Prose: `README.md`, `AGENTS.md`, `ARCHITECTURE.md`, `THREAT_MODEL.md`, `CODING_STANDARDS.md`, `CONTRIBUTING.md`, and `docs/usage.md`, `docs/data-flow.md`, `docs/decisions.md`, `docs/principles.md`, `docs/extending.md`, `docs/modules.md`, `docs/proofs.md`.
- Code: one comment in `gpunit/lifecycle.py`, no behaviour.
- Test: `tests/test_docs.py`, one function widened and one test extended.
- No verb, config key, exit code or message changes ([D2](design.md#d2)).

## Not in this change

- A live re-proof — before v1.0, on the roadmap ([D12](design.md#d12)).
- F9, F10, F14 and the `provider` key — Vast.ai's.
- Any behaviour, message, exit code or config key ([D8 of the decisions](../../../docs/decisions.md)); no decision added or overturned.
- A new page: `docs/usage.md` stays one page ([D6](design.md#d6)).
