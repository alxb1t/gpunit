# Design — 0008 a 30B-class model row

A row is data: the repository, its revision, vLLM's flags, the card memory and the cards. The version adds one row, one
check that proves it answers a tool request, and the live run that decides whether the flags and the cards were right.
**Verdict: feasible** — nothing in the code changes; the unknowns are all read on one real pod.

## Context

See [proposal](proposal.md) — *Why*. What holds at the cut, `main` at `98f7b47` (`v0.4.0`):

- **The table** `gpunit/serve/models.toml` holds the image by digest and one row, `qwen3-4b`, on `NVIDIA RTX A5000`,
  `NVIDIA GeForce RTX 4090`, `NVIDIA L4`, `vram_gb = 24`, `disk_gb = 40`, the `hermes` parser, the `qwen3` reasoning
  parser. `table.load` reads a row's `repo`, `revision` (40 hex), `served`, `args`, `vram_gb`, `gpus`, `disk_gb`, and
  refuses an `args` entry holding a space (`gpunit/serve/table.py:19-27`, `:101-123`); `WAIT_S` is 1200
  (`gpunit/serve/table.py:15`).
- **`Row.spec`** takes `(ceiling_s, volume, max_hourly, key, local_port)` and builds `project = serve-<name>`, the row's
  memory, cards and disk, `ports` forwarding remote 8000, `timeout_s = WAIT_S`, and the model in `env`
  (`gpunit/serve/table.py:44-72`). `cli._known` lists `sorted(table.load().models)` (`gpunit/cli.py:180-182`).
- **`make live-serve`** hardcodes `qwen3-4b` in the endpoint's `serve` command, the request body and the chat's
  command (`Makefile:29`, `:34`, `:37`).
- **The model**, read from Hugging Face on 2026-10-12: `Qwen/Qwen3.8-27B-FP8`, revision
  `017b9c7af6b5689d5dd426a76e0bc077eb5ca20a` (2026-08-14), 30.9 GB, `Qwen3_5ForConditionalGeneration`, Apache-2.0,
  FP8 with 128×128 blocks. Its card's family sibling, `Qwen3.6-35B-A3B-FP8`, documents `--reasoning-parser qwen3
  --enable-auto-tool-choice --tool-call-parser qwen3_coder`.
- **The pinned vLLM** is `v0.31.0`, still the latest release: `qwen3_coder` and `qwen3_xml` both map to
  `Qwen3EngineToolParser` (`vllm/tool_parsers/__init__.py`), and `--language-model-only` is a flag of its `vllm serve`
  (`vllm/engine/arg_utils.py`).
- **The cards**, secure cloud, all availability LOW: `NVIDIA A40` and `NVIDIA RTX A6000` $0.59/h, `NVIDIA L40` $0.82,
  `NVIDIA RTX 6000 Ada Generation` $0.99, `NVIDIA L40S` $1.09 — each 48 GB. Ada runs FP8 natively; Ampere would run it
  weight-only, which is unproven.
- **A TOML table name with a dot nests**, so the row is written `[models."qwen3.8-27b"]`.

## Goals / Non-Goals

**Goals:** the row, proved to load and to call a tool on a real card.

**Non-Goals:** a second row; a code change in `serve`; a new image; a per-row wait.

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| [D1](#d1) | the row `qwen3.8-27b` for `Qwen/Qwen3.8-27B-FP8` at the pinned revision | the newest dense line, lighter than the MoE, room for context on 48 GB | the MoE; the founding Qwen3-30B-A3B |
| [D2](#d2) | the flags and the cards, cheapest first, `disk_gb = 80` | the card's parsers; no vision tower; 31 GB of weights plus a large image | `hermes`; the vision encoder |
| [D3](#d3) | `live/tool_call.py`, stdlib, key from `OPENAI_API_KEY` | a tool call is the fact the row is for | trusting the flag |
| [D4](#d4) | `make live-serve` takes `MODEL` (default `qwen3-4b`) and runs the check | one proof for every row | a target per row |
| [D5](#d5) | README names both rows and `MODEL` | the README is the promise | — |
| [D6](#d6) | the last phase HUMAN · METERED: one `make live-serve MODEL=qwen3.8-27b` | only a real card shows FP8, the flags and the cold load | trusting the card |

### D1

```toml
[models."qwen3.8-27b"]
repo = "Qwen/Qwen3.8-27B-FP8"
revision = "017b9c7af6b5689d5dd426a76e0bc077eb5ca20a"
served = "qwen3.8-27b"
```

The pod's name becomes `gpunit-serve-qwen3.8-27b`; the live run is also the first to put a dot in a pod's name.

### D2

```toml
args = ["--max-model-len", "32768", "--reasoning-parser", "qwen3", "--enable-auto-tool-choice",
        "--tool-call-parser", "qwen3_coder", "--language-model-only", "--max-num-seqs", "64"]
vram_gb = 48
gpus = ["NVIDIA A40", "NVIDIA RTX A6000", "NVIDIA L40", "NVIDIA RTX 6000 Ada Generation", "NVIDIA L40S"]
disk_gb = 80
```

`--max-num-seqs 64` was added after the first live runs, 2026-10-13: vLLM refused to start with its default 256,
`max_num_seqs (256) exceeds available Mamba cache blocks (192)`, on a 48 GB card at 32k context. 64 leaves room
under 192 for an agent's few concurrent requests.

No argument holds a space. The price prompt counts the dearest placeable card, `NVIDIA L40S` at $1.09/h: for
`--ceiling 30m` and the 1200 s SSH wait, at most $0.91.

### D3

`live/tool_call.py <base-url> <model>` posts to `<base-url>/chat/completions`, with `OPENAI_API_KEY` as the bearer
token, a request holding one user message and one function:

```
{"model": <model>, "messages": [{"role": "user", "content": "What is the weather in Paris? Use the tool."}],
 "tools": [{"type": "function", "function": {"name": "get_weather", "description": "Get the weather in a city",
   "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}}],
 "tool_choice": "auto", "chat_template_kwargs": {"enable_thinking": false}}
```

It passes when `choices[0].finish_reason` is `tool_calls`, the first call's `function.name` is `get_weather`, and its
`arguments` parse as JSON; it prints `tool call: get_weather <arguments>` and exits `0`. Anything else exits `1`
naming what it found. The key is never an argument.

### D4

`Makefile` gains `MODEL ?= qwen3-4b`; `live-serve` uses `$(MODEL)` in the `serve` commands and the request body, and
after the `curl` runs `OPENAI_API_KEY="$$key" uv run python live/tool_call.py "$$base" $(MODEL)`, killing the endpoint
and failing if it exits non-zero.

### D5

README's *Serve a model* says the table holds `qwen3-4b` and `qwen3.8-27b`, one line on each (the 4B on a 24 GB card
for cents; the 27B on a 48 GB card, `qwen3_coder`, with the dearest card's price), and that `make live-serve
MODEL=<row>` proves a row.

### D6

A **HUMAN · METERED** phase: `RUNPOD_API_KEY` set, `make live-serve MODEL=qwen3.8-27b`; the log of what card ran, the
chat's answer, the `curl`'s answer and the check's line appended to `live/serve_last_run.txt` under a header
`<date> — make live-serve MODEL=qwen3.8-27b, 0008-a-30b-class-row`; the console shows no pod left. If a card refuses to
load the model, it is cut from the row's `gpus` and the run repeated. If the cold load passes 1200 s, or the name is
refused, the task halts and says so.

## Dependencies

None.

## Risks / Trade-offs

- **FP8 on Ampere is weight-only** → the cheapest cards may fail to load it; the live run says which, and the row loses
  them.
- **A cold load of 31 GB plus vLLM's image may pass 1200 s** → the proof halts; a per-row wait is the next version.
- **A dot in a pod's name may be refused** → the proof halts and the row is renamed.
- **Availability is LOW on every 48 GB card** → the run may find none; the price prompt shows each card, and the run is
  repeated, not changed.

## Verdict

Feasible: one row of data, one stdlib check, and one real run to read what the flags and the cards cannot say.
