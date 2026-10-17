# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0/).

## [Unreleased]

### Fixed

- `volume up` on a live volume never moves its end earlier, so a running session keeps its volume (`0010·R4`).
- The overdue sweep clears `.gpunit/volume.pending` beside the record it deletes (`0010·S4`); `serve` sweeps an
  overdue volume and refuses before its price (`0010·R6`).
- `volume down`'s lost-create sweep asks only a terminal, so a piped `y` deletes nothing (`0010·S3`), and Ctrl-C ends
  it with exit `130`, the rest and the mark kept (`0010·R9`); its message and ledger-skip test match it (`0010·R10`,
  `0010·R11`).

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
