# Decisions in force

The choices gpunit is built on, each with why and the archived decisions that made it. **A change that makes or
overturns a decision edits this page**; its own `design.md` keeps the history. Code cites a decision as
`decision Dn`; an overturned one is not listed, and the archive keeps it.

Each decision states the choice and why. Behaviour is the spec's: a decision links it. A value is its file's: a
decision names the file.

## The package

### D1 · A flat stdlib package, Python 3.11, no runtime dependency

**`gpunit/` is one flat package on the standard library, for Python 3.11 and later; `dependencies = []`.**

`pyproject.toml` holds the floor and the empty list.

- **Why:** A consumer adds gpunit as a dev tool and inherits nothing; `tomllib` needs 3.11.
- **Made by:** `0001·D1`, `0016·D1`.

### D2 · A `Provider` protocol, its nouns not RunPod's

**The session talks to a GPU cloud through `gpunit/provider.py::Provider`; RunPod is one implementation of it.**

Its nouns are gpunit's: a card, a pod, a volume, a log, a bill. Breached: `gpunit/lifecycle.py::_delete_pods` compares
HTTP codes (`0015·F3`); `gpunit/lifecycle.py::DEAD` and `gpunit/volume.py::STOCK` are RunPod's words (`0015·F5`).

- **Why:** The contract must not be RunPod's shape by accident, so a second provider is one more implementation.
- **Made by:** `0001·D2`, `0007·D2`, `0010·D1`.

### D3 · RunPod on `urllib`: bounded calls, the key in a header, no redirect, quiet log reads end

**`gpunit/runpod.py::RunPod` calls RunPod's REST v2 over `urllib`: each call bounded, the key in a request header,
no redirect followed, a log read ended once it goes quiet.**

Behaviour: [spec](../openspec/specs/spec/spec.md). The bounds are `gpunit/runpod.py`'s constants.

- **Why:** The key never reaches a subprocess or another host, and a stalled read cannot hold a poll past its
  deadline.
- **Made by:** `0001·D3`, `0002·D4`, `0002·D6`.

### D4 · gpunit's lines: UTC-stamped, to stderr or a sink; `refused:` opens a refusal; a dead pipe swallowed; `sys.exit` in `cli` alone

**`gpunit/log.py` writes each line UTC-stamped to stderr or a sink; a refusal opens with `refused:`; a dead pipe ends
nothing; only `gpunit/cli.py` exits.**

`gpunit/log.py::say` writes through a sink that `session(say=…)` swaps for its life.

- **Why:** One stamped stream says where the minutes go, the tunnel's thread logs too, and a closed pipe must not stop
  a teardown.
- **Made by:** `0001·D12`, `0004·D5`.

## The proof and the process

### D5 · The gate fakes every provider answer; `boot.py` at 100 %

**`make gate` runs offline on faked provider answers, and holds `boot/boot.py` at 100 % line and branch coverage.**

`tests/fakes.py` holds `FakeProvider` and `FakeOpener`; `tests/fixtures/` holds the v2 bodies; every test carries
`@pytest.mark.spec`.

- **Why:** A test that bills cannot be a gate, and `boot.py` runs where no debugger reaches.
- **Made by:** `0001·D13`, `0007·D5`, `0012·D5`, `0012·D6`, `0012·D7`.

### D6 · The metered proofs run by hand, the price first, their tails committed; a boot change rebuilds the images

**Each `make live-*` target rents a real pod or volume, by hand, never in CI; it prints the price first, and its
tail is committed.**

The targets are in `Makefile`, their steps in `live/`. A change to `boot/boot.py` rebuilds and re-pins the images that
carry it before the live runs.

- **Why:** Only a real pod proves the spend rules, the images and RunPod's answers; the fakes cannot.
- **Made by:** `0001·D14`, `0002·D13`, `0008·D4`, `0009·D7`, `0009·D8`, `0010·D10`, `0010·D11`, `0012·D10`,
  `0012·D12`, `0012·D13`, `0014·D12`.

### D7 · An archived change is a record; a card against it closes won't-fix

**A change under `openspec/changes/archive/` is a record: a finding against it is fixed in a new change.**

- **Why:** History is the archive and git; a fix in place would rewrite what was shipped.
- **Made by:** `0002·D12`, `0003·D6`, `0006·D7`, `0009·D6`, `0011·D9`, `0012·D11`, `0013·D12`, `0014·D10`.

### D8 · A patch closes cards; it adds no verb, `gpunit.toml` key or exit code

**A `vX.Y.Z` change fixes what is there; a new verb, key or exit code needs a `vX.Y`.**

- **Why:** A patch is safe to take without reading a new interface.
- **Made by:** `0006·D5`.

### D9 · The threat model lives in `docs/` and moves with every trust-boundary change

**`docs/threat-model.md` is edited by the change that adds a flow, secret, file mode, network call or log line.**

The page is [the threat model](threat-model.md).

- **Why:** It is versioned with the code, so it is current when the code is.
- **Made by:** `0013·D14`.

### D10 · The lifecycle module is `lifecycle.py`

**`up`, `status`, `down` and `ssh` live in `gpunit/lifecycle.py`.**

- **Why:** The package exports the function `session`, which would hide a submodule of that name.
- **Made by:** `0004·D10`.

## The spec and the state

### D11 · `Spec` from `gpunit.toml`: strict keys, a digest, a required ceiling, checked ports

**`gpunit/spec.py::load_spec` refuses an unknown key, an image without a digest, a missing ceiling and a bad port,
before any request.**

Behaviour: [spec](../openspec/specs/spec/spec.md).

- **Why:** A session with no end bills forever, a moving image is not reproducible, and a typo'd port rents a pod for
  a forward that cannot bind.
- **Made by:** `0001·D4`, `0002·D3`.

### D12 · `[env]` passes as written, names no `GPUNIT_*` or `RUNPOD_*`; gpunit's names win

**The spec's `[env]` reaches the pod as written; a `GPUNIT_*` or `RUNPOD_*` name is refused, and gpunit's own names
are set after it.**

`gpunit/contract.py::pod_env` sets the names; `gpunit/spec.py` refuses the reserved ones. Behaviour:
[spec](../openspec/specs/spec/spec.md).

- **Why:** A consumer's `RUNPOD_API_KEY` in `[env]` would put the account key in the pod's env, and a `GPUNIT_*` name
  would forge boot's own.
- **Made by:** `0001·D4`, `0004·D7`, `0013·D2`, `0015·D7`.

### D13 · The window keys, never beside `volume`

**`volume_gb`, `volume_ceiling` and `volume_datacenter` describe the window volume gpunit makes; beside `volume`, an
existing one, they are refused.**

Behaviour: [spec](../openspec/specs/spec/spec.md).

- **Why:** Infra as config: the window lives in the spec, not in flags, and a spec fault is exit `1` before any
  request. `volume` names a volume that exists and the window keys a new one; a session mounts one.
- **Made by:** `0010·D2`.

### D14 · `datacenters` is an allow-list

**`datacenters` names the data centres a pod or volume may be placed in; none set allows any.**

Behaviour: [spec](../openspec/specs/spec/spec.md).

- **Why:** One allow-list holds pods and volumes alike, for data that must stay in a jurisdiction.
- **Made by:** `0013·D7`.

### D15 · `.gpunit/` in the working directory, each record written whole, the directory 0700

**A session's state lives in `.gpunit/` beside the spec, each file replaced whole, the directory `0700`.**

`gpunit/state.py::State` holds `pod`, `pending`, `known_hosts`, `key`, `key.pub`, `volume` and `volume.pending`.

- **Why:** One session per working directory, as isekai's dotfiles; a found directory may carry a loose mode.
- **Made by:** `0001·D5`, `0010·D4`, `0013·D3`.

### D16 · A keypair per session, deleted at teardown

**Each session makes its own SSH keypair in `.gpunit/`, and deletes it with the pod.**

`gpunit/state.py::State.keygen` makes it; `State.clear_session` deletes it.

- **Why:** Nothing long-lived is authorized on a pod.
- **Made by:** `0001·D6`.

### D17 · The ledger: best effort to write, refuses to read; `spend` joins on it

**`gpunit/ledger.py` records each pod's and volume's project under the home directory; a failed write blocks
nothing, and a faulty read refuses.**

`gpunit/ledger.py` writes one JSON line per pod, per volume, and per `deleted`; `gpunit/lifecycle.py::delete_volume`
writes the last.

- **Why:** Billing carries no name: an id learned once is attributable forever, and the ledger must never block a
  session.
- **Made by:** `0007·D1`, `0010·D9`, `0011·D7`, `0015·D6`.

### D18 · `serve`'s state under the home directory, one session per model

**`serve` keeps its state under `~/.local/state/gpunit`, one directory per model, so one session runs per model.**

`gpunit/state.py::home_state` names the root.

- **Why:** `serve` runs from any directory, so its state cannot live in the working one.
- **Made by:** `0005·D2`.

## A session

### D19 · Placement: the catalogue floor, one create per card, a 400 moves on, the rest is `Lost`

**`up` filters `gpus` on the catalogue, tries one create per card in order, moves on after a 400, and treats any
other failure as `Lost`.**

`gpunit/lifecycle.py::placeable` reads the floor; `provider.Unplaceable` is the 400. Behaviour:
[session](../openspec/specs/session/spec.md).

- **Why:** Isekai's placement, proven: a 400 is a refusal of that card, and anything else may have made a pod.
- **Made by:** `0001·D7`, `0015·D5`.

### D20 · Teardown only when a create began here or was lost

**A session tears down only what its own create began, or a create whose outcome it lost.**

- **Why:** The sweep is for a pod this session may have made, never an earlier one.
- **Made by:** `0003·D1`.

### D21 · The wait: a bounded poll; a failed read is not yet; two dead polls end any wait

**Each wait polls to a deadline; a failed read is "not yet", and two dead statuses in a row end it.**

`gpunit/lifecycle.py::DeadPod` is the one rule, read by `up`'s wait and `serve`'s wait and hold.

- **Why:** A restart may show a dead status once, and a failed read says nothing of the pod.
- **Made by:** `0001·D8`, `0006·D2`, `0009·D1`.

### D22 · The host key is proven over the log

**The pod prints its key, with the session's nonce, before its command; the laptop compares it to the scan.**

`gpunit/contract.py::fingerprint` reads the line; `gpunit/hostkey.py::verify` reads the log, scans, compares and
writes `known_hosts`. Behaviour: [session](../openspec/specs/session/spec.md).

- **Why:** A command's output cannot supply the key, and nothing connects first.
- **Made by:** `0001·D8`, `0003·D2`, `0006·D1`, `0009·D3`, `0010·D14`, `0010·R3`, `0011·D8`, `0015·D7`, `0015·D8`.

### D23 · Teardown: a 404 keeps the record; the project's pods are swept

**`down` deletes the recorded pod and sweeps the project's by name and image; a 404 keeps the record.**

`gpunit/provider.py::DELETED` is the success set.

- **Why:** A false "gone" leaves a pod billing, and a wrong key gets a 404 too.
- **Made by:** `0001·D9`, `0002·D5`.

### D24 · gpunit's ssh is its own; the tools checked before any request

**Every `ssh` gpunit runs reads no `ssh_config` and offers the session key alone; `ssh`, `ssh-keygen` and
`ssh-keyscan` are checked before any request.**

`gpunit/lifecycle.py::ssh_command` builds the argv; `gpunit/lifecycle.py::SSH_TOOLS` names the tools.

- **Why:** A `Host *` block brings an agent, a proxy and forwards to a pod on a public IP; a tool missing after the
  create leaves a pod rented.
- **Made by:** `0002·D1`, `0002·D2`.

### D25 · The pod stops at its ceiling and on any end; `down` deletes

**`boot/boot.py` stops the pod at its ceiling and whenever its command ends; `down` deletes it.**

Behaviour: [boot](../openspec/specs/boot/spec.md).

- **Why:** The pod ends itself even when the laptop sleeps or crashes; `down` deletes what is left.
- **Made by:** `0001·D11`.

### D26 · A pod outside `datacenters` is torn down

**A pod RunPod places outside `datacenters` is torn down before anything connects.**

`gpunit/lifecycle.py` reads the pod's data centre during the wait.

- **Why:** RunPod calls the create's data centres *preferred*.
- **Made by:** `0013·D8`, `0013·D9`.

### D27 · `session()` is a context manager over `open_session`; `run` is its first caller

**`gpunit.session` opens a session for a `with` block over `library.open_session`; `gpunit run` is built on it.**

Behaviour: [library](../openspec/specs/library/spec.md).

- **Why:** One implementation: the CLI's specs prove the library, and the tests inject a provider into `open_session`.
- **Made by:** `0001·D10`, `0004·D1`, `0004·D6`, `0015·D4`.

### D28 · One exception per outcome; the provider's `Unplaceable` stays private

**A session raises `Refused`, `Lost`, `TeardownFailed` or `Interrupted`; `provider.Unplaceable` is caught where
the create is made.**

`library.Refused` is `log.Refusal`; `Lost` is `provider.Lost`.

- **Why:** One exception per outcome the CLI already tells apart.
- **Made by:** `0004·D2`, `0015·D5`.

### D29 · Signals raise `Interrupted` once, are ignored during teardown, restored after

**`SIGINT`, `SIGTERM` and `SIGHUP` raise `Interrupted` in the block once; teardown runs with them ignored, and the
handlers are restored after.**

`gpunit/library.py::_Signals` installs and restores them; a session opens on the main thread.

- **Why:** A library must keep `run`'s signal rules, and `KeyboardInterrupt` alone names no signal.
- **Made by:** `0004·D3`.

### D30 · The tunnel: a watched `ssh -N -L`, a backoff, one forward per loopback family

**The session forwards its ports over a watched `ssh -N -L`, reopened with a backoff, one forward per loopback
family.**

`gpunit/library.py::_Tunnel` is the watched child. Behaviour: [library](../openspec/specs/library/spec.md).

- **Why:** There is no main loop to poll from, a tunnel that cannot bind would flood stderr, and OpenSSH counts a
  forward set up when either family binds.
- **Made by:** `0002·D8`, `0004·D4`, `0013·D5`, `0013·S1`, `0013·S6`.

### D31 · A taken local port refuses, from any thread, unlatched

**A local port another process takes ends the block with `Refused`, raised in the main thread; a block that swallows
it still ends on a signal.**

`gpunit/library.py::_Signals.refuse` raises it through the session's signal handler.

- **Why:** A reopen would send the traffic, and the vLLM key, to a squatter; a thread cannot raise in the main one.
- **Made by:** `0013·D5`, `0013·D6`, `0013·S2`.

### D32 · Exit codes: `0`, `1`, `2`, `3`, `128+n`

**`gpunit` exits `0` on success, `1` on a refusal or a failed teardown, `2` on a usage error, `3` on a lost create,
and `128+n` on signal `n`.**

`gpunit/cli.py::_run` and `gpunit/run.py::outcome` map outcomes to codes. Behaviour:
[cli](../openspec/specs/cli/spec.md). Breached: `gpunit/volume.py::_agree` exits `1` on Ctrl-C at the price
(`0015·F20`).

- **Why:** A shell or an agent tells a refusal from a lost create by the code alone.
- **Made by:** `0001·D10`, `0002·D7`, `0004·D6`, `0006·D3`.

### D33 · `run`'s command gets the host, the ports and `GPUNIT_SSH`, never the account key

**`gpunit run` hands its command the pod's address, the local ports and an `ssh` line, and strips the account key
from its environment.**

`gpunit/run.py` sets `GPUNIT_HOST`, `GPUNIT_SSH` and a `GPUNIT_PORT_<remote>` per port.

- **Why:** The command never needs the account key.
- **Made by:** `0001·D10`, `0004·D6`, `0013·D1`.

## Serve

### D34 · A model is a row: the bundled table and one user file

**`gpunit serve <model>` reads a row from `gpunit/serve/models.toml` or the operator's one user file; a user row of
a bundled name replaces it.**

`gpunit/serve/table.py::rows` reads both; the user file is `--models`, else `GPUNIT_MODELS`, else the XDG default.
Behaviour: [serve](../openspec/specs/serve/spec.md).

- **Why:** A model is a row and its spec is built, never written; a file outside every repo needs no gitignore.
- **Made by:** `0005·D1`, `0008·D1`, `0008·D2`, `0014·D1`, `0014·D2`, `0014·D3`, `0014·D5`, `0014·D7`, `0014·S2`.

### D35 · The price first, `y/N`; `--yes` skips it

**`serve` and `volume up` print the most the rent can cost and ask `y/N`; `--yes` answers for a script.**

- **Why:** A person rents by hand at cost, and a script must still be able to.
- **Made by:** `0005·D3`.

### D36 · `serve`'s wait polls `/v1/models`; the local port is picked before the price

**`serve` picks a free local port before the price, and waits on `/v1/models` over the tunnel.**

`gpunit/serve/session.py` holds the poll's bounds.

- **Why:** vLLM pulls, downloads and loads before it answers, and the local port is known before anything is rented.
- **Made by:** `0005·D4`, `0006·D3`.

### D37 · The chat: streamed, in memory, cleaned on screen

**The chat streams each reply, keeps the history in memory, not on disk, and cleans what it prints.**

`gpunit/serve/chat.py` holds it.

- **Why:** Stdlib only, and a model's output must not steer the terminal.
- **Made by:** `0005·D5`, `0006·D3`, `0014·D9`, `0014·S4`.

### D38 · `--api`: a fresh key, the URL and key on stdout, a hold

**`serve --api` draws a fresh key, prints the URL and key on stdout, and holds the session until it is ended.**

- **Why:** The key keeps the loopback port the session's.
- **Made by:** `0005·D6`.

### D39 · `pod.log` holds the log since the create; printed lines are cleaned

**`serve` keeps the pod's log since its create in `pod.log`, and cleans each line it prints.**

`gpunit/log.py::clean` cleans; `pod.log` stays as read.

- **Why:** The log is gone once the pod stops, and a command's output can carry terminal escapes.
- **Made by:** `0009·D2`, `0013·D4`.

### D40 · The serve image: vLLM by digest; the launcher turns logging and telemetry off

**`serve/Dockerfile` builds on vLLM by digest; `serve/launch.py` turns request logging and telemetry off, then
starts vLLM.**

`gpunit/serve/models.toml` pins the image. Breached: `gpunit/serve/table.py::_args` refuses `--enable-log-requests` by
its exact name, while vLLM takes abbreviations (`0015·F23`).

- **Why:** One image serves every row; only gpunit's launcher sees every row, so it holds the quiet flags.
- **Made by:** `0005·D7`, `0012·D9`, `0014·D4`, `0014·D6`.

## The window volume

### D41 · `volume up` and `down`; the sweep asks a person at a terminal

**`gpunit volume up` makes or extends the window volume, `volume down` deletes it; a volume of its name in no
record is deleted only on a person's `y`.**

`gpunit/volume.py` holds both verbs. Behaviour: [volume](../openspec/specs/volume/spec.md).

- **Why:** The pod's lifecycle, for a volume; no script or agent may confirm deleting a volume no record names.
- **Made by:** `0010·D5`, `0010·S1`, `0010·S2`, `0010·R1`, `0011·D1`, `0011·D4`, `0011·D5`.

### D42 · The window's data centre

**`volume_datacenter` names the window's data centre; without it, `volume up` picks one that stocks a card in
`gpus`.**

`gpunit/volume.py` picks the highest stock of the first placeable card, among standard-volume data centres in
`datacenters`.

- **Why:** Every pod of the window goes where its volume is.
- **Made by:** `0010·D3`.

### D43 · Every session mounts the window; the sweep runs first

**Every session mounts the recorded window volume, and every verb first deletes a window past its end.**

`gpunit/lifecycle.py::sweep_window` runs first in `up`, `status`, `serve` and `volume`, and in `down` after its pods.

- **Why:** A forgotten volume ends at the next command, with no chore to remember.
- **Made by:** `0010·D6`, `0010·D7`, `0010·D8`, `0010·R2`, `0011·D2`, `0011·D3`.

## Spend

### D44 · `spend`: whole UTC days, the provider's amounts, one rounding

**`gpunit spend` totals the provider's billing over whole UTC days, by project through the ledger, rounded once.**

`gpunit/spend.py` holds the window, the join and the render. Behaviour: [spend](../openspec/specs/spend/spec.md).

- **Why:** A table of zeros would read as a free week; the amount charged is the provider's, not price × seconds.
- **Made by:** `0007·D3`, `0007·D4`.

## The pod's boot

### D45 · `boot.py`: one stdlib file for Python 3.10, no gpunit import

**`boot/boot.py` is one file on Python 3.10's standard library, one function a step, importing nothing of gpunit.**

Behaviour: [boot](../openspec/specs/boot/spec.md).

- **Why:** Ubuntu 22.04 ships 3.10, a consumer `ADD`s one file, and each step is tested alone.
- **Made by:** `0012·D1`, `0012·D2`, `0012·D8`.

### D46 · The ceiling in a forked watchdog; the stop in a `finally`, retried

**A forked watchdog stops the pod at its ceiling; the main flow stops it in a `finally`, retrying the call.**

`boot/boot.py` holds `GRACE_S`, the wait before the stop.

- **Why:** A separate process outlives a crash in the main one, and an outage still gets its stop.
- **Made by:** `0001·D11`, `0003·D4`, `0009·D4`, `0012·D1`, `0012·D3`.

### D47 · Boot's stop over `urllib`; the command's env without the key and the nonce

**`boot.py` stops the pod over `urllib`, and runs the command without `RUNPOD_API_KEY` and `GPUNIT_NONCE`.**

- **Why:** The stop key is boot's, not the command's, and the nonce in the command's hands would let it forge the key
  line.
- **Made by:** `0003·D3`, `0012·D4`.

### D48 · sshd on boot's own config and a fresh host key

**`boot.py` starts sshd on a config of its own, with a host key it makes at boot.**

- **Why:** A `!`-locked root logs in by key with `UsePAM yes`, and the key made at boot is the one boot prints.
- **Made by:** `0001·D11`, `0002·D9`.

## The guide

### D49 · The layers, held by `tests/test_layers.py`

**A module imports its own layer, without a cycle, and the layers below; `tests/test_layers.py` holds it.**

`tests/test_layers.py::LAYERS` is the table, and each rule is a function beside it.

- **Why:** The guide states a rule only a test keeps.
- **Made by:** `0015·D9`.

### D50 · The guide: why, flow and where, never a value; symbols and decision ids cited, held by `tests/test_docs.py`

**`docs/` says why, how data flows and where to change it; it cites symbols and decision ids, and
`tests/test_docs.py` holds them.**

Each page links the spec for behaviour and names the file for a value.

- **Why:** A doc that restates a value drifts from it; docs a test holds stay true.
- **Made by:** `0015·D10`, `0015·D11`, `0015·D14`.

### D51 · A refactor changes no scenario, message or exit code

**A change that moves or renames code leaves every spec scenario, message and exit code as it was; tests change in
names and imports alone.**

- **Why:** The unchanged tests prove nothing moved.
- **Made by:** `0015·D1`.
