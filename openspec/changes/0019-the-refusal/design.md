# Design — 0019 the refusal

A refusal carries its exit code, the lines a caller parses are stated, and a capacity stall is waited out on request.
**Verdict: feasible.**

## Context

Every refusal raises `gpunit/log.py::Refusal` through `log.refuse`, and `gpunit/cli.py::_run` and
`gpunit/run.py::outcome` turn it into `1`. The refusals a capacity stall or a price makes:

| refusal | where | kind |
|---|---|---|
| `no card of gpus is in stock in a data centre with standard volumes…` | `gpunit/volume.py::_datacenter` | no capacity |
| `no card in 'gpus' was placed` — every create a 400 | `gpunit/lifecycle.py::up` | no capacity |
| `no card in 'gpus' meets vram_gb and max_hourly`, after a `skipped:` line per card | `gpunit/lifecycle.py::placeable` | no fit |

Each line is printed and flushed as it happens (`gpunit/log.py::_stderr`). Ctrl-C at `volume up`'s price is a refusal,
`1` (`gpunit/volume.py::_agree`), the audit's F20, which D32 names as a breach. A session's signals raise
`gpunit/library.py::Interrupted` from their handler (`gpunit/library.py::_Signals`), and `lifecycle.CLOCK.sleep` is
`time.sleep`, which a raising handler cuts short. A `ceiling` parses through `gpunit/spec.py::parse_ceiling`.

## Goals / Non-Goals

**Goals:** a caller tells no capacity, no fit and every other refusal apart by the code alone, and reads the reason
from a line of a stated form; a stall in stock is waited out when the spec or a flag asks.

**Non-Goals:** `--json`; a `session()` argument; a wait for anything but capacity; the price prompts' refactor (F9).

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| <a id="d1"></a>**D1** | Exit `4`, **no capacity**: `volume._datacenter`'s no stock, `lifecycle.up`'s none placed. Exit `5`, **no fit**: `lifecycle.placeable`'s no card meets the floor. Every other refusal stays `1`; a lost create `3` | a caller retries a `4` and edits the spec on a `5` | a code per message: the provider's 400 is one kind, capacity |
| <a id="d2"></a>**D2** | `log.Refusal` gains `code: int`, default `1`; `log.refuse(text, code=1)`; `NO_CAPACITY = 4` and `NO_FIT = 5` in `gpunit/log.py`. `cli._run` and `run.outcome` return `refused.code`. `gpunit.Refused` is `log.Refusal`, so a `session()` caller reads `.code` | one exception, one field; only `cli` exits (decision D4) | a subclass per kind: a caller would import more names |
| <a id="d3"></a>**D3** | `volume._agree` on Ctrl-C writes `refused: not created` and re-raises `KeyboardInterrupt`; `cli._run` returns `128 + signal.SIGINT` for a `KeyboardInterrupt` | D32: Ctrl-C is `130` | keeping `1` |
| <a id="d4"></a>**D4** | `docs/usage.md` gains `## The lines a caller reads`: `refused: <reason>`, `skipped: <card> has <n> GB, under <vram_gb>`, `skipped: <card> costs $<hourly>/h, over <max_hourly>`, `no capacity: attempt <n>; next in 60s, waiting until <UTC>`, each after the UTC time; and the exit table's `4` and `5` rows | a stated form is one a caller may parse | `--json`: a code and a line carry it |
| <a id="d5"></a>**D5** | `stock_wait` in `gpunit/spec.py`, a duration through `_duration`, as `Spec.stock_wait_s: int \| None`. `--stock-wait` on `up`, `run`, `serve` and `volume up`, parsed as `--ceiling` is, replaces it (`dataclasses.replace`). `serve` and `volume up --serve` set it on the row's spec in `gpunit/serve/session.py` | the parameter lives in the config; a flag overrides (`serve` has no `gpunit.toml`) | a flag alone |
| <a id="d6"></a>**D6** | One round helper, `gpunit/lifecycle.py::stock_round(attempt, deadline, until) -> bool`: when `CLOCK.monotonic() + STOCK_ROUND_S` is within `deadline`, it writes the attempt line and sleeps `STOCK_ROUND_S = 60`, returning `True`; else `False`. `lifecycle.up` clears `.gpunit/pending` after a round of 400s, then asks it, and marks again before the next round. `volume._datacenter` asks it before reading the stock again. Both take `deadline` and `until` from `lifecycle.stock_deadline(spec)`. `placeable` runs once, before any round | no pending mark outlives a round; a `5` never waits | a loop in each caller |
| <a id="d7"></a>**D7** | A signal ends the wait, nothing rented: in a session, `Interrupted` from the sleep (`128 + n`); at the CLI, `KeyboardInterrupt` to `130`, per [D3](#d3) | isekai's Stop sends SIGINT to its children | a cancel argument |
| <a id="d8"></a>**D8** | D32 amended and D56 added in `docs/decisions.md`, per [The decisions' text](#the-decisions-text). `gpunit/cli.py::USAGE` names `--stock-wait` | the rule review reads | |

No threat-model change (decision D9): no new endpoint or secret; a round repeats the stock read and the create
`gpunit` already makes, and the attempt line names no secret.

## The decisions' text

D32's heading and bold line, before → after:

- before: `### D32 · Exit codes: `0`, `1`, `2`, `3`, `128+n`` and `` **`gpunit` exits `0` on success, `1` on a refusal
  or a failed teardown, `2` on a usage error, `3` on a lost create, and `128+n` on signal `n`.** ``
- after: `### D32 · Exit codes: `0`, `1`, `2`, `3`, `4`, `5`, `128+n`` and `` **`gpunit` exits `0` on success, `1` on
  a refusal or a failed teardown, `2` on a usage error, `3` on a lost create, `4` on no capacity, `5` on no card that
  fits, and `128+n` on signal `n`.** `` Its *Breached* sentence on `gpunit/volume.py::_agree` goes; *Made by* gains
  `0019·D1`.

```markdown
### D56 · A stall in stock is waited out on request

**`stock_wait`, or `--stock-wait`, retries a round that found no capacity every 60 s until the duration passes, then
refuses with `4`; no other refusal waits, and a signal ends the wait with nothing rented.**

`gpunit/lifecycle.py::stock_round` holds the round; `lifecycle.up` and `gpunit/volume.py::_datacenter` ask it.

- **Why:** A data centre's stock runs out for hours, and every caller would write the same retry loop.
- **Made by:** `0019·D6`.
```

## Tests

| layer | adds | removes |
|---|---|---|
| unit | `tests/test_up.py`: `cli:exits:no-capacity-exits-4`, `cli:exits:no-fit-exits-5`, `cli:lines:skipped-forms`, `session:stock:placed-later`, `session:stock:gives-up`, `session:stock:no-fit-never-waits`; `tests/test_library.py`: `session:stock:signal-ends-the-wait`; `tests/test_volume.py`: `volume:stock:found-later`, `volume:stock:ctrl-c-exits-130`, `cli:lines:attempt-form`; `tests/test_spec.py`: `spec:file:stock-wait-duration`; `tests/test_cli.py`: a `--stock-wait` usage case | none |
| end-to-end | none | none |

The suite stands at 567 tests, by `uv run pytest --collect-only -q` at the base. Changed, not removed:
`test_none_placed_exits_1_with_no_record` becomes `test_none_placed_exits_4_with_no_record`;
`test_no_stock_refuses_naming_the_cards` and `test_no_stock_within_the_allow_list_refuses` assert `4`;
`test_an_interrupt_at_the_price_creates_nothing` binds `volume:up:ctrl-c-at-price-exits-130` and asserts `130`. This
change deletes and merges no test.

## Dependencies

None.

## Risks / Trade-offs

- **A caller reading `1` as "no card" breaks** → the CHANGELOG names it; isekai maps `4` and `5`, and is the one
  consumer that reads them.
- **A long wait keeps a terminal busy** → it is opt-in, bounded by the duration, and Ctrl-C ends it.
- **RunPod's rate limits are unmeasured** → one round a minute is a stock read or a create per card.
- **Beside `0018-the-vanished-volume`** → both edit `gpunit/volume.py` and `gpunit/lifecycle.py`, `docs/usage.md`
  and `docs/decisions.md`; `0018` adds D55, so this one adds D56.

## Verdict

**feasible.** Every file and symbol named exists at `bebc030`. Two exit codes and a key are added, so the change is a
minor (decision D8).
