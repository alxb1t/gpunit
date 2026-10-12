# Tasks — 0008 a 30B-class model row

The row, the check, the handover, then the one metered proof, per [design](design.md). Every new test carries
`@pytest.mark.spec` with the key its task names.

## Progress

- [x] 1 — The row
- [x] 2 — The check
- [ ] 3 — The handover
- [ ] 4 — ⚠️ **HUMAN · METERED** — make live-serve MODEL=qwen3.8-27b

## 1 — The row

- [x] 1.1 **HALT CHECK** — the table holds the 4B row alone, and the larger model's revision is still on the Hub.
  Verify: `grep -c '^\[models' gpunit/serve/models.toml` prints `1`, and `curl -s -m 20 https://huggingface.co/api/models/Qwen/Qwen3.8-27B-FP8/revision/017b9c7af6b5689d5dd426a76e0bc077eb5ca20a | grep -c '"sha":"017b9c7af6b5689d5dd426a76e0bc077eb5ca20a"'` prints `1`.
- [x] 1.2 Add the row `[models."qwen3.8-27b"]` to `gpunit/serve/models.toml` per [D1](design.md#d1) and [D2](design.md#d2); in `tests/test_serve_table.py` widen `serve:table:loads` to both rows and bind `serve:table:larger-row`; in `tests/test_cli.py` assert the unknown-model refusal names both rows.
  Verify: `uv run python -c 'from gpunit.serve import table; print(sorted(table.load().models))'` prints `['qwen3-4b', 'qwen3.8-27b']`, and `grep -c 'serve:table:larger-row' tests/test_serve_table.py` prints `1`.

## 2 — The check

- [x] 2.1 Write `live/tool_call.py` per [D3](design.md#d3); in `tests/test_tool_call.py` bind the four `serve:tools:*` scenarios against a local `http.server` that answers each case.
  Verify: `grep -o 'serve:tools:[a-z-]*' tests/test_tool_call.py | sort -u | wc -l | tr -d ' '` prints `4`, and `grep -c 'sys.argv' live/tool_call.py` prints a number of at least `1`.
- [x] 2.2 Give the `Makefile` `MODEL ?= qwen3-4b`, use it in `live-serve`, and run `live/tool_call.py` beside the `curl`, per [D4](design.md#d4).
  Verify: `grep -c 'qwen3-4b' Makefile` prints `1`, and `make -n live-serve MODEL=qwen3.8-27b | grep -c 'tool_call.py'` prints a number of at least `1`.

## 3 — The handover

- [ ] 3.1 Name both rows and `make live-serve MODEL=<row>` in `README.md`'s *Serve a model* and its proof paragraph, per [D5](design.md#d5).
  Verify: `grep -c 'qwen3.8-27b' README.md` prints a number of at least `1`, and `grep -c 'MODEL=' README.md` prints a number of at least `1`.

## 4 — ⚠️ **HUMAN · METERED** — make live-serve MODEL=qwen3.8-27b

- [ ] 4.1 **HUMAN · METERED** — with `RUNPOD_API_KEY` set, run `make live-serve MODEL=qwen3.8-27b`; confirm through the RunPod console that no pod is left; append the card that ran, the chat's answer, the `curl`'s answer and the check's line to `live/serve_last_run.txt` under a header `<date> — make live-serve MODEL=qwen3.8-27b, 0008-a-30b-class-row`, per [D6](design.md#d6). A card that fails to load the model leaves the row's `gpus`, and the run is repeated; a cold load past 1200s, or a refused name, is a halt: say so and keep the log.
  Verify: `grep -c '^2026-.*0008-a-30b-class-row' live/serve_last_run.txt` prints `1`, and `grep -c 'tool call: get_weather' live/serve_last_run.txt` prints a number of at least `1`.
