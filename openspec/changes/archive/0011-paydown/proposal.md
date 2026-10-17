---
version: v0.7.1
backlog: [0010·R4, 0010·R5, 0010·R6, 0010·R7, 0010·R8, 0010·R9, 0010·R10, 0010·R11, 0010·S3, 0010·S4]
---

# 0011 — paydown

**`0010`'s open cards closed.** A live volume's end only moves later, a deleted volume is recorded and not warned
about, `serve` sweeps before it prices, an older `boot.sh` is judged only on a read from the log's start, and the
lost-create sweep stops at Ctrl-C and takes no piped answer. **A patch: no verb, no `gpunit.toml` key, no exit code.**

| read | for |
|---|---|
| this file | why, and what changes |
| [design](design.md) | each fix, the cards it closes, and why that fix |
| [tasks](tasks.md) | the phases, in build order |
| `specs/` | `volume` · `spend` · `session` · `cli` |

## Why

**`v0.7.0`'s converge left its cards in `.minions/backlog.md`.** Most are small: a text that fell behind the code, a
test weaker than its scenario. These are not:

- **A piped `y` deletes an unrecorded volume** (`0010·S3`). `echo y | gpunit volume down` answers the sweep's question
  with no person in sight, and a teammate's volume of the same project carries the same name.
- **A second `volume up` can pull a window's end in** under a running session (`0010·R4`), and the next command
  then deletes the volume under it.

## What Changes

- **`volume up` on a live volume never moves its end earlier** ([D1](design.md#d1), `0010·R4`).
- **The overdue sweep clears the pending mark** when it deletes a recorded volume beside it
  ([D2](design.md#d2), `0010·S4`).
- **`serve` sweeps an overdue volume before the price**, and refuses before the price when that leaves no window
  ([D3](design.md#d3), `0010·R6`).
- **Ctrl-C ends the lost-create sweep** with exit `130`, the volume asked about, the rest and the mark kept
  ([D4](design.md#d4), `0010·R9`).
- **A stdin that is not a terminal is no answer** to the sweep's question ([D5](design.md#d5), `0010·S3`).
- **The lost-create message says `volume down` asks first; the ledger-skip test reads stderr too**
  ([D6](design.md#d6), `0010·R10`, `0010·R11`).
- **Every volume delete appends a `deleted` line to the ledger; `spend` names no deleted volume**
  ([D7](design.md#d7), `0010·R5`).
- **An older `boot.sh` is judged only on a read that opens with boot's `step: the ceiling` line**
  ([D8](design.md#d8), `0010·R7`).
- **`0010·R8` closes won't-fix** — it names archived text ([D9](design.md#d9)).
- **`make live-volume`**, run by hand on a real volume ([D10](design.md#d10)).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `volume`:
  - *A live window volume is extended* — the end becomes the later of the recorded end and now plus `volume_ceiling`.
  - *The window volume is deleted by its verb* — a stdin that is not a terminal is no answer; Ctrl-C ends the sweep
    with exit `130`.
  - *A window volume past its ceiling is deleted by the next command* — the sweep clears a pending mark beside the
    record; `serve` sweeps and refuses before the price.
- `spend`:
  - *The ledger names each pod gpunit learns of* — a volume's delete appends a `deleted` line, with its keys.
  - *Spend reports the provider's billing by project* — a window volume the ledger records as deleted is not named.
- `session`:
  - *The host key is verified from the log's tail before anything connects* — an older `boot.sh` is judged only on a
    read opening with boot's `step: the ceiling` line.
- `cli`:
  - *The exit codes say what happened* — `128 + n` also when Ctrl-C ends `volume down`'s sweep.

## Impact

- **Files:** `gpunit/volume.py`, `gpunit/lifecycle.py`, `gpunit/ledger.py`, `gpunit/spend.py`,
  `gpunit/provider.py`, `gpunit/serve/session.py`, `README.md`, `live/last_run.txt`, and the tests.
- **The `Provider` seam:** unchanged.
- **The ledger:** gains a `deleted` line. An older gpunit reading it skips the line: it lacks the keys a pod's or a
  volume's line needs.
- **Consumers:** none; `boot.sh` and the images do not change.
- **Dependencies:** none ([Dependencies](design.md#dependencies)).
- **Spend:** `make live-volume` costs ~$0.10, by hand.

## Not in this change

- **A `--yes` for the sweep** — a delete of an unrecorded volume needs a person; such a volume goes through the
  console or the RunPod MCP by hand ([D5](design.md#d5)).
- **Editing `0010`'s archived proposal** — an archived change is a record ([D9](design.md#d9)).
- **A seam that says when a log read was cut** — boot's first line tells a whole read apart ([D8](design.md#d8)).
- **What isekai's and Synthetic Portraits' working windows find** — trigger: their builds on `v0.7.0` report a
  defect.
- **`make live`, `make live-dead`, `make live-serve` and `make live-serve-dead`** — `volume.py` is the one file
  whose edges a real volume shows; the rest are proven offline.
