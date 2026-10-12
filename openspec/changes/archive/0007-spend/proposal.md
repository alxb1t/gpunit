---
version: v0.4
---

# 0007 — spend

**`gpunit spend --days 7` answers "what did last week cost?" from the provider's own billing, by project.** A ledger
of the pods gpunit has made gives each pod its project; pods it never recorded, and the volumes you keep, are shown
on lines of their own. **A minor: it delivers one feature, the report.**

| read | for |
|---|---|
| this file | why, and what changes |
| [design](design.md) | the ledger, the billing seam, the report, the window, the proof |
| [tasks](tasks.md) | the phases, in build order |
| `specs/` | `spend` (new) · `cli` |

## Why

**gpunit's sessions bill in four repositories, and nothing totals them.** The week of 2026-10-06 cost $1.79: pods
$1.46 across fifteen pods, storage $0.33. The provider's billing carries only a pod id, and gpunit forgets that id at
teardown, so no one can say which project spent what.

**The storage you keep is the one cost no session shows.** One volume bills $0.047 a day whether or not a pod runs,
18% of last week.

## What Changes

- **A ledger** of pod ids and their projects, written where gpunit first learns an id: the create's answer and the
  sweep's listing; best-effort, never blocking ([D1](design.md#d1)).
- **Two billing reads on the provider seam**, pods and volumes, in day buckets ([D2](design.md#d2)).
- **`gpunit spend [--days N] [--json]`**: the report, its window, the note on the day still billing
  ([D3](design.md#d3), [D4](design.md#d4)).
- **A refusal for an unreadable billing**, never a table of zeros ([D3](design.md#d3)).
- **README and `CLAUDE.md`**; **a read-only live comparison** ([D5](design.md#d5), [D6](design.md#d6)).

## Capabilities

### New Capabilities

- `spend`: the ledger, the report by project, the window.

### Modified Capabilities

- `cli`:
  - *The verbs and the usage exit* — `spend`; a window under one day exits `2`.

## Impact

- **Files:** `gpunit/ledger.py` (new), `gpunit/spend.py` (new), `gpunit/provider.py`, `gpunit/runpod.py`,
  `gpunit/lifecycle.py`, `gpunit/cli.py`, `README.md`, `CLAUDE.md`, `live/spend_last_run.txt` (new), and the tests,
  including `tests/conftest.py` and `tests/fakes.py`.
- **Behaviour:** `up` and `down` append to a file under the home directory; no other verb changes.
- **Dependencies:** none ([Dependencies](design.md#dependencies)).
- **Spend:** none: the report reads billing, which costs nothing.

## Not in this change

- **Estimating a cost from price and seconds** — the provider's figure is the one charged.
- **Attributing storage to a project** — gpunit does not know which volume a project uses beyond its spec.
- **Back-filling the ledger** — pods before this version stay unattributed.
- **A budget warning** — parked, with this version as its prerequisite.
- **A public Python function** — the surface `v0.2` promised stays as it is.
