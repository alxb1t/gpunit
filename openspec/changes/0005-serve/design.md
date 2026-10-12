# Design — 0005 serve

How a model is served over a gpunit session: a table row becomes a `Spec`, a prompt guards the price, the session
waits for vLLM, and a chat or an endpoint holds it open. **Verdict: feasible** — the session is `gpunit.session()`;
the new code is a table, an HTTP client on `urllib`, and an image.

## Context

See [proposal](proposal.md) — *Why*. What holds at the cut, `main` at `d0b63ab` (`v0.2.0`):

- **The library:** `gpunit.session(spec, environ=, cwd=, say=)` (`gpunit/library.py:61`) over `_open`
  (`:80`); `Session.port(remote)` (`:53`); `State(cwd)` keeps `<cwd>/.gpunit/`.
- **The CLI:** the verbs `up · status · down · ssh · run`, each with `--spec` (`gpunit/cli.py:31-39`); `parse`
  refuses an unreadable spec path with exit `2` (`:58-59`).
- **The provider:** `RunPod.gpu(name)` returns `GpuInfo(vram_gb, hourly)` (`gpunit/provider.py:36-40`);
  `RunPod.log(pod_id, tail=, since=)`; `live/price.py` prints each card's price and the maximum.
- **`[env]`** refuses a `GPUNIT_*` name (`gpunit/spec.py`, `_env`); the create's environment adds `PUBLIC_KEY`,
  `GPUNIT_CEILING` and, with a volume, `GPUNIT_VOLUME_ID` and `GPUNIT_VOLUME_PATH`.
- **The live image** `live/Dockerfile`: Ubuntu by digest, `openssh-server`, `curl`, the host keys deleted, `boot.sh`
  copied, `ENTRYPOINT ["/opt/gpunit/boot.sh", "--"]`.
- **Pinned at the cut:** `Qwen/Qwen3-4B` at `1cfa9a7208912126459214e8b04321603b3df60c` (its chat template carries
  `enable_thinking`); `vllm/vllm-openai:v0.31.0` at
  `sha256:c1c9f6fd5c109ba7f0546a59f5b2f15fb87f64c77782e90a27b648b42a8e67c3`; vLLM `v0.31.0`'s docs give Qwen3 the
  `qwen3` reasoning parser and Qwen models the `hermes` tool parser.

## Goals / Non-Goals

**Goals:** one command from a model name to a chat or an endpoint, its spend shown and agreed first; stdlib only.

**Non-Goals:** Hermes on its box; a bind address; serverless; the tailnet; a volume's lifecycle.

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| [D1](#d1) | `gpunit/serve/models.toml` and `table.py`: rows, the image digest, `Row.spec(ceiling, volume, max_hourly, key)` | a model is a row; the spec is built, never written | a `gpunit.toml` per model |
| [D2](#d2) | the state under `~/.local/state/gpunit/serve/<model>/`; `gpunit down --serve <model>` | one session per model, from any directory | the working directory |
| [D3](#d3) | the price from `RunPod.gpu` per card, the max over placeable cards × ceiling, `input` for `y/N` | a person runs serve by hand at cost | no prompt |
| [D4](#d4) | the wait polls `GET /v1/models` with the key every 5 s for 1200 s; a log line every 30 s | pull, download, load | no wait |
| [D5](#d5) | `chat.py`: `readline` when importable, SSE over `urllib`, history in memory, `enable_thinking` false unless `--think` | stdlib only | a client library |
| [D6](#d6) | `--api`: a `secrets.token_urlsafe(32)` key in the pod's environment; the URL and key printed; hold until `Interrupted` | the key keeps the loopback port the session's | no key |
| [D7](#d7) | `serve/Dockerfile` from vLLM by digest; its `CMD` runs `vllm serve` from the pod's environment; `build-serve-image.yml` on dispatch | the image any row serves on | one image per model |
| [D8](#d8) | README *Serve a model*; `CLAUDE.md`'s layout names `gpunit/serve/` | the README is the promise | — |
| [D9](#d9) | the last phase HUMAN · METERED: build and pin the image; `make live-serve` — one prompt, one `curl`, teardown | only a pod proves the image and the model | — |

### D1

```toml
image = "ghcr.io/alxb1t/gpunit-vllm@sha256:<digest>"   # 0 × 64 until the metered phase pins it

[models.qwen3-4b]
repo = "Qwen/Qwen3-4B"
revision = "1cfa9a7208912126459214e8b04321603b3df60c"
served = "qwen3-4b"
args = ["--max-model-len", "16384", "--enable-auto-tool-choice", "--tool-call-parser", "hermes",
        "--reasoning-parser", "qwen3"]
vram_gb = 24
gpus = ["NVIDIA RTX A5000", "NVIDIA RTX A4500", "NVIDIA GeForce RTX 4090"]
disk_gb = 40
```

`table.load()` reads it with `tomllib` and refuses a missing field, a revision that is not 40 hex, or an image that
is not a digest. `Row.spec(...)` returns a `Spec`: project `serve-<name>`, the image, the row's cards, memory and disk,
`ports = (8000,)`, the ceiling, an SSH wait of 1200 s, the volume and `max_hourly` if given, and `env` holding
`SERVE_REPO`, `SERVE_REVISION`, `SERVE_NAME`, `SERVE_ARGS` (the args joined) and `VLLM_API_KEY`. The `SERVE_*` names
stay clear of the `GPUNIT_` names `[env]` reserves.

### D2

`gpunit/serve/session.py`'s `serve(name, ceiling, api, volume, max_hourly, yes, think, provider, …)` makes
`~/.local/state/gpunit/serve/<name>/` and opens `library._open` there. `gpunit down --serve <name>` builds the row's
spec and runs `lifecycle.down` with that state. `gpunit serve` is a verb in `cli.py`: `<model>` positional,
`--ceiling` required, `--api`, `--volume`, `--max-hourly`, `--yes`, `--think`; no `--spec`. An unknown model exits `2`
naming the table's models.

### D3

For each of the row's cards, `RunPod.gpu(card)` gives the price; cards over `--max-hourly` are dropped; the maximum
is the highest remaining price × the ceiling in hours. The prompt reads one line through an injectable `ask`;
anything but `y` or `yes` refuses with `refused: not rented`, exit `1`.

### D4

`GET http://127.0.0.1:<s.port(8000)>/v1/models` with `Authorization: Bearer <key>`, a 5 s timeout, no proxy. Every
30 s the last line of `RunPod.log(s.pod_id, tail=50)` is printed as `loading: <line>`. At 1200 s the command refuses
`the model did not load within 1200s` and leaves the block.

### D5

`chat.run(base_url, key, model, think, read, write)`: `read` defaults to `input` (with `readline` imported when
present), `write` to stdout. Each turn posts `{"model", "messages", "stream": true, "chat_template_kwargs":
{"enable_thinking": think}}` and prints each `data:` chunk's `choices[0].delta.content` until `data: [DONE]`. `/exit`
and `EOFError` end it.

### D6

`--api` prints both lines to stdout, then polls `/v1/models` every 30 s until `Interrupted` — an operator's
Ctrl-C — or until the server has not answered for 60 s, as when the pod's ceiling has stopped it; either way the block
ends and the session tears down.

### D7

```
FROM vllm/vllm-openai:v0.31.0@sha256:c1c9f6fd5c109ba7f0546a59f5b2f15fb87f64c77782e90a27b648b42a8e67c3
RUN apt-get update && apt-get install -y --no-install-recommends openssh-server curl \
 && rm -rf /var/lib/apt/lists/* /etc/ssh/ssh_host_*
ENV DO_NOT_TRACK=1 HF_HUB_DISABLE_TELEMETRY=1 VLLM_NO_USAGE_STATS=1
COPY boot/boot.sh /opt/gpunit/boot.sh
ENTRYPOINT ["/opt/gpunit/boot.sh", "--"]
CMD ["sh", "-c", "${GPUNIT_VOLUME_PATH:+export HF_HOME=\"$GPUNIT_VOLUME_PATH/huggingface\";} exec vllm serve \"$SERVE_REPO\" --revision \"$SERVE_REVISION\" --served-model-name \"$SERVE_NAME\" --host 127.0.0.1 --port 8000 $SERVE_ARGS"]
```

`build-serve-image.yml`: `workflow_dispatch` with a required `tag`, `latest` refused, `ghcr.io/alxb1t/gpunit-vllm`,
the digest written to the summary; actions pinned by commit. `boot.sh` is copied from the tree, as `live/Dockerfile`
does, so the image carries the boot of the commit it was built from.

### D8

README *Serve a model*: the command, the price prompt, the chat, `--api` with the two lines and a `curl`, `gpunit down
--serve`, and *From a container* — the two checks a containerized client needs, named and not made.

### D9

`make live-serve`: `uv run gpunit serve qwen3-4b --ceiling 30m --yes --api` in the background long enough for one
`curl` of `/v1/chat/completions`, then a chat of one prompt piped in. The operator builds the image first, pins its
digest in `models.toml`, runs the target, confirms no pod is left, and writes the tail to `live/serve_last_run.txt`.

## Dependencies

None.

## Risks / Trade-offs

- **vLLM's image is large** → a cold host pulls it before it maps port 22, so the row's spec sets the SSH wait to
  the same 20 minutes as the model's.
- **The weights download at every boot** → `--volume` caches them for those who keep a volume.
- **The key rides the create's environment** → RunPod, the GPU's operator, can read it; it lives one session.
- **`SERVE_ARGS` is word-split by `sh`** → the table's args hold no spaces inside an argument; `table.load` refuses
  one.

## Verdict

Feasible: a row and a flag set over a session gpunit already holds, an HTTP client on the stdlib, and one image.
