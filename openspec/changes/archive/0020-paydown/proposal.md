---
bump: patch
version: v0.12.1
backlog: [0014·R5, 0014·R6, 0014·S1, 0014·S2, 0017·R6, 0017·R7, 0017·S1, 0017·S3, 0019·S2]
---

# 0020 — paydown

**The backlog closed: a user row can no longer repin its model or turn request logging on, the threat model's worker
row says what a worker really sends, and a wait for stock guards its checkout.**

| read | for |
|---|---|
| this file | why, and what changes |
| [design](design.md) | the flag rule, the launcher, the threat model's rows, the wait mark, the image |
| [tasks](tasks.md) | the phases, in build order |
| `specs/` | `serve`, `session`, `volume` |

## Why

**A row's checks match exact flag names, and vLLM `v0.31.0` does not.** It takes argparse abbreviations and rewrites
argv, so `--revisio main` repins a row past `_LAUNCHERS`, and `--enable_log_requests` or a trailing dotted flag turns
request logging on. T13, T30 and T55 say the pin and the quiet hold (`0014·R5`, `S1`, `S2`; the scenario `0014·R6`).
**The worker row's accept rests on a misstated flow:** a worker sends what it reads to its model provider, not only a
pushed commit (`0017·S1`, `S3`). **A wait for stock leaves the checkout unguarded** (`0019·S2`).

## What Changes

- **One flag rule** in `gpunit/serve/table.py::_args` and `serve/launch.py` ([D1](design.md#d1),
  [D2](design.md#d2)); T13, T30, T55 and `docs/usage.md` say what holds ([D3](design.md#d3)).
- **The worker row, G17 and T20 told true** ([D4](design.md#d4)).
- **`.gpunit/waiting`** guards a wait for stock ([D5](design.md#d5)).
- **The serve image rebuilt** on the branch and its digest re-pinned, so pods run the new launcher
  ([D6](design.md#d6)).
- **`0017·R6` and `R7` close won't-fix**: they name the archived `0017`'s artefacts, a record (decision D7)
  ([D7](design.md#d7)).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `serve`:
  - *The model table names what each model serves on*: the flag rule, with scenarios for the launcher flags and the
    logging families.
  - *The serve image is built on request and pinned*: the launcher refuses a row the table refuses.
- `session`:
  - *One live session per project*: a live `.gpunit/waiting` refuses `up`; a stale one is removed.
  - *A stall in stock is waited out when asked*: the mark from the first wait, removed on every way out.
- `volume`:
  - *Volume up waits out a stall in stock when asked*: the same mark.

## Impact

- **Code:** `gpunit/serve/table.py`, `serve/launch.py`, `gpunit/lifecycle.py`, `gpunit/state.py`, `gpunit/volume.py`,
  `gpunit/serve/models.toml` (the digest).
- **Tests:** `tests/test_serve_table.py`, `tests/test_serve_image.py`, `tests/test_up.py`, `tests/test_volume.py`,
  `tests/test_state.py`.
- **Docs:** `THREAT_MODEL.md` (T13, T20, T30, T55, the worker row, G17), `docs/usage.md`.
- **Consumers:** a user row holding an abbreviated or rewritten flag, `--tokenizer` among them, is now refused.
- **GitHub:** one manual run of `build-serve-image.yml`; it pushes an image to GHCR and rents nothing.
- **Dependencies:** none ([Dependencies](design.md#dependencies)).
- **Spend:** none. No live run.

## Not in this change

- **One price prompt (the audit's F9).** Trigger: the seam's refactor.
- **A deny-read of `.env` in a worker's sandbox.** MinionsFactory's, not gpunit's.
- **A `make live-serve` on the new image.** Trigger: the next serve change that rents a pod.
