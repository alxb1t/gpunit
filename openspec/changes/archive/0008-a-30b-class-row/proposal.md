---
version: v0.5
---

# 0008 — a 30B-class model row

**`gpunit serve qwen3.8-27b --ceiling 1h` — a second row in the model table, on a 48 GB card.** Qwen3.8-27B at FP8,
pinned, with the tool-call flags its family needs, and a live check that it answers a tool-calling request under the
pinned vLLM. **A minor: it delivers one feature, a second served model. It adds no verb, flag or `gpunit.toml` key.**

| read | for |
|---|---|
| this file | why, and what changes |
| [design](design.md) | the row, the cards, the check, the live proof |
| [tasks](tasks.md) | the phases, in build order |
| `specs/` | `serve` |

## Why

**The test row cannot be what an agent works with.** `qwen3-4b` proves `serve`; a 4B model is too small to drive
Hermes. The founding choice, Qwen3-30B-A3B, is two model generations old: Qwen3.5, Qwen3.6 and Qwen3.8 have followed,
all in the `qwen3_5` family, and the newest dense 27B at FP8 fits one 48 GB card.

**Its tool calls are the point, and its flags differ.** The family's tool-call parser is `qwen3_coder`, not the `hermes`
of the 4B row; whether it answers a tool request under the pinned vLLM is a fact only a live run shows.

## What Changes

- **The row `qwen3.8-27b`** in `gpunit/serve/models.toml`: the repository at its pinned revision, the card list, the
  flags ([D1](design.md#d1), [D2](design.md#d2)).
- **`live/tool_call.py`**, the check, with an offline test ([D3](design.md#d3)).
- **`make live-serve` takes `MODEL`** and runs the check beside the chat and the `--api` request ([D4](design.md#d4)).
- **README** names the second row ([D5](design.md#d5)).
- **A metered proof**: `make live-serve MODEL=qwen3.8-27b` once ([D6](design.md#d6)).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `serve`:
  - *The model table names what each model serves on* — the table holds the second row; a scenario for its flags and
    cards.
  - *A row's tool-calling is proved by a check* (added) — the check passes on a tool call and fails on text, bad
    arguments, or a key on its command line.

## Impact

- **Files:** `gpunit/serve/models.toml`, `live/tool_call.py` (new), `Makefile`, `README.md`,
  `live/serve_last_run.txt`, `tests/test_serve_table.py`, `tests/test_cli.py`, `tests/test_tool_call.py` (new).
- **Behaviour:** `gpunit serve qwen3.8-27b` becomes a valid model; every other verb is unchanged.
- **The image** is unchanged: no build, no new digest.
- **Dependencies:** none ([Dependencies](design.md#dependencies)).
- **Spend:** `make live-serve MODEL=qwen3.8-27b` rents one 48 GB card for at most the printed maximum, by hand
  ([D6](design.md#d6)).

## Not in this change

- **The MoE row `Qwen3.6-35B-A3B-FP8`** — trigger: Hermes running on the dense row and wanting more tokens a second.
- **A per-row wait** — trigger: the live proof's cold load passing the 1200 s bound.
- **A default model** — `serve` still takes the model by name.
- **A bind address, a volume's lifecycle, a new image.**
