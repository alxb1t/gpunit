# gpunit

**A RunPod GPU session any project can open, use and close.** One TOML file, one Dockerfile line, one command:
the pod is placed, its host key proven, the command run against it, and the pod torn down on every way out.

```
laptop                                           pod
gpunit run -- <cmd>                              boot.sh -- <cmd>
 ├─ up: place · wait · verify host key ────────▶  ceiling armed · sshd · fingerprint
 ├─ ssh -N -L <ports>  ◀─────────────────────────▶ sshd
 ├─ <cmd> with GPUNIT_HOST, GPUNIT_PORT_*, GPUNIT_SSH
 └─ down: delete · sweep                          stops itself at the ceiling
```

The design: [openspec/changes/archive/0001-core/design.md](openspec/changes/archive/0001-core/design.md).

## Use it from a project

1. **Write `gpunit.toml`** at the project root.

   ```toml
   project = "isekai"                          # the pod is named gpunit-isekai
   image = "ghcr.io/you/isekai@sha256:<64 hex>" # a digest, never a tag
   gpus = ["NVIDIA GeForce RTX 4090", "NVIDIA RTX A6000"]  # tried in order
   vram_gb = 24
   ceiling = "45m"                             # required: the pod stops itself after this
   disk_gb = 50
   # optional
   volume_gb = 60                              # a window volume, made by gpunit volume up
   volume_ceiling = "4h"                       # required with volume_gb: the volume is deleted after it
   volume_datacenter = "EU-RO-1"               # else where the first card of gpus is in stock
   # volume = "<network volume id>"            # or a kept volume, never with volume_gb
   # either pins the data centre; the pod sees GPUNIT_VOLUME_PATH
   ports = [8188, { remote = 8080, local = 18080 }]
   ram_gb = 32
   cuda = "12.8"
   max_hourly = 0.80
   timeout = 420                               # seconds to wait for SSH
   [env]
   MODE = "render"                             # GPUNIT_* names are gpunit's, and refused here
   ```

2. **Make `boot.sh` the image's entrypoint.** It needs `openssh-server`, `curl` and coreutils' `env` in the
   image, and BuildKit for the checksum; on an older Docker, copy the file in.

   ```dockerfile
   ADD --checksum=sha256:<digest> https://raw.githubusercontent.com/alxb1t/gpunit/v0.6.0/boot/boot.sh /opt/gpunit/boot.sh
   RUN chmod +x /opt/gpunit/boot.sh
   ENTRYPOINT ["/opt/gpunit/boot.sh", "--"]
   CMD ["python3", "main.py", "--listen", "0.0.0.0", "--port", "8188"]
   ```

   `<digest>` is the file's sha256 at the tag: `curl -sL <the URL above> | shasum -a 256`. An older `boot.sh` is
   refused: its host-key line carries no session nonce, so `up` tears the pod down and names `v0.6.0`.

3. **Install and run.** The key comes from the environment alone; gpunit reads no `.env`. The command's
   environment on the pod does not carry `RUNPOD_API_KEY`: boot keeps it to stop the pod. The command runs as
   root beside boot, though, so it can still read the key from boot's own environment in `/proc`; run nothing
   on the pod you would not trust with the key.

   ```sh
   uv add --dev git+https://github.com/alxb1t/gpunit@v0.6.0
   echo .gpunit/ >> .gitignore
   export RUNPOD_API_KEY=...
   uv run gpunit run -- python3 render.py
   ```

   The command sees `GPUNIT_HOST`, `GPUNIT_PORT_<remote>=<local>` for each port, and `GPUNIT_SSH`, a command
   line that opens a shell on the pod. gpunit does not wait for the app: the command polls its own port.

## Use it from Python

`gpunit.session()` is the session `gpunit run` opens, as a `with` block: the pod is torn down when the block
ends, however it ends.

```python
import subprocess

import gpunit

with gpunit.session("gpunit.toml", environ={"RUNPOD_API_KEY": key}, say=my_log) as s:
    url = f"http://127.0.0.1:{s.port(8188)}"
    subprocess.run([*s.ssh, "nvidia-smi"], check=True)
```

| attribute | is |
|---|---|
| `s.host` | the pod's public SSH host |
| `s.port(remote)` | the local port `remote` is forwarded to; `Refused` for a port not in `ports` |
| `s.ssh` | the `ssh` argv that opens a shell on the pod |
| `s.image` | the booted image |
| `s.pod_id` | the pod's id |

| raises | when | `gpunit run` exits |
|---|---|---|
| `gpunit.Refused` | it refused; nothing it rented is left | `1` |
| `gpunit.Lost` | a create's answer was lost; the sweep was attempted | `3` |
| `gpunit.TeardownFailed` | the teardown failed; `.gpunit/pod` is kept, so run `gpunit down`. Its `__cause__` is the exception that ended the block, if one did, or the `Refused` whose own teardown failed while the session opened | `1` |
| `gpunit.Interrupted` | `SIGINT`, `SIGTERM` or `SIGHUP` ended the block; a `KeyboardInterrupt` whose `.signal` names it | `128+n` |

- **The spec** is a path, or a `Spec` from `gpunit.load_spec`. `cwd` is where `.gpunit/` lives; it defaults to
  the working directory.
- **The key** is read from `environ` when given, else from the process's environment.
- **The lines** go to `say(line)` when given, else to stderr. The tunnel's thread calls `say` too, so it must be
  safe to call from another thread.
- **Signals:** while the block runs, `SIGINT`, `SIGTERM` and `SIGHUP` raise `Interrupted`; during the teardown
  they are ignored. Your own handlers are replaced for the block's life and set back when it closes.
- **The main thread:** open the session there; another thread gets `Refused`.
- **The tunnel** is reopened when it dies, as in `gpunit run`.

## Serve a model

`gpunit serve <model> --ceiling 2h` boots vLLM on a rented card and opens a chat in the terminal; `--api` gives an
OpenAI-compatible endpoint on loopback instead. The models it knows are rows of
[gpunit/serve/models.toml](gpunit/serve/models.toml), each at a pinned revision, all on one image pinned by digest:

- **`qwen3-4b`** — Qwen3-4B on a 24 GB card, for cents an hour: the row that proves `serve`.
- **`qwen3.8-27b`** — Qwen3.8-27B at FP8 on a 48 GB card, tool calls through the `qwen3_coder` parser; its dearest
  card, `NVIDIA L40S`, was $1.09/h at the cut.

```
laptop                                         pod (gpunit-vllm)
gpunit serve qwen3-4b --ceiling 2h             boot.sh -- vllm serve, key required
 ├─ the price · [y/N]: nothing rented without y
 ├─ up · ssh -L <port> ◀─────────────────────▶ vLLM on 127.0.0.1:8000
 ├─ wait for /v1/models, at most 1200s
 ├─ the chat, or --api's two lines and a hold
 └─ down: /exit, end of input, Ctrl-C; the chat ends if the server stops answering
```

```console
$ export RUNPOD_API_KEY=...
$ uv run gpunit serve qwen3-4b --ceiling 2h
<UTC> price: NVIDIA RTX A5000 $<hourly>/h
<UTC> at most $<max> for 7200s and a 1200s wait for SSH
rent serve-qwen3-4b for at most $<max>? [y/N] y
...
> What is a warp?
A warp is ...
> /exit
```

- **The price comes first.** Each card's hourly price and the most the session can cost — the highest price times
  the ceiling plus the 1200s wait for SSH, since the pod bills while it pulls and the ceiling starts after — are
  printed, and nothing is rented without `y`. `--yes` skips the question; `--max-hourly` drops the dearer cards.
- **The wait is minutes.** The first boot pulls vLLM's image and downloads the weights; the pull and the load each
  have 1200s, a `loading:` line from the pod's log comes every 30s, and past 1200s the session is torn down.
  `--volume <id>` keeps the weights on a network volume across sessions; a [working window](#working-window)
  keeps them for the window alone.
- **A pod that stops ends the session.** Two status reads in a row of a stopped pod, in the wait or the `--api`
  hold, refuse with `the pod stopped while the model loaded` or `… while serving`, and tear it down. The pod's log
  is kept every 30s at `~/.local/state/gpunit/serve/<model>/pod.log`; the refusal prints its last 30 lines.
  `boot.sh` waits 60s after vLLM exits before it stops the pod, so the crash reaches `pod.log`.
- **The chat** streams each answer and keeps the conversation in memory. Thinking is off unless `--think`.
  `/exit` or the end of input ends the session; so does a server that stops answering, as when the ceiling has
  stopped the pod.
- **The local port** `<port>` is a free one, picked before the price is asked.
- **`--api`** prints two lines to stdout, then holds the session until Ctrl-C, or until the server has not
  answered for 60s, as when the ceiling has stopped the pod or vLLM has crashed; that refusal prints `pod.log`'s
  last 30 lines too:

  ```sh
  OPENAI_BASE_URL=http://127.0.0.1:<port>/v1
  OPENAI_API_KEY=<a fresh key per session>
  ```

  ```sh
  curl -s "$OPENAI_BASE_URL/chat/completions" -H "Authorization: Bearer $OPENAI_API_KEY" \
    -H 'Content-Type: application/json' \
    -d '{"model": "qwen3-4b", "messages": [{"role": "user", "content": "Hi"}]}'
  ```

  The key rides the pod's environment, so RunPod can read it; it lives one session.
- **The session's files** are under `~/.local/state/gpunit/serve/<model>/`, wherever the command runs: one session
  per model. After a failed teardown, `gpunit down --serve <model>` deletes what is left.

### From a container

A client in a container, such as an agent's box, needs two checks before it can use `--api`. gpunit makes neither.

1. **Its reach to the host's loopback.** The endpoint listens on the host's `127.0.0.1`; inside a container,
   `127.0.0.1` is the container itself.
2. **Its SSRF block.** A client that refuses loopback and private addresses refuses `OPENAI_BASE_URL` too.

## Working window

**A network volume that lives for a working window.** `gpunit volume up` creates it from `gpunit.toml`, every
session in the window mounts it, and `gpunit volume down`, or the volume's own ceiling, deletes it. The weights
download once a window, and no storage bills between windows.

```
gpunit volume up ──▶ run · up · serve, each pod mounts it ──▶ gpunit volume down
 data centre · price · [y/N]    GPUNIT_VOLUME_PATH              or the next command past its ceiling
```

From a project whose `gpunit.toml` sets `volume_gb` and `volume_ceiling`:

```sh
uv run gpunit volume up                    # .gpunit/volume records it
uv run gpunit run -- python3 render.py     # downloads the weights into $GPUNIT_VOLUME_PATH
uv run gpunit run -- python3 render.py     # a new pod reads them
uv run gpunit volume down
```

For `serve`, the volume is the row's `disk_gb`, and `serve` mounts it:

```sh
uv run gpunit volume up --serve qwen3-4b --ceiling 4h
uv run gpunit serve qwen3-4b --ceiling 1h
uv run gpunit volume down --serve qwen3-4b
```

- **The data centre comes from stock:** `volume_datacenter`, else the first card of `gpus` in stock in a data centre
  offering standard volumes, the highest stock winning. Every pod of the window goes there; when stock moves, run
  `volume down` and `volume up` to choose afresh.
- **The price comes first:** $0.07 per GB a month, over the whole hours of `volume_ceiling`, and nothing is created
  without `y`. `--yes` skips the question.
- **No session outlives its volume.** `up`, `run` and `serve` refuse when no volume is recorded, or when the session's
  ceiling plus its wait for SSH would end after the volume.
- **`volume up` again extends** a live volume to now plus `volume_ceiling`, after the price.
- **The ceiling:** `up`, `run`, `serve`, `down`, `status`, `volume up` and `volume down` each delete a volume past its
  end before anything else, `down` after its pods, which may hold it. `status` names the volume and its end.
- **The residual:** a volume no command reaches after its ceiling bills $0.07/GB a month until one does; `spend` names
  it once its billing shows it.
- **A lost create exits `3`.** `.gpunit/volume.pending` stays, and `volume down` lists the `gpunit-<project>`
  volumes, skips any this machine's ledger records, and names each other one, deleting it only on your `y`; no answer
  keeps it and the mark. Only that mark, with no volume recorded, sweeps by name: otherwise `volume down` deletes the
  recorded volume alone, so another checkout's volume of the same project is never deleted unasked.
- **`volume = "<id>"` keeps its meaning:** a volume you keep, never set with `volume_gb`.

## What it cost

`gpunit spend` prints what the provider billed for pods and network volumes over the last 7 whole UTC days, each
pod and window volume under its project.
`--days N` picks another window, from 1 to 3660; `--json` prints one object, its amounts in whole cents.

```console
$ uv run gpunit spend --days 7
spend, 2026-10-06 → 2026-10-12 (UTC)
pods      isekai               6 pods  $0.57
pods      unattributed         6 pods  $0.20
storage   db7sc8cild                   $0.31
total                                  $1.79
<UTC> the current UTC day is still being billed; its figures can change
```

- **Every amount is the provider's.** The pods' and the network volumes' billing is read from RunPod, never
  estimated from a price. The total sums the unrounded amounts, so a line's cents may miss it by a cent.
- **Pods and network volumes only.** Serverless endpoints, public endpoints and clusters billed to the same account
  are not read, so their charges are in no line and not in the total.
- **A pod's project comes from the ledger**, `~/.local/state/gpunit/ledger.jsonl`: `up` adds a line when a create
  answers, and `down` when it sweeps a pod no record names. Each line holds the pod's id, the project, the card,
  the image and the time; one that cannot be written warns and blocks nothing, one that cannot be read exits `1`.
- **`unattributed`** counts the pods the ledger does not name: made before this version, on another machine, by a
  create whose answer was lost, or outside gpunit.
- **`storage`** is one line per network volume the ledger does not name, billed whether or not a pod runs.
- **A window volume bills under its project**, in its amount; a project with a volume and no pod shows `0 pods`. One
  whose end fell before today and still bills today is named on stderr, with `gpunit volume down`.
- **The current UTC day is still being billed**: its figures can change, and stderr says so.
- **An unreadable billing exits `1`**, with no table: a table of zeros would read as a free week.

## The verbs

Each verb reads `gpunit.toml` from the working directory, or the file `--spec <path>` names; `serve` and each
`--serve` read the bundled model table instead, and `spend` reads only the billing and the ledger.

| verb | does |
|---|---|
| `gpunit up` | places a pod, waits for SSH, verifies its host key, records it in `.gpunit/` |
| `gpunit status [--json]` | prints the recorded session to stdout |
| `gpunit ssh` | opens a shell on the recorded pod |
| `gpunit down` | deletes the recorded pod, then every other live pod of the project |
| `gpunit run -- <cmd>` | the Python session around `<cmd>`: `up`, the tunnel, `<cmd>`, then `down`, however `<cmd>` ends |
| `gpunit serve <model> --ceiling <d>` | the price and `[y/N]`, then the session around a chat; `--api` for the endpoint ([how](#serve-a-model)) |
| `gpunit down --serve <model>` | `down` for the session `serve` left for `<model>` |
| `gpunit spend [--days N] [--json]` | the provider's billing over the last N UTC days, by project ([how](#what-it-cost)) |
| `gpunit volume up [--yes]` | the price and `[y/N]`, then creates the window volume, or extends a live one ([how](#working-window)) |
| `gpunit volume down` | deletes the window volume, then, after a lost create, each other `gpunit-<project>` volume you agree to |
| `gpunit volume up --serve <model> --ceiling <d>` | `volume up` for the row's volume, which `serve` mounts |
| `gpunit volume down --serve <model>` | `volume down` for the row's volume |

| exit | means |
|---|---|
| `0` | done; for `run`, the command's own code passes through |
| `1` | refused or failed; the teardown failed |
| `2` | usage: an unknown verb, a missing command, an unreadable spec path, `serve` or `volume up --serve` without `--ceiling`, an unknown model, `spend --days` under 1 or over 3660, `volume` without `up` or `down` |
| `3` | a create's answer was lost; a pod may exist and bill — run `gpunit down`; for a volume's create, `gpunit volume down` |
| `128+n` | signal `n` stopped `run` or `serve`, or killed `run`'s command, and the teardown succeeded; a failed teardown is still `1` |

gpunit's own lines go to stderr, each opening with the UTC time; stdout belongs to the command, or to `serve`'s
chat and `--api`'s two lines, or to `spend`'s report.

## The spend rules

- **The ceiling is required.** `boot.sh` stops the pod at it, whatever happens to the laptop.
- **The pod stops; `down` deletes.** A stopped pod bills storage, not GPU, until the next `gpunit down`.
- **A 404 is not "gone".** A wrong key gets a 404 too; `down` keeps the record and exits `1`.
- **A lost create exits `3`.** `.gpunit/pending` stays, and `down` sweeps every live `gpunit-<project>` pod.
- **One session per project.** `up` refuses on a record, a pending create, or a listed pod.
- **Secure cloud, port 22 only.** Other ports reach the laptop over the SSH tunnel, never a public proxy.
- **A fresh keypair per session**, in `.gpunit/`, deleted with the pod.
- **gpunit's ssh is its own.** No ssh_config is read, and only the session's key is offered; a user who wants
  their own config runs `ssh -i .gpunit/key` themselves.

## The proof — `make live`

`make live` rents one real pod for at most ten minutes plus its 420s wait for SSH, run by hand: it prints the
card's price and the maximum first, then runs `nvidia-smi` through `gpunit run`. The gate, `make gate`, fakes every
provider answer.

`make live-volume` opens a [working window](#working-window) of 10 GB for at most 30 minutes: one pod writes the UTC
time to the volume, a new pod reads it back, and the target fails unless the lines are equal.

`make live-serve MODEL=<row>` proves the serve image and a row on one of its cards, for at most 30 minutes plus the
1200s wait for SSH a session, inside the row's working window: `gpunit serve <row> --api` downloads the weights into
the volume for one `curl` and one tool call through [live/tool_call.py](live/tool_call.py), then a chat of one prompt
loads them from it. `MODEL` defaults to `qwen3-4b`.

`make live-dead` boots an image whose container exits at once, and passes when `up` exits `1` and prints its refusal
as `reason: <line>`. RunPod may restart such a container, so the reason can be the 120s wait's end.

`make live-serve-dead` serves `qwen3-4b` with an argument vLLM refuses, inside its working window, through
[live/serve_dead.py](live/serve_dead.py): it passes when the dead-pod refusal, the crash's lines from `pod.log` and
the delete within 15s all show. It is the dead-pod rule's live proof.
