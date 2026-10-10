# Tasks — 0005 serve

The table, the served session, the chat and the endpoint, the image and the documents, then the one metered proof,
per [design](design.md). Every new test carries `@pytest.mark.spec` with the key its task names.

## Progress

- [ ] 1 — The table
- [ ] 2 — The served session
- [ ] 3 — The chat and the endpoint
- [ ] 4 — The image and the documents
- [ ] 5 — ⚠️ **HUMAN · METERED** — build, pin, make live-serve

## 1 — The table

- [ ] 1.1 **HALT CHECK** — no serve code exists, and the pinned revision is still on the Hub.
  Verify: `ls gpunit/serve 2>&1 | grep -c 'No such file'` prints `1`, and `curl -s -m 20 https://huggingface.co/api/models/Qwen/Qwen3-4B/revision/1cfa9a7208912126459214e8b04321603b3df60c | grep -c '"sha":"1cfa9a7208912126459214e8b04321603b3df60c"'` prints `1`.
- [ ] 1.2 Write `gpunit/serve/__init__.py`, `gpunit/serve/models.toml` and `gpunit/serve/table.py` per [D1](design.md#d1); in `tests/test_serve_table.py` bind `serve:table:loads`, `serve:table:revision-pinned` and `serve:table:row-makes-the-spec`.
  Verify: `uv run python -c 'from gpunit.serve import table; print(sorted(table.load().models))'` prints `['qwen3-4b']`, and `grep -o 'serve:table:[a-z-]*' tests/test_serve_table.py | sort -u | wc -l | tr -d ' '` prints `3`.

## 2 — The served session

- [ ] 2.1 Write `gpunit/serve/session.py` per [D2](design.md#d2), [D3](design.md#d3) and [D4](design.md#d4); in `tests/test_serve_session.py` bind `serve:price:no-by-default`, `serve:price:yes-skips`, `serve:wait:awaited`, `serve:wait:bound-tears-down` and `serve:wait:state-per-model` on a `FakeProvider` and a fake model server.
  Verify: `grep -o -E 'serve:(price|wait):[a-z-]+' tests/test_serve_session.py | sort -u | wc -l | tr -d ' '` prints `5`.
- [ ] 2.2 Add `serve <model>` and `down --serve <model>` to `gpunit/cli.py` per [D2](design.md#d2); in `tests/test_cli.py` bind `cli:verbs:serve-without-ceiling-exits-2` and `cli:verbs:serve-unknown-model-exits-2`.
  Verify: `uv run gpunit serve qwen3-4b; echo $?` prints a last line `2`, and `grep -c -E 'cli:verbs:serve-' tests/test_cli.py` prints `2`.

## 3 — The chat and the endpoint

- [ ] 3.1 Write `gpunit/serve/chat.py` per [D5](design.md#d5) and wire it into `serve`; in `tests/test_serve_chat.py` bind `serve:chat:streams`, `serve:chat:thinking-off` and `serve:chat:eof-ends` against a local `http.server` that streams SSE.
  Verify: `grep -o 'serve:chat:[a-z-]*' tests/test_serve_chat.py | sort -u | wc -l | tr -d ' '` prints `3`.
- [ ] 3.2 Add `--api`'s key, its printout and its hold per [D6](design.md#d6); in `tests/test_serve_session.py` bind `serve:api:prints-the-endpoint` and `serve:api:key-required`.
  Verify: `grep -o 'serve:api:[a-z-]*' tests/test_serve_session.py | sort -u | wc -l | tr -d ' '` prints `2`.

## 4 — The image and the documents

- [ ] 4.1 Write `serve/Dockerfile` and `.github/workflows/build-serve-image.yml` per [D7](design.md#d7); in `tests/test_serve_image.py` bind `serve:image:pinned-inputs` and `serve:image:only-a-request-builds`.
  Verify: `grep -c '^FROM vllm/vllm-openai:v0.31.0@sha256:c1c9f6fd5c109ba7f0546a59f5b2f15fb87f64c77782e90a27b648b42a8e67c3$' serve/Dockerfile` prints `1`, and `grep -c 'workflow_dispatch' .github/workflows/build-serve-image.yml` prints `1`.
- [ ] 4.2 Add README's *Serve a model* with *From a container*, `gpunit/serve/` to `CLAUDE.md`'s layout, and the `live-serve` target to the `Makefile`, per [D8](design.md#d8) and [D9](design.md#d9).
  Verify: `grep -c 'Serve a model' README.md` prints `1`, `grep -c 'From a container' README.md` prints `1`, and `make -n live-serve | grep -c 'gpunit serve qwen3-4b'` prints a number of at least `1`.

## 5 — ⚠️ **HUMAN · METERED** — build, pin, make live-serve

- [ ] 5.1 **HUMAN · METERED** — push `v0.3_serve`; dispatch `build-serve-image.yml` on it with tag `v0.3-rc1`; write its digest into `gpunit/serve/models.toml`'s `image`; run `make live-serve` with `RUNPOD_API_KEY` set; confirm with the RunPod console that no pod is left; append the run's tail to `live/serve_last_run.txt` under a header `<date> — make live-serve, 0005-serve`; per [D9](design.md#d9).
  Verify: `grep -c 'gpunit-vllm@sha256:0000' gpunit/serve/models.toml` prints `0`, and `grep -c '^2026-.*0005-serve' live/serve_last_run.txt` prints a number of at least `1`.
