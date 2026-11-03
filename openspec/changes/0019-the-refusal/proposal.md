---
bump: minor
---

# 0019 — the refusal

**A refusal a caller can act on: exit `4` for no capacity and `5` for no card that fits, the `refused:` and `skipped:`
lines a documented contract, and an opt-in wait, `stock_wait`, that retries placement through a capacity stall.**

| read | for |
|---|---|
| this file | why, and what changes |
| [design](design.md) | the codes, the lines, the wait, the signals, the tests |
| [tasks](tasks.md) | the phases, in build order |
| `specs/` | `cli`, `spec`, `session`, `volume` |

## Why

**Every refusal exits `1`, and its reason reaches only the log.** isekai's app can say no more than *did not open the
window (exit 1)*: it cannot tell a card out of stock, worth a retry, from a card over `max_hourly`, fixed only by
editing the spec. **EU-RO-1 runs out of stock for hours**, and the workaround is an operator's 60 s retry loop, which
every caller would write again.

## What Changes

- **Exit `4`, no capacity; exit `5`, no card that fits** ([D1](design.md#d1)); a refusal carries its code
  ([D2](design.md#d2)). **D32** is amended.
- **Ctrl-C at `volume up`'s price exits `130`**, the audit's F20 ([D3](design.md#d3)).
- **The lines are a contract:** `refused:`, both `skipped:` forms and the attempt line, in `docs/usage.md`
  ([D4](design.md#d4)).
- **`stock_wait`**, a `gpunit.toml` duration, and `--stock-wait` on `up`, `run`, `serve` and `volume up`
  ([D5](design.md#d5)). On a `4` alone, the round is tried again every 60 s ([D6](design.md#d6)); a signal ends the
  wait ([D7](design.md#d7)). **D56** records it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cli`:
  - *The refusal's lines are a contract* (added): the four line forms.
  - *The verbs and the usage exit*: `--stock-wait` on `up`, `run`, `serve` and `volume up`.
  - *The exit codes say what happened*: `4`, `5`, and `130` at `volume up`'s price.
- `spec`:
  - *The spec is one TOML file*: the `stock_wait` key.
- `session`:
  - *A stall in stock is waited out when asked* (added): the rounds, the give-up, the signals.
  - *A GPU is placed from the preference list*: `5` when no card fits, `4` when none was placed.
- `volume`:
  - *Volume up waits out a stall in stock when asked* (added): the stock reread, Ctrl-C.
  - *A window volume is created from the spec*: no stock exits `4`; Ctrl-C at the price exits `130`.

## Impact

- **Code:** `gpunit/log.py`, `gpunit/cli.py`, `gpunit/run.py`, `gpunit/spec.py`, `gpunit/lifecycle.py`,
  `gpunit/volume.py`, `gpunit/serve/session.py`.
- **Tests:** `tests/test_up.py`, `tests/test_volume.py`, `tests/test_spec.py`, `tests/test_cli.py`,
  `tests/test_library.py`.
- **Docs:** `docs/decisions.md` (D32, D56), `docs/usage.md` (the exit codes, the lines, the key).
- **Consumers:** **a breaking change for a caller that reads `1` as "no card".** No capacity is `4`, no fit is `5`.
  `gpunit.Refused` gains `code`. isekai's app maps both.
- **Dependencies:** none ([Dependencies](design.md#dependencies)).
- **Spend:** none. No live run.

## Not in this change

- **The vanished volume.** Change `0018-the-vanished-volume`, beside this one.
- **`--json` output.** Trigger: a caller that cannot read an exit code and a line.
- **A `session()` argument for the wait.** Trigger: a caller that cannot set `stock_wait` in its spec.
- **One price prompt (the audit's F9).** Trigger: the paydown that closes the backlog.
- **A registry credential.** Trigger: a measured pull an authenticated registry would speed.
