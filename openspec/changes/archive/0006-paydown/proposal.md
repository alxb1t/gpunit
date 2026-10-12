---
version: v0.3.1
backlog: [0003·R2, 0003·S2, 0005·R2, 0005·R3, 0005·R4, 0005·R5, 0005·R6, 0005·R7, 0005·R10, 0003·R3, 0003·R4, 0003·R5, 0005·R8, 0005·R9]
---

# 0006 — paydown

**`v0.3`'s and `v0.1.2`'s open cards closed, and a pod that cannot start stops billing in seconds.** A host key a
command's echo cannot supply, a chat that notices a stopped pod, a serve port that is never busy, a wait that ends on
a dead pod. **A patch: no verb, no `gpunit.toml` key, no exit code.**

| read | for |
|---|---|
| this file | why, and what changes |
| [design](design.md) | each fix, the cards it closes, and why that fix |
| [tasks](tasks.md) | the phases, in build order |
| `specs/` | `session` · `cli` · `serve` |

## Why

**`serve`'s first contact left defects:** the chat keeps prompting a pod that has stopped, a busy port 8000 refuses
only after the price is agreed, and Ctrl-C at the question prints a traceback.

**A pod that never starts bills for the whole wait.** `up` waits `timeout` seconds for a host and a port; `serve`
waits 1200. A dead container stays `EXITED`, and nothing reads that. The cost is real, if small.

**A command's own output can supply the host key** (`0003·S2`): `fingerprint` keeps the last key-shaped line anywhere
in the pod's log.

## What Changes

- **The host key is the one boot printed before the command started** ([D1](design.md#d1), `0003·S2`).
- **A dead pod ends the wait** on two terminal polls in a row ([D2](design.md#d2)).
- **`serve`:** the chat ends when the server cannot be reached; the forward picks a free local port before the price;
  Ctrl-C at the question rents nothing and exits `130`; the row names 24 GB cards only ([D3](design.md#d3),
  `0005·R2`, `R5`, `R6`, `R7`).
- **Text that fell behind the code:** the cli spec's exit codes, README, a `boot.sh` comment, `state.py`'s docstring,
  the `live-serve` comment and the price script ([D4](design.md#d4), `0003·R2`, `0005·R3`, `R4`, `R10`).
- **`CLAUDE.md` states what a patch holds** ([D5](design.md#d5)).
- **`make live-dead`**, the live proof of the dead path ([D6](design.md#d6)).
- **Five cards close moot** — they name an archived change's design or tasks ([D7](design.md#d7)).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `session`:
  - *The wait is bounded and a timeout tears down* — a dead pod on two polls in a row ends the wait.
  - *The host key is verified before anything connects* — the key is the line boot's step line followed.
- `cli`:
  - *The exit codes say what happened* — `128 + n` for `run` and `serve`.
- `serve`:
  - *The model table names what each model serves on* — the forward's local port is given.
  - *Nothing is rented before the operator agrees to the price* — Ctrl-C at the question rents nothing.
  - *A served session waits for the model, within a bound* — a busy local port is skipped.
  - *The chat streams the model's answer in the terminal* — a stopped server ends the chat.

## Impact

- **Files:** `gpunit/provider.py`, `gpunit/lifecycle.py`, `gpunit/run.py`, `gpunit/state.py`,
  `gpunit/serve/table.py`, `gpunit/serve/session.py`, `gpunit/serve/chat.py`, `gpunit/serve/models.toml`,
  `boot/boot.sh` (a comment), `README.md`, `CLAUDE.md`, `Makefile`, `live/price.py`, `live/Dockerfile.dead` (new),
  `live/gpunit.dead.toml` (new), `live/last_run.txt`, and the tests.
- **Behaviour:** `fingerprint` accepts a key only with boot's step line after it; a pod `EXITED` twice ends `up`.
- **Consumers:** `boot.sh`'s bytes change by a comment, so its sha256 at `v0.3.1` differs; an image pinned at an older
  tag is unaffected.
- **Dependencies:** none ([Dependencies](design.md#dependencies)).
- **Spend:** `make live` and `make live-dead` rent a pod each, by hand: `make live` for at most its 10 m ceiling plus
  the 420 s wait for SSH, `make live-dead` for at most its 120 s wait ([D6](design.md#d6)).

## Not in this change

- **A root command forging both lines** — a command that prints the key and the step line itself. Trigger: a command
  run on a pod that is not trusted with the key (README already says to run none).
- **`make live-serve` again** — the serve fixes are covered by fakes and `0005`'s live run.
- **`gpunit spend`, Vast.ai, the larger model row** — their own versions.
