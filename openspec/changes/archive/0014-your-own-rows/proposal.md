---
version: v0.10
backlog: [0013·R1, 0013·R2, 0013·R3, 0013·R5, 0013·R6, 0013·R7, 0013·S4, 0013·S5]
---

# 0014 — your own rows

**`gpunit serve <row>` reads rows from the operator's own file, `~/.config/gpunit/models.toml` by default, beside the
bundled ones,** so the models a person runs never sit in a tracked file. Request logging and telemetry are always off,
set by the image's launcher whatever a row says. The `0013` cards that `v0.9`'s release left open close here.

| read | for |
|---|---|
| this file | why, and what changes |
| [design](design.md) | the lookup, the merge, the checks, the launcher, the flag, the docs, the cards, the proof |
| [tasks](tasks.md) | the phases, in build order |
| `specs/` | `serve` · `cli` |

## Why

**Every model `serve` knows is a row of the tracked `gpunit/serve/models.toml`.** A person who serves another model
edits gpunit's repo, and a project's choice of model lands in gpunit's history. `0010`'s *Not in this change* set the
trigger, "a `serve` user running the same row every day", and it is met.

**A row from outside the repo must not turn logging on.** In `v0.9` each bundled row carries
`--no-enable-log-requests`, and the image sets the telemetry variables. A row the operator writes could drop the flag
or add `--enable-log-requests`. So the launcher turns logging and telemetry off, for every row.

**The `0013` cards** — `R1`, `R2`, `R3`, `R5`, `S4` and `S5` fixed in live text and code; `R6` and `R7` won't-fix
([D10](design.md#d10)).

## What Changes

- **The user file:** `--models <path>`, else `GPUNIT_MODELS`, else `$XDG_CONFIG_HOME/gpunit/models.toml`
  (`~/.config/gpunit/models.toml`); one file read, never merged with another ([D1](design.md#d1)).
- **Its rows join the bundled ones;** a row of a bundled name replaces it, said in one line ([D2](design.md#d2)).
- **A user row passes the bundled row's checks,** and the file names no `image` ([D3](design.md#d3)).
- **A row holding `--enable-log-requests` is refused** ([D4](design.md#d4)).
- **The unknown-model usage error names each row's source**, `bundled` or the file's path ([D5](design.md#d5)).
- **`serve/launch.py` sets `DO_NOT_TRACK`, `HF_HUB_DISABLE_TELEMETRY` and `VLLM_NO_USAGE_STATS`, and passes
  `--no-enable-log-requests` last;** the bundled rows lose the flag ([D6](design.md#d6)).
- **`--models <path>`** on `serve`, `down --serve` and `volume up|down --serve` ([D7](design.md#d7)).
- **README's *Your own rows*, `CLAUDE.md`'s layout, and the threat model's user file** ([D8](design.md#d8)).
- **The `0013` cards** ([D9](design.md#d9), [D10](design.md#d10)).
- **The serve image rebuilt and re-pinned** ([D11](design.md#d11)), then **`make live-serve` on a non-Qwen row from
  `live/models.toml`**, by hand and metered ([D12](design.md#d12)).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `serve`:
  - *The operator's own rows come from one user file* (added) — the lookup, the merge, the replace line, the checks,
    the sources.
  - *The model table names what each model serves on* — no row may hold `--enable-log-requests`; the bundled rows
    no longer carry `--no-enable-log-requests`.
  - *The serve image is built on request and pinned* — the launch script sets the telemetry variables and passes
    `--no-enable-log-requests` last, whatever the pod's environment holds.
  - *The chat streams the model's answer in the terminal* — streamed text prints without control characters but
    newline and tab (`0013·S4`).
- `cli`:
  - *The verbs and the usage exit* — `--models` on each verb that names a model; `--models` without a model exits
    `2`; the unknown-model error names each row's source.

## Impact

- **Code:** `gpunit/serve/table.py`, `gpunit/serve/session.py`, `gpunit/serve/chat.py`, `gpunit/serve/models.toml`,
  `gpunit/log.py`, `gpunit/cli.py`, `serve/launch.py`, and the tests.
- **Docs:** `README.md`, `CLAUDE.md`, `docs/threat-model.md`; `live/models.toml` (new); `live/serve_last_run.txt`
  after the proof.
- **Consumers:** none break. A script that parsed the unknown-model error's list reads `name (source)` now.
- **The serve image:** rebuilt as `gpunit-vllm:v0.10-rc1`, since `serve/launch.py` changed.
- **Dependencies:** none ([Dependencies](design.md#dependencies)).
- **Spend:** one `make live-serve` on a 24 GB card, about $0.20, by hand ([D12](design.md#d12)).

## Not in this change

- **A per-row `image`** (Q9) — trigger: the first model the pinned vLLM cannot serve; it bumps the bundled image.
- **A gated model:** a row-level `env` taking `{{ RUNPOD_SECRET_hf_token }}` (Q5) — trigger: the first gated model to
  serve.
- **A verb that lists rows** (Q6): the usage error lists them.
- **Several user files merged** (Q1): one file is read.
- **Checking a user row's other vLLM arguments,** as `--trust-remote-code` — trigger: a user file written by someone
  other than the operator.
- **`datacenters` for `serve`** — trigger: a served model whose prompts must stay in a region. `0013·S5` only says so.
- **A change to the bundled rows' models.**
- **`0013·R6` and `0013·R7`** — they name the archived `0013` design and tasks, and the released `[0.9.0]` entry.
