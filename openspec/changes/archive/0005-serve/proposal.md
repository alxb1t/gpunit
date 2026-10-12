---
version: v0.3
---

# 0005 — serve

**`gpunit serve <model> --ceiling 2h` is a chat in the terminal; `--api` is an OpenAI-compatible endpoint on
loopback for any local client.** A bundled model table, a `gpunit-vllm` image pinned by digest, and a session over
`gpunit.session()`. **A minor: it delivers one feature, serving a model.**

| read | for |
|---|---|
| this file | why, and what changes |
| [design](design.md) | the table, the session, the chat, the endpoint, the image, the proof |
| [tasks](tasks.md) | the phases, in build order |
| `specs/` | `serve` (new) · `cli` |

## Why

**An open model on a rented GPU takes a dozen manual steps**: pick a card, boot vLLM, tunnel, guess when it has
loaded, and remember to tear down. gpunit already owns every step but the model. One command and a table row make
the rest a matter of choosing the model.

**An agent needs the same endpoint a person chats with**: an OpenAI-compatible URL and a key, for as long as a
session with a ceiling lasts.

## What Changes

- **The model table** `gpunit/serve/models.toml`: one row, `qwen3-4b`, and the image's digest
  ([D1](design.md#d1)).
- **`gpunit serve <model> --ceiling …`**: the price and a `y/N` before any rent; the session's files per model; the
  wait for the model, bounded ([D2](design.md#d2)–[D4](design.md#d4)).
- **The chat**: streamed answers, the conversation in memory, thinking off unless `--think`
  ([D5](design.md#d5)).
- **`--api`**: the base URL and a per-session key, held until an interrupt or the ceiling ([D6](design.md#d6)).
- **`gpunit down --serve <model>`** ([D2](design.md#d2)).
- **`serve/Dockerfile`** and **`build-serve-image.yml`**: vLLM by digest, gpunit's boot script, on request only
  ([D7](design.md#d7)).
- **README and `CLAUDE.md`**; **`make live-serve`** ([D8](design.md#d8), [D9](design.md#d9)).

## Capabilities

### New Capabilities

- `serve`: the model table, the price prompt, the served session and its wait, the chat, the endpoint, the image.

### Modified Capabilities

- `cli`:
  - *The verbs and the usage exit* — `serve <model>` and `down --serve <model>`; a missing ceiling and an unknown
    model exit `2`.

## Impact

- **Files:** `gpunit/serve/` (new: `__init__.py`, `models.toml`, `table.py`, `session.py`, `chat.py`), `gpunit/cli.py`,
  `serve/Dockerfile` (new), `.github/workflows/build-serve-image.yml` (new), `Makefile`, `README.md`, `CLAUDE.md`,
  `live/serve_last_run.txt` (new), and the tests.
- **Behaviour:** the existing verbs are unchanged.
- **Dependencies:** none ([Dependencies](design.md#dependencies)).
- **Spend:** `make live-serve` rents one 24 GB card for about 20 minutes, by hand ([D9](design.md#d9)).

## Not in this change

- **Hermes reaching `--api` from its box** — trigger: agent-iac's check of the container's reach to the host's
  loopback and of Hermes' SSRF block.
- **A bind address other than loopback** — trigger: that check failing.
- **The 30B-class model** — trigger: *serve* proven; it is a row.
- **Serverless, the tailnet, volume lifecycle, a second provider.**
