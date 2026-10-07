# Design — 0001 core

How one package owns a GPU session: the seam, the lifecycle, the boot, the gate, and the one metered proof.
**Verdict: feasible** — every rule here already runs in isekai's bash; the work is a port into tested Python and
one shell file.

## Context

See [proposal](proposal.md) — *Why*. What holds at the cut:

- **This repo** (`ebdb496`): the bootstrap alone — `Makefile` with `openspec validate`, `CLAUDE.md`, `CHANGELOG.md`,
  `README.md`, `openspec/`. No code, no `pyproject.toml`.
- **The source, isekai `main` at `ac22bdf`.** `infra/up.sh` (309 lines): the key on a file descriptor (`:26`);
  the volume's data centre read and matched (`:49-66`); the pod found by name and image (`:75`, `infra/pods.sh:8`);
  the catalogue floor (`:87`); the host-key log read, scan and match (`:118-164`); the create loop, one GPU type
  per call, 400 moves on, 5xx/000 is lost (`:206-246`); the bounded 420 s wait that tears down (`:273-293`).
  `infra/down.sh` (80 lines): a 404 keeps the record (`:41`); the sweep (`:57-79`). `infra/render.sh` (176
  lines): the trap set before the pod exists, a second Ctrl-C ignored (`:98-115`); the tunnel reopened (`:148-162`).
  `start.sh:12-16`: the ceiling and the exit trap; `:32` the fingerprint line. `tools/stop_pod.sh`: the stop with
  backoff to 300 s (`:12-13`, `:19-31`). The gate: `Makefile:6-19`.
- **Synthetic Portraits `main` at `2bd0b72`.** `infra/up.sh:27` on `rest.runpod.io/v1`; a long-lived key at
  `~/.ssh/id_ed25519_runpod` (`:34`). Not a source — a consumer.
- **RunPod's REST v2**, as isekai calls it: `GET /catalog/gpus/{id}` (`memory`), `GET /network-volumes/{id}`
  (`dataCenter`, `size`), `POST /pods` (201, `id`), `GET /pods/{id}` (`ssh.direct.host`, `.port`, `status`),
  `GET /pods/{id}/logs?tail=&source=container` (SSE lines), `GET /pods?limit=&cursor=` (`pods[]`,
  `pagination.hasNextPage`, `.nextCursor`), `DELETE /pods/{id}` (204), `POST /pods/{id}/action` `{"action":"stop"}`
  (200). Errors are `problem+json` with `title` and `detail`.
- **What RunPod injects into a pod:** `RUNPOD_API_KEY`, `RUNPOD_POD_ID`, and `PUBLIC_KEY` from the create's `env`.

## Goals / Non-Goals

**Goals:** one tested implementation of the lifecycle; a consumer that writes one TOML file, one Dockerfile line
and one `run` call; a gate that never touches the network; one metered proof by hand.

**Non-Goals:** a public Python API; a second provider; serving; the tailnet; volumes' lifecycle; a laptop-side
ceiling.

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| [D1](#d1) | flat package `gpunit/`, hatchling, Python ≥3.11, zero runtime dependencies | a consumer inherits no dependency; `tomllib` needs 3.11 | `src/` layout; `requests`; the RunPod SDK |
| [D2](#d2) | a `Provider` protocol — `gpu · volume · create · get · log · list · delete · stop` — provider nouns kept out | the contract must not be RunPod's shape by accident | a RunPod client called directly |
| [D3](#d3) | `RunPod` on `urllib`, every call bounded to 30 s, the key only in a request header | the key never reaches a subprocess; a stalled read cannot hold the poll | `curl` via subprocess |
| [D4](#d4) | `Spec` from `gpunit.toml`, strict keys, digest required, ceiling required | isekai's pin rule; a session with no end bills forever | defaults for the ceiling; `.env` |
| [D5](#d5) | `.gpunit/` in cwd: `pod`, `pending`, `known_hosts`, `key`, `key.pub` | per working directory, as isekai's dotfiles; one pod per project is enforced by the listing | a lock file; `~/.gpunit` |
| [D6](#d6) | an Ed25519 keypair per session, `ssh-keygen` into `.gpunit/`, deleted at teardown | nothing long-lived is authorized on a pod | `~/.ssh/id_ed25519_runpod` |
| [D7](#d7) | placement: catalogue floor → one create per card → 400 moves on → 5xx/transport/201-without-id is `Lost` | isekai `up.sh:206-246` verbatim | walking the list server-side |
| [D8](#d8) | the wait and the host key: bounded poll, log line vs keyscan, teardown on timeout or mismatch | `up.sh:118-164`, `:273-293` verbatim | trusting the first key seen |
| [D9](#d9) | teardown: a 404 keeps the record; sweep every listed pod; `pending` cleared only after a clean sweep | `down.sh` verbatim: a false "gone" leaves a pod billing | reading 404 as gone |
| [D10](#d10) | `run`: tunnel child, command child, teardown in a `finally` and in the signal handlers, second interrupt ignored; exits `0 · 1 · 2 · 3` | `render.sh:98-162` verbatim | a laptop watchdog |
| [D11](#d11) | `boot/boot.sh`: isekai's `start.sh:12-32` and `stop_pod.sh` generalised; the pod *stops*, `down` deletes | one file a Dockerfile `ADD`s by sha256 | a `gpunit-boot` image |
| [D12](#d12) | stderr lines `YYYY-MM-DDTHH:MM:SSZ <text>`; refusals open `refused:`; `--json` on `status` only | one boot log says where the minutes go | the `logging` module |
| [D13](#d13) | the gate as isekai's; tests on `FakeProvider` and hand-written v2 fixtures; `@pytest.mark.spec` keys | a test that bills cannot be a gate | recording fixtures live |
| [D14](#d14) | `make live`: `live/Dockerfile` on plain Ubuntu, pushed by hand, its digest in `live/gpunit.toml`; price printed first; the run's tail committed as `live/last_run.txt` | the one proof of the spend rules on a real account | CI |

### D1

```
gpunit/
├── pyproject.toml      hatchling · requires-python >=3.11 · no dependencies · dev: ruff, ty, pytest
├── gpunit/
│   ├── __init__.py     __version__
│   ├── __main__.py     python -m gpunit
│   ├── cli.py          argparse: up · status · down · ssh · run; the exit codes
│   ├── spec.py         Spec, load_spec, parse_ceiling
│   ├── state.py        State: the .gpunit/ files
│   ├── provider.py     Provider protocol, Lost, Refused, the answer types
│   ├── runpod.py       RunPod(Provider) on urllib
│   ├── session.py      up · status · down · ssh — the lifecycle
│   ├── run.py          run — the tunnel, the child, the teardown
│   └── log.py          say(), refuse()
├── boot/boot.sh
├── live/               Dockerfile · gpunit.toml · last_run.txt
├── tests/              fakes.py · fixtures/*.json · test_*.py
└── Makefile
```

`uv` manages the environment; `uv.lock` is committed. The CLI is `gpunit` via `[project.scripts]`, installed by a
consumer as `uv add --dev git+https://github.com/alxb1t/gpunit@v0.1.0`.

### D2

```
class Provider(Protocol):
    def gpu(self, name: str) -> GpuInfo                      # vram_gb, hourly  — Unknown on 404
    def volume(self, volume_id: str) -> VolumeInfo           # datacenter, size_gb
    def create(self, spec: Spec, gpu: str, pubkey: str, ceiling_s: int) -> str   # the id; Refused on 400; Lost otherwise
    def get(self, pod_id: str) -> PodInfo | None             # status, host, port; None on a failed read
    def log(self, pod_id: str, *, tail: int) -> list[str]
    def list(self, project: str, image: str) -> list[tuple[str, str]]   # (id, status) — NoImage on a bare pod
    def delete(self, pod_id: str) -> int                     # the HTTP status
    def stop(self, pod_id: str) -> int
```

`Lost`, `Refused`, `Unknown`, `NoImage` are exceptions in `provider.py`. `session.py` and `run.py` see only this
protocol; `FakeProvider` in `tests/fakes.py` implements it with scripted answers.

### D3

- `RunPod.__init__` reads `RUNPOD_API_KEY` from `os.environ` and refuses when empty.
- Each call builds a `urllib.request.Request` with `Authorization: Bearer …` and `timeout=30`; a `URLError` or a
  timeout is a transport failure.
- A `problem+json` body is reported as `title: detail`, else the body's first 200 characters.
- The listing walks `cursor` to a bound of 100 pages, refusing a cursor answered twice.
- The log read uses `tail=5000&source=container`, keeps lines starting `data: `, parses each as JSON, and matches
  `^gpunit host key: (SHA256:[A-Za-z0-9+/]+)\s*$`; the last match wins.

### D4

- `Spec` is a frozen dataclass; `load_spec(path)` reads TOML with `tomllib`.
- A missing required key, a wrong type, or an unknown key refuses — the unknown one naming the nearest known key
  by `difflib.get_close_matches`.
- `ports` accepts an int or a table `{remote, local}`; `parse_ceiling("45m") → 2700`, the unit required.
- The `image` regex is `@sha256:[0-9a-f]{64}$`.
- `[env]` is passed to the create as is, after `PUBLIC_KEY` and `GPUNIT_CEILING`, which win; `ram_gb` and `cuda`
  go into the create when set.

### D5

```
.gpunit/
├── pod            {"id", "image", "host", "port", "created"}  — written after the create answered 201
├── pending        empty; from the first create until the record, or until every create refused
├── known_hosts    the scanned key, written only after the match
├── key            0600
└── key.pub
```

`State` reads and writes these; `up` refuses on `pod` or `pending`. The consumer adds `.gpunit/` to its
`.gitignore`; `up` warns once when it is not ignored.

### D6

`ssh-keygen -q -t ed25519 -N "" -f .gpunit/key -C gpunit-<project>` before the create; `delete` in `down` removes
both files with the record. An `ssh-keygen` not on `PATH` refuses before any request.

### D7

```
up
 ├─ spec, key, state, port checks        (no request)
 ├─ volume(id) → datacenter              refuse on failure
 ├─ for card in gpus: gpu(card)          refuse on Unknown; skip under vram_gb or over max_hourly
 ├─ keygen; write pending
 ├─ for card: create(...)                Refused (400) → next · Lost → exit 3, pending stays · id → break
 ├─ none → remove pending, exit 1
 ├─ write pod record
 ├─ wait(timeout) for host+port          deadline → down, exit 1
 ├─ verify host key                      no line 60 s / no scan 180 s / mismatch → down, exit 1
 └─ print the session
```

### D8

The wait polls `get` every 5 s; `None` is not yet. The host key: poll `log` every 5 s for 60 s for the
fingerprint; then `ssh-keyscan -T 10 -t ed25519 -p <port> <host>` every 5 s for 180 s; compare
`ssh-keygen -lf -` of the scanned line with the printed fingerprint. Both `ssh-keyscan` and `ssh-keygen` run via
`subprocess` with the host and port as arguments — no secret rides them.

### D9

`down`: delete the recorded pod; `204` clears `pod`, `known_hosts`, `key`, `key.pub`; `404` and anything else keep
them and set the exit to `1`. Then `list(project, image)`: an unreadable listing exits `1`; each listed pod not the
recorded one is deleted; `pending` is removed only when nothing failed. `status != "TERMINATED"` is live.

### D10

```
run -- <cmd>
 ├─ busy-port check (no request)
 ├─ install handlers: SIGINT, SIGTERM, SIGHUP → set `stopping`, kill the child; a second signal is ignored
 ├─ up()                                  Lost → down(), exit 3
 ├─ tunnel = Popen(ssh -N -L ... -o ExitOnForwardFailure=yes -o BatchMode=yes)
 ├─ child = Popen(cmd, env | GPUNIT_HOST, GPUNIT_PORT_<r>, GPUNIT_SSH)
 ├─ while child runs: if tunnel exited → log, reopen
 └─ finally: kill tunnel; down(); exit child's code, or 1 if down failed, or 130/143/129 on a signal
```

`GPUNIT_SSH` is the full `ssh -i .gpunit/key -o UserKnownHostsFile=.gpunit/known_hosts -o StrictHostKeyChecking=yes
root@<host> -p <port>` line. No app-health wait: the consumer polls its own port.

### D11

`boot/boot.sh -- <cmd>`, bash, `set -uo pipefail`:

```
1 check: sshd and curl on PATH; RUNPOD_API_KEY, RUNPOD_POD_ID, PUBLIC_KEY, GPUNIT_CEILING; a command after --
2 arm:   ( sleep "$GPUNIT_CEILING"; stop ) &   and   trap stop EXIT
3 sshd:  authorized_keys from PUBLIC_KEY; ssh-keygen a fresh ed25519 host key in a mktemp -d dir; sshd -f on a
         config boot writes there: that HostKey alone, root by key, no password, sftp internal
4 print: "gpunit host key: SHA256:…"
5 run:   "$@" as a child; SIGTERM forwarded; wait; exit its code (the trap stops the pod)
```

`stop` is `stop_pod.sh`'s loop: `POST /pods/$RUNPOD_POD_ID/action {"action":"stop"}` with `curl`, the key on a
file descriptor, retry doubling from 30 s to 300 s until `200`. sshd runs on boot's config, never the image's:
`HostKey` is a list, so a key the image's `sshd_config` names would be served too, and `-o HostKey` only adds
to it. A consumer's Dockerfile:

```
ADD --checksum=sha256:<digest> https://raw.githubusercontent.com/alxb1t/gpunit/v0.1.0/boot/boot.sh /opt/gpunit/boot.sh
RUN chmod +x /opt/gpunit/boot.sh
ENTRYPOINT ["/opt/gpunit/boot.sh", "--"]
CMD ["python3", "main.py", "--listen", "0.0.0.0", "--port", "8188"]
```

The pod stops, not deletes: a stopped pod bills storage only and `down` deletes it on the next sweep. Whether the
injected key may stop the pod is proven by [D14](#d14).

### D12

`log.say(text)` writes `<UTC> <text>` to stderr; `log.refuse(text)` writes `<UTC> refused: <text>` and raises
`Refusal`, which `cli.py` turns into exit `1`. `cli.py` is the only place `sys.exit` is called.

### D13

`Makefile`'s `gate` becomes, in order: `uv sync --locked` · `uv run ruff format --check .` · `uv run ruff check .`
· `uv run ty check` · `uv run pytest` · `openspec validate --all --strict --no-interactive`. Ruff selects
`E, F, I, D, ANN`; tests waive `D1`. Tests run the CLI in-process via `cli.main(argv, provider=FakeProvider(...))`
against a `tmp_path` cwd; `tests/fixtures/` holds JSON bodies in RunPod's v2 shape for the catalogue, a volume, a
pod, a page of pods, a log, and `problem+json` errors. `boot.sh` is tested by running it under `bash` with a stub
`sshd`, `ssh-keygen` and `curl` on `PATH` in `tmp_path`, as isekai's `tests/test_infra.py` does. Every test
carries `@pytest.mark.spec("<key>")`, registered in `pyproject.toml`.

### D14

`live/Dockerfile`: `FROM ubuntu:22.04@sha256:…`, `openssh-server` installed and its host keys deleted, `boot.sh`
copied from the tree, `ENTRYPOINT ["/opt/gpunit/boot.sh", "--"]`, `CMD ["sleep", "infinity"]`. No CUDA: RunPod
mounts the driver and `nvidia-smi`. Built and pushed by hand as `ghcr.io/alxb1t/gpunit-live`, its digest written
into `live/gpunit.toml` (`ceiling = "10m"`, `gpus` the cheapest secure-cloud card, no volume). `make live` prints
the card's hourly price and the ten-minute maximum, then runs `gpunit run --spec live/gpunit.toml -- nvidia-smi`
with `GPUNIT_SSH` and, after it returns, `gpunit status` to show no record; the operator appends the last lines to
`live/last_run.txt` with the date.

## Dependencies

Development only; no runtime dependency.

- `ruff>=0.16.0` — format and lint, as isekai.
- `ty>=0.0.64` — strict types, as isekai.
- `pytest>=9.1.1` — the tests.

## Risks / Trade-offs

- **The injected key cannot stop the pod** → `make live` proves it before release; if it cannot, the ceiling falls
  back to a laptop-side `down` in a later change and the release waits.
- **RunPod's v2 shapes drift from the hand-written fixtures** → `make live` is the check; a drift is a patch.
- **`ADD --checksum` needs BuildKit** → the README says so; a consumer on an older Docker copies the file in.
- **A stopped pod is not deleted until the next `down`** → it bills storage, not GPU; the sweep names it.
- **`ssh-keyscan` sees a different host than the API's log** → the mismatch tears down; the operator re-runs.

## Verdict

Feasible: a port of proven bash into a tested package, one shell file, and one metered proof. The one unknown —
the injected key's power to stop — has a halt and a fallback.
