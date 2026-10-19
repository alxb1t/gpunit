# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0/).

## [Unreleased]

### Added

- `tests/test_layers.py` holds the package's layers, lazy imports included, plus the stdlib-only, `sys.exit` and
  `RunPod`-construction rules, each with a twin that breaks it (`0015`).
- `docs/decisions.md`: the decisions in force, `D1`–`D51`, grouped by area. `tests/test_docs.py` holds the guide's
  links and anchors, every `decision Dn` cited, and no archived design's id outside that page (`0015`).

### Changed

- `__version__` lives in `gpunit/version.py`, which hatch reads; it breaks the cycle `gpunit.runpod` → `gpunit` →
  `gpunit.library` → `gpunit.runpod`. `cli` imports `serve.table` inside `_known` (`0015`).
- `library._open` is `library.open_session`, the seam `run` and `serve` open through; the provider's 400 is
  `provider.Unplaceable`, so *refusal* names gpunit's own. `lifecycle.delete_volume` is the one volume delete and
  its ledger line (`0015`).
- `gpunit/contract.py` holds the laptop's half of the boot contract: the pod's env (`pod_env`), the boot-log
  patterns, `fingerprint` and `old_boot`. `gpunit/hostkey.py` proves the host key; `lifecycle.up` tears down on its
  reason (`0015`).
- Code, configuration and the threat model cite `decision Dn` in place of an archived design's id; a live proof's
  own design id is dropped, its reason kept (`0015`).
- `make live` proved the moved pod env and host-key proof against RunPod on an A40 (`live/last_run.txt`,
  `0015`).

## [0.10.0] - 2026-10-18

### Added

- `serve` reads the operator's own rows beside the bundled ones, from `GPUNIT_MODELS` or
  `$XDG_CONFIG_HOME/gpunit/models.toml`; a row of a bundled name replaces it, said in one line (`0014`).
- `--models <path>` on `serve`, `down --serve` and `volume up|down --serve` names the user file first; without a
  model it exits `2` (`0014`).
- README's *Your own rows*; `live/models.toml`, the `granite-4.0-micro` row `make live-serve` proves; the threat
  model's F13 and T55, the user file. T34 is `partly`: `serve` pods ignore `datacenters` (`0014`).
- `make live-serve` proved a user file's row, `granite-4.0-micro` from `live/models.toml`, on a restricted key
  (`live/serve_last_run.txt`, `0014`).
- A user row passes the bundled rows' checks, and a user file holds rows alone; any row holding
  `--enable-log-requests` is refused. The unknown-model usage error names each row's source (`0014`).

### Changed

- `serve/launch.py` sets `DO_NOT_TRACK`, `HF_HUB_DISABLE_TELEMETRY` and `VLLM_NO_USAGE_STATS` and passes
  `--no-enable-log-requests` last, for every row; the bundled rows drop the flag (`0014`).
- The serve image rebuilt as `gpunit-vllm:v0.10-rc1`, for the new launcher, and re-pinned by digest (`0014`).

### Fixed

- The chat prints each streamed part without control characters but newline and tab, so a model's answer cannot
  steer the terminal; the conversation keeps the part as streamed (`0013·S4`).
- `docs/threat-model.md` re-cites `gpunit/spec.py` and `gpunit/volume.py`; README names the ledger's fields and that
  `serve` takes no `datacenters`; `_free_port`'s comment names `127.0.0.1` (`0013·R1`, `R2`, `R3`, `S5`).
- README's *Measured minimum* and the threat model's G6 name the restricted key's console settings:
  `api.runpod.io/graphql` Read / Write, `api.runpod.ai` None (`0013·R5`).
- `make live-serve-dead` reads the bundled table alone, so an operator's own `qwen3-4b` row cannot replace the
  broken one and serve a healthy model to the ceiling (`0014·R1`).
- A row's `args` holding a flag the launcher sets — `--revision`, `--code-revision`, `--tokenizer-revision`,
  `--served-model-name`, `--host`, `--port` or `--api-key`, `_` read as `-`, alone or as `--flag=value` — is
  refused, so a user row cannot repin its weights or code; T13, T55 and README *Your own rows* say so (`0014·S2`).
- The threat model's T30 cites the live run on `v0.10-rc1` for the quiet flag and its *Gaps* intro names `v0.10`;
  the bundled table's header names the user file's rows beside its own (`0014·R2`, `R3`, `R4`).

## [0.9.0] - 2026-10-18

### Added

- `datacenters = [...]` in `gpunit.toml`, an optional allow-list: the create names it, a mounted volume or a pod
  reported outside it refuses or tears down, and `volume up`'s stock choice stays within it (`0013`).
- `docs/threat-model.md`: what gpunit protects, from whom, and each threat's status at `v0.9`; README's
  *Security and privacy* says where data lands, how to pass a secret, the key's calls and the accepted risks.
  `CLAUDE.md` holds that a change touching a trust boundary updates the model (`0013`).
- The probe, by hand: a restricted key covers every call gpunit makes; the pod's own key reads its pod and the
  account's billing, and nothing else read; an account SSH key opens a root shell on a gpunit pod through RunPod's
  SSH proxy. README's *Accepted risks* names the last two; `docs/threat-model.md` holds no gap (`0013`).

### Changed

- **BREAKING:** `run`'s command gets no `RUNPOD_API_KEY`: it never needs the account key (`0013`).
- `[env]` refuses `RUNPOD_*` names, as it refuses `GPUNIT_*`; a `{{ RUNPOD_SECRET_name }}` value passes as written.
  `.gpunit/` is set to `0700` on every write, a found one too (`0013`).
- Each `serve` row passes vLLM `--no-enable-log-requests`, so the off stays explicit whatever a later vLLM
  defaults to; the image is unchanged (`0013`).

### Fixed

- `serve`'s printed pod-log lines drop C0, DEL and C1 characters, so a pod's output cannot steer the terminal;
  `pod.log` keeps them as read (`0013`).
- A tunnel's local port that another process took refuses and tears down, before the tunnel opens and in place of a
  reopen, so no traffic reaches a squatter; the busy-port probe reads `::1` as well as `127.0.0.1` (`0013`).
- The tunnel forwards `127.0.0.1` and `::1` as separate `-L`s: a squatter holding one loopback family ends `ssh` and
  refuses, where one `-L<local>:localhost:` forward stayed up on the other family and handed it the traffic for the
  whole session (`0013`).
- A taken-port `Refused` that the block swallows leaves Ctrl-C, `SIGTERM` and `SIGHUP` live: they still end the
  block and tear the pod down (`0013`).
- A dead tunnel's port is probed on every poll until the reopen, so a squatter that takes it during the backoff wait
  refuses within a second, not at the reopen up to 30 s later; the tunnel's `ssh` takes `ConnectTimeout=10`, which
  bounds how long a port is unheld while it connects, as `docs/threat-model.md` T9 now states (`0013`).
- `docs/threat-model.md` sets T21 `partly`, and README step 3 says `run`'s laptop command can still read the key
  from gpunit's own environment (`0013`).
- The `0012` cards: the CA-store tests bind `boot:refuse:no-ca-store` and `live/dead.py`'s guard binds
  `session:wait:dead-proof-spares-a-record`; `boot.py`'s stop comment names an untrusted certificate; README says
  `make live-dead` deletes what `up` left and rents nothing over a recorded pod (`0013`).

## [0.8.0] - 2026-10-17

### Added

- `boot/boot.py`: the pod's boot in stdlib Python 3.10, one function a step, every `boot:*` scenario unit-tested in
  `tests/test_boot_steps.py`; it prints `boot.sh`'s lines and needs neither `curl` nor `env`. It pauses 1s after its
  key line, so RunPod's log keeps it before `step: the command` (`0012`).
- The gate holds `boot/boot.py` at 100 % line and branch coverage (`pytest-cov`) and type-checks it as Python 3.10.

### Changed

- `boot.py` is the entrypoint of `serve/Dockerfile`, `live/Dockerfile` and `live/Dockerfile.dead`; they install
  `ca-certificates`, not `curl`. `tests/test_boot.py` runs `boot.py` end to end (`0012`).
- The serve image's `CMD` is `serve/launch.py`, in place of `sh -c`: it sets `HF_HOME` on a window volume and `exec`s
  vLLM, with no shell to misparse (`0012`).
- `make live-volume`, `make live-serve`, `make live-dead` and `make live-serve-dead` are one line each: their logic is
  `live/volume.py`, `live/serve.py`, `live/dead.py` and `live/serve_dead.py`, the window volume's teardown
  `live/window.py`, tested offline in `tests/test_live.py` (`0012`).
- README's step 2 adds `boot.py` from `v0.8.0` on `python3` 3.10 or newer; `CLAUDE.md` and the boot spec's Purpose
  name the Python files (`0012`).
- `gpunit-vllm`, `gpunit-live` and `gpunit-live-dead` rebuilt on `boot.py` at `v0.8-rc3`, after its stop's fixes, and
  re-pinned by digest (`0012`).
- `make live`, `make live-dead`, `make live-volume` and `make live-serve` passed on the `v0.8-rc2` images; their
  tails are in `live/last_run.txt` and `live/serve_last_run.txt`. The `v0.8-rc3` rebuild changed only `boot.py`'s stop
  and its log lines, held offline, and was not re-run (`0012`).

### Fixed

- A Ctrl-C during a live script waits for gpunit's own teardown: `live/window.py`'s `call` starts each gpunit child
  and waits through every interrupt before re-raising it, where `subprocess.run` killed the child 0.25s in, mid-delete;
  `live/dead.py` waits on its own `up` the same way, then runs `gpunit down`, since `up` has no SIGINT teardown of its
  own (`0012·R1`, `0012·S1`, `0012·R5`).
- `live/serve.py` ends the `serve --api` hold however its proof ends: a non-`OSError` from the chat request or the
  tool call no longer leaves the endpoint's pod held while the window's volume is deleted (`0012·S2`).
- `boot.py`'s stop follows no redirect, as `runpod.py`'s `_NoRedirect` already guards the laptop's side: a 3xx from
  the stop endpoint is a failed stop and retried, where urllib carried the key to the host it named (`0012·S3`) and
  read that host's 200 as the pod stopping, ending the ceiling while the pod billed (`0012·R8`, `0012·S5`).
- A stop that gets no answer names its cause, `the stop answered HTTP 000 (<cause>)`: an image without
  `ca-certificates` says its certificate check failed, where it said nothing (`0012·S4`).
- A watchdog whose stop raises an error it did not expect says the ceiling's stop failed, prints the traceback and
  exits `1`, where it exited `0` without a line (`0012·R6`).
- Design D1, D3, D4, D5 and D6 say what `boot.py`'s stop does: an opener built with `_NoRedirect`, `000 (<cause>)`
  on no answer, and the watchdog's failure line and exit `1`; a test comment names the watchdog's guard, not a
  `finally` (`0012·R2`, `0012·R3`, `0012·R4`).
- README says the serve proof sends one chat request, not one `curl`; design D12 and task 6.1 say the shipped images
  are `v0.8-rc3`; `test_the_cmd_is_launch_py` is bound to `serve:image:pinned-inputs`, whose scenario it checks
  (`0012·R2`, `0012·R3`, `0012·R4`).

- `boot.py`'s stop sends `User-Agent: gpunit-boot`, as the laptop sends its own: RunPod's Cloudflare refuses urllib's
  default agent with a 403 (code 1010), which would fail every stop, the ceiling's too (review `R1` at `65a8f39`).
- `boot.py` refuses before the arm, `no CA store for the stop's TLS; install ca-certificates in the image`, when
  OpenSSL finds no CA file and no CA directory holding a file: every stop would fail its certificate check, and the pod
  would bill past its ceiling (security `S3` at `65a8f39`).
- The `v0.8-rc3` images, `gpunit-vllm`, `gpunit-live` and `gpunit-live-dead`, predate the two `boot.py` fixes above:
  their `boot.py` sends urllib's default agent and arms without a CA store. They are not rebuilt or re-pinned here.
- `live/dead.py` runs `gpunit down` after `up` however `up` ends, and a failed `down` fails the run: a lost create or a
  failed teardown left the dead image's pod, which no ceiling stops, billing (security `S1` at `65a8f39`).
- A SIGHUP or SIGTERM during a live script is a Ctrl-C: `live/window.py`'s `hangups_interrupt` holds it while
  `window` and `live/dead.py` run, so their `down` still runs, as the recipes' `trap … EXIT` did on both (security
  `S2` at `65a8f39`).
- `tests/test_live.py` checks that `live/dead.py` waits `up` to its exit before `gpunit down` starts, where the
  Ctrl-C test checked only the `down` (review `R2` at `65a8f39`).
- `live/dead.py` refuses at once, with no `up` and no `down`, when this checkout's `.gpunit/` already records a pod
  (`pod` or `pending`), naming `gpunit down`: its `down` deleted that session's pod, and the run passed on `up`'s
  refusal; `tests/test_live.py` runs each test in a checkout of its own (security `S4` at `beef206`).

### Removed

- `boot/boot.sh`: consumers keep it at `v0.7.0` by its tag URL, and gpunit still reads its lines (`0012`).

## [0.7.1] - 2026-10-17

### Fixed

- `volume up` on a live volume never moves its end earlier, so a running session keeps its volume (`0010·R4`).
- The overdue sweep clears `.gpunit/volume.pending` beside the record it deletes (`0010·S4`); `serve` sweeps an
  overdue volume and refuses before its price (`0010·R6`).
- `volume down`'s lost-create sweep asks only a terminal, so a piped `y` deletes nothing (`0010·S3`), and Ctrl-C ends
  it with exit `130`, the rest and the mark kept (`0010·R9`); its message and ledger-skip test match it (`0010·R10`,
  `0010·R11`).
- Off a terminal, the sweep's no-answer line says to run `gpunit volume down` at a terminal or delete the volume by
  hand, since a rerun off one can never answer (0011 review `R3`).
- Each volume delete that answers `204` appends a `deleted` line to the ledger, and `spend` names no deleted volume as
  still billing past its end (`0010·R5`).
- An older `boot.sh` is judged only on a log read that opens with boot's `step: the ceiling` line, so a read cut
  before boot's lines names no wrong reason (`0010·R7`).
- `make live-volume` passed on a real volume: a pod wrote it, a new pod read it back, and its delete wrote the ledger's
  `deleted` line (`live/last_run.txt`).

## [0.7.0] - 2026-10-16

### Added

- The `Provider` seam reads a card's stock by data centre and the data centres with standard volumes, and creates,
  lists and deletes a network volume, so a window volume can be made where the cards are (0010).
- `gpunit.toml` takes `volume_gb`, `volume_ceiling` and `volume_datacenter`, refused without their pair, beside
  `volume`, or outside 10–4000 GB; `.gpunit/volume` records the window and the ledger names its volume and end.
- `gpunit volume up` creates `gpunit-<project>` where the first card of `gpus` is in stock, after the price, or extends
  a live one; `gpunit volume down` deletes it, and sweeps any other of its name only after a lost create, so another
  checkout's volume is never deleted (`0010·S1`); that sweep skips a volume the ledger records and deletes each other
  one only on a `y`, and a record beside the mark clears it unswept (`0010·S2`). A volume past its end is deleted first.
- A spec with `volume_gb` mounts the window's volume in `up`, `run` and `serve`, and refuses with none recorded or a
  session that would outlive it; `up` and `status` delete an overdue volume first, `down` after its pods, which may
  hold it (`0010·R2`); `status` names the volume.
- `gpunit volume up --serve <model> --ceiling 4h` makes the row's window volume, of its `disk_gb`, and `serve` mounts
  it; `gpunit volume down --serve <model>` deletes it. `serve` never creates a volume.
- `spend` bills a window volume under its project, a project with no pod showing `0 pods`, and names on stderr one
  that ended before today and still bills today, with `gpunit volume down`.
- `make live-volume` proves a window: one pod writes the volume, a new pod reads it back. `make live-serve` and
  `make live-serve-dead` run inside the row's window; `make live-dead` passes on `up`'s exit `1` and prints `reason:`.
  README's *Working window* and `CLAUDE.md` name the volume verbs and `make live-volume`.
- `live/last_run.txt` and `live/serve_last_run.txt` record `v0.6`'s acceptance, run inside working windows:
  `make live-volume`, `make live-serve` and `make live-serve-dead` pass, and `make live-dead` passes on its deadline's
  reason, the dead-pod rule's live proof being `make live-serve-dead` (`0009·L1`).

### Fixed

- `gpunit-vllm`, `gpunit-live` and `gpunit-live-dead` carry the released `boot.sh` and are re-pinned by digest:
  `gpunit-vllm:v0.7-rc2` from `build-serve-image` run 38893906654, with the `CMD` fixed below; the live images pushed
  by hand for `linux/amd64`.
  `v0.6.0`'s digests carried the `boot.sh` of `057ce89`, from before `681e23c` (`0009·R6`, `0009·S3`).
- The serve image starts vLLM with a volume mounted: its `CMD` set `HF_HOME` inside `${…:+…}`, whose `;` is a word,
  so `sh` ran one `export` over vLLM's arguments and exited `2`. `serve --volume` broke the same way since `v0.3`.
  `make live-volume`'s cards add the RTX PRO 4500 Blackwell and the RTX 4090, under `max_hourly = 0.90`.
- A log read since the create holds the pod's lines: RunPod's `since` stream sends none, so the read takes the last
  5000 lines and keeps those from that second on. `serve`'s `pod.log`, the host-key fallback and the older-`boot.sh`
  refusal read nothing on a real pod before. The host-key poll now makes one read of the last 5000 lines, a key line
  further back being lost, and judges an older `boot.sh` only on a read that holds the whole log (`0010·R3`).

## [0.6.0] - 2026-10-15

### Added

- `make live-serve-dead` runs `live/serve_dead.py`: `qwen3-4b` with an argument vLLM refuses, passing only when the
  dead-pod refusal, the crash's `pod:` lines and the delete within 15 s all show; its `check` is tested offline.
- README's step 2 adds `boot.sh` from `v0.6.0` and says an older one is refused; *Serve a model* names the dead-pod
  refusal, `pod.log` and boot's 60 s grace; the proof names `make live-serve-dead`, as `CLAUDE.md`'s invariant does.

### Changed

- **BREAKING for a consumer's image:** each pod gets a fresh `GPUNIT_NONCE`; `boot.sh` prints it in its key line,
  `gpunit host key <nonce>: SHA256:…`, and keeps it from the command, so an echoed key line is never the key
  (`0006·S1`). An older `boot.sh` is refused at once, naming `v0.6.0`, judged on the log since the create alone, so
  a command's echo in the tail cannot trigger it; `boot.sh` checks the nonce after the ceiling is armed, so an older
  gpunit's pod stops. README's install pin moves to `v0.6.0` with step 2.
- `boot.sh` waits 60 s after the command exits before it stops the pod, so gpunit reads the exit line; the ceiling
  and a refusal stop without it.
- `gpunit-vllm`, `gpunit-live` and `gpunit-live-dead` are rebuilt with this `boot.sh` and pinned by digest:
  `gpunit-vllm:v0.6-rc1` from `build-serve-image` run 38717674106, the live images pushed by hand for `linux/amd64`.
- `live/last_run.txt`: `make live` verifies the host key through the nonce; `make live-dead` tears its pod down on the
  120 s deadline rather than the dead-pod rule, recorded as such. The serve runs move to the next version.

### Fixed

- A pod that stops while `serve` waits for the model, or holds the endpoint, ends the session: two polls in a row
  reading a dead status refuse with `the pod stopped while the model loaded` or `… while serving`, and tear it down.
  One `DeadPod` rule in `lifecycle.py` serves `up`'s wait and both of `serve`'s.
- `serve` keeps the pod's log at `~/.local/state/gpunit/serve/<model>/pod.log` (mode `0600`), read since the create
  every 30 s, since RunPod drops it when the pod stops; a dead-pod refusal, or the `--api` hold's quiet one, prints its
  last 30 lines and names the file. The last session's file is removed once a new pod's create begins, so a `serve`
  refused before it leaves the file in place.
- README's exit row for `2` names `spend --days` over 3660; the unreadable-ledger test carries its own scenario key,
  and `spend`'s docstring names the ledger (`0007·R6`, `0007·R7`).

## [0.5.0] - 2026-10-13

### Added

- The model table's second row, `qwen3.8-27b`: `Qwen/Qwen3.8-27B-FP8` at a pinned revision, on a 48 GB card, with
  the `qwen3_coder` tool-call parser, the language model alone and 64 concurrent sequences (its Mamba cache holds 192
  on 48 GB), so `serve` offers a model large enough for an agent.
- `live/tool_call.py` sends one chat request with a function and passes only on a parseable call to it, the key read
  from `OPENAI_API_KEY` and a base URL that is not http(s) refused without echoing it; `make live-serve MODEL=<row>`
  runs it after the `curl`, so a live run proves a row's tools.
- README's *Serve a model* names both rows and their cards; its proof paragraph says `make live-serve MODEL=<row>`.
- `live/serve_last_run.txt`: `make live-serve MODEL=qwen3.8-27b` on an NVIDIA A40 answers the `curl`, the chat, and
  the tool call `get_weather {"city": "Paris"}`.

## [0.4.0] - 2026-10-12

### Added

- A ledger at `~/.local/state/gpunit/ledger.jsonl` names each pod `up` creates and `down` sweeps, with its project,
  so its billing finds the project after teardown; a ledger that cannot be written warns and blocks nothing.
- The provider seam reads the pods' and the network volumes' billing in UTC day buckets, each record's
  `totalAmount` as RunPod charged it; an answer that does not read is `Lost`.
- `gpunit spend [--days N] [--json]` reports the last N whole UTC days' billing, N from 1 to 3660: one line per
  project, the pods the ledger does not name, each volume, and the total; an unreadable billing or ledger exits `1`,
  never a table of zeros.
- README's *What it cost* explains the report, `unattributed` and the day still billing; `CLAUDE.md` names
  `ledger.py` and `spend.py`.
- `live/spend_last_run.txt`: `gpunit spend --days 7`'s total matches the RunPod console's to the cent, $1.80.

## [0.3.1] - 2026-10-12

### Fixed

- The host key is the last one boot printed before its `step: the command` line, so a command that echoes a key
  line cannot supply it; a key line with no step after it is not yet read.
- `serve` forwards to a free local port picked before the price, so a busy 8000 is never refused after a `y`;
  Ctrl-C at the question says `not rented` and exits `130`; the chat ends when the server cannot be reached,
  or when the tunnel closes the connection with no answer.
- `qwen3-4b`'s cards are 24 GB only: the RTX A4500 (20 GB) gives way to the L4.
- A pod `EXITED`, `ERROR` or `TERMINATED` on two polls in a row ends the wait and is torn down, so a container
  that cannot start stops billing in seconds, not at `timeout`.

### Added

- `make live-dead`: an image without `curl`, so boot refuses and the container exits, to show what RunPod reports
  for a dead boot. `live/price.py` takes a spec path and counts the wait for SSH with the ceiling.
- The image `gpunit-live-dead` is built and pinned by digest; `make live-dead` saw RunPod report `EXITED`, and `up`
  tore the pod down in 17s. `make live` passed on an A40; no pod was left ([live/last_run.txt](live/last_run.txt)).

### Changed

- README, the `live-serve` comment and `CLAUDE.md` say what the code does: the serve diagram's end, the live runs'
  wait for SSH, and what a patch may hold.

## [0.3.0] - 2026-10-12

### Added

- The model table `gpunit/serve/models.toml`: `qwen3-4b` at a pinned revision, and the serve image by digest.
  `gpunit.serve.table` refuses a moving revision, a tagged image or a missing field, and builds a row's `Spec`.
- `gpunit serve <model> --ceiling …` prints each card's price and the most the session can cost, and rents nothing
  without a `y` (`--yes` skips the question); it waits up to 1200s for the model, with its files under
  `~/.local/state/gpunit/serve/<model>/`. `gpunit down --serve <model>` tears that session down.
- The chat: each answer streams as it is written, the conversation is kept in memory, and thinking is off
  unless `--think`. `/exit` or the end of input ends the session.
- `--api` prints `OPENAI_BASE_URL` on loopback and a per-session `OPENAI_API_KEY` the model server requires, and
  holds the session until Ctrl-C, or until the server has not answered for 60s.
- `serve/Dockerfile`, vLLM `v0.31.0` by digest with sshd and `boot.sh`, built only by a manual run of
  `build-serve-image.yml`, which refuses `latest` and writes the digest to its summary. `make live-serve` is the
  metered proof.
- The serve image `gpunit-vllm:v0.3-rc1` is built and pinned by digest in `models.toml`; `make live-serve` passed on
  an RTX A5000, a `curl` and a chat each answered, and no pod was left ([live/serve_last_run.txt](live/serve_last_run.txt)).

### Changed

- README: *Serve a model*, with *From a container*; the verbs and exits name `serve` and `down --serve`.
  `CLAUDE.md`'s layout names `gpunit/serve/` and `serve/`.

### Fixed

- `gpunit serve` waits up to 1200s, not 420s, for the pod's SSH port, so a cold host's pull of vLLM's image no
  longer tears the session down before the model wait begins.
- `gpunit serve`'s "at most" price counts the 1200s SSH wait with the ceiling: the pod bills while it pulls, and
  boot arms the ceiling only after, so the figure agreed is no longer short by up to 20 minutes of the dearest card.

## [0.2.0] - 2026-10-09

### Added

- A pod with a `volume` is told `GPUNIT_VOLUME_ID` and `GPUNIT_VOLUME_PATH`, so a command reads its volume in
  gpunit's words. `[env]` naming a `GPUNIT_*` variable is refused.
- gpunit's lines go through a swappable sink; the default one survives a closed stderr, so a dead pipe ends no
  teardown, and the process still exits with the code the teardown earned, not `120`. A stderr with no
  descriptor, or no null device to open, is swallowed too.
- `gpunit.session(spec, environ=…, cwd=…, say=…)` opens a session from Python as a `with` block, yielding a
  `Session` (`host`, `port()`, `ssh`, `image`, `pod_id`), and tears it down on every way out. It raises
  `Refused`, `Lost`, `TeardownFailed` and `Interrupted`, and owns the signals and the tunnel thread while open.
  A refusal while it opens whose own teardown failed raises `TeardownFailed`, never `Refused`.

### Changed

- README: *Use it from Python* documents `gpunit.session`, its attributes, exceptions, signals, `environ` and
  `say`; the volume's `GPUNIT_VOLUME_PATH` and the refused `GPUNIT_*` env names are in the spec example.
- `gpunit run` runs on `gpunit.session`: one implementation of the session, its exit codes read from the
  library's exceptions. A signal that lands while it starts the command is held until it has the command's
  handle, so the command is terminated, never left running.
- `gpunit/session.py` is `gpunit/lifecycle.py`: the package's `session` names the library's function, which
  would hide a submodule of that name.
- `make live` passed on the existing `live` image with `gpunit run` on the library: the host key verified,
  `nvidia-smi` ran, and the pod was deleted. The tail is in `live/last_run.txt`.

## [0.1.2] - 2026-10-08

### Security

- `boot.sh` runs the command under `env -u RUNPOD_API_KEY`: the account-wide key stays boot's, for the stop,
  and is not in the command's environment. The command still runs as root beside boot, so it can read the key
  from boot's own environment in `/proc`; run no code on the pod you would not trust with the key. Boot refuses
  an image without coreutils' `env`.

### Fixed

- An interrupt before any create began tears nothing down: `run` no longer sweeps another working copy's pod
  of the same project, and says no create began. A record or pending marker left by an earlier `gpunit up`
  no longer counts as this run's create: an interrupt before `up` refuses deletes neither that session's pod
  nor any other listed one.
- A host-key line pushed out of the log's last 5000 lines is read again from the create's time, so a boot
  that logs heavily no longer tears a healthy pod down; `created` is stamped before the create.
- A stop answered `401` or `403` says the key cannot stop this pod and to delete it by hand, then retries,
  instead of an outage's message.
- README: the image needs coreutils' `env`, the command's environment on the pod does not carry
  `RUNPOD_API_KEY` (though a root command can still read it from boot's process), and the pins move to `v0.1.2`.
- `make live` passed on a rebuilt `live` image carrying this `boot.sh`: the host key verified, `nvidia-smi` ran
  over `GPUNIT_SSH`, and the pod was deleted; it is the first live run of `AllowUsers root`. The tail is in
  `live/last_run.txt`.

## [0.1.1] - 2026-10-08

### Security

- Every ssh line is gpunit's own: `-F none -o IdentitiesOnly=yes`, so a user's ssh_config cannot forward their
  agent, proxy or multiplex to the pod.
- The API client follows no redirect: a 3xx is read as a failed answer, so the key never reaches another host;
  the redirect test also shows an unguarded opener leaking the key.
- `boot.sh`'s sshd admits root alone (`AllowUsers root`), so a key the image baked in for another account, even a
  `!`-locked one, opens no login on the pod.

### Fixed

- `up` checks `ssh`, `ssh-keygen` and `ssh-keyscan` before any request, so a missing tool no longer leaks a pod;
  `gpunit ssh` without `ssh` refuses instead of a traceback.
- `gpunit.toml` refuses a port outside 1–65535 before anything is rented.
- A delete answering `200` is a success for `down` and the sweep, as it already was for `RunPod.delete`.
- The pod's log read ends once the stream is quiet for 3 s, not after a fixed 10 s; a stream that never goes
  quiet still ends at 10 s.
- `run` exits `128 + n` when signal `n` killed the command, as a shell does, not a negative code.
- A tunnel that keeps dying is reopened with backoff, 1 s doubling to 30 s, so it no longer floods stderr.
- `boot.sh` starts sshd with `UsePAM yes`, so a root whose password is locked with `!` still logs in by key.
- The curl refusal is its own test under `boot:refuse:no-curl`, apart from the sshd one.
- `session:ssh:no-ssh-refuses` is checked through the CLI too: `gpunit ssh` without `ssh` exits `1`.
- README: the design link points at the archive, the pins move to `v0.1.1`, a spend rule says gpunit's ssh is
  its own, and the `128+n` row covers a command killed by a signal.
- `make live` passed on a rebuilt `live` image carrying this `boot.sh` before `AllowUsers root`: the host key
  verified and `nvidia-smi` ran over `GPUNIT_SSH` under `-F none`, with sshd on `UsePAM yes`; the run's tail is in
  `live/last_run.txt`.

## [0.1.0] - 2026-10-07

### Added

- The `gpunit` package skeleton: the CLI parser with its usage exit `2`, `gpunit.toml` loaded strictly into
  a `Spec`, and the `.gpunit/` session files with a fresh keypair at `0600`.
- The gate grows to `uv sync`, ruff, ty and pytest before `openspec validate`, so the package is checked offline.
- The `Provider` seam and its RunPod implementation on `urllib`: the key only in a request header, a 400
  refused, a 5xx or a lost answer `Lost`, a listing that never reads a look-alike or a bare pod as ours.
- `gpunit up`, `status` and `down`: one create per card, a lost create exits `3` and is swept later, the wait
  and the host-key check tear down on failure, and `down` never reads a 404 as gone.
- `gpunit run -- <cmd>` and `gpunit ssh`: the session handed over in the environment, the tunnel reopened,
  teardown on exit and on every signal; a busy local port refuses before anything is rented.
- `boot/boot.sh`, the pod's half: the ceiling and an exit trap that stop the pod with backoff, sshd on a
  fresh host key, the fingerprint line, and the command as a child whose code is boot's.
- `README.md` and `CLAUDE.md` describe the package: a consumer's steps, the verbs and exit codes, the spend rules,
  the layout and the invariants.
- `make live`, the metered proof: a real pod placed, its host key verified and torn down, and a second pod
  stopped by its own ceiling; the run's tail is `live/last_run.txt`.

### Fixed

- RunPod requests send `User-Agent: gpunit/<version>`: RunPod's Cloudflare refused Python's default agent
  with a 403 (code 1010), which `make live` found.
- `gpunit run` exits `1` when a signal is followed by a failed teardown; it exited `128+n`, which reads as torn down.
- `boot.sh` makes a fresh host key in a new directory on every boot; it served any key the image baked in, as
  installing `openssh-server` on Debian or Ubuntu does.
- `boot.sh` refuses an image without `curl`; the ceiling's stop needs it, and without it retried forever.
- `boot.sh` starts sshd on a config of its own that names only the fresh host key; `-o HostKey` added it to
  the keys the image's `sshd_config` names, so an image naming its own `HostKey` lines served those too.
