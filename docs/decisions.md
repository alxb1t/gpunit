# Decisions in force

The choices gpunit is built on, each with why and the archived decisions that made it. **A change that makes or
overturns a decision edits this page**; its own `design.md` keeps the history. Code cites a decision as
`decision Dn`; an overturned one is not listed, and the archive keeps it.

Each decision states the choice and why. Behaviour is the spec's: a decision links it. A value is its file's: a
decision names the file.

## The package

### D1 · A flat stdlib package, Python 3.11, no runtime dependency

**`gpunit/` is one flat package on the standard library, for Python 3.11 and later; `dependencies = []`.**

### D2 · A `Provider` protocol, its nouns not RunPod's

**The session talks to a GPU cloud through `gpunit/provider.py::Provider`; RunPod is one implementation of it.**

### D3 · RunPod on `urllib`: bounded calls, the key in a header, no redirect, quiet log reads end

**`gpunit/runpod.py::RunPod` calls RunPod's REST v2 over `urllib`: each call bounded, the key in a request header,
no redirect followed, a log read ended once it goes quiet.**

### D4 · gpunit's lines: UTC-stamped, to stderr or a sink; `refused:` opens a refusal; a dead pipe swallowed; `sys.exit` in `cli` alone

**`gpunit/log.py` writes each line UTC-stamped to stderr or a sink; a refusal opens with `refused:`; a dead pipe ends
nothing; only `gpunit/cli.py` exits.**

## The proof and the process

### D5 · The gate fakes every provider answer; `boot.py` at 100 %

**`make gate` runs offline on faked provider answers, and holds `boot/boot.py` at 100 % line and branch coverage.**

### D6 · The metered proofs run by hand, the price first, their tails committed; a boot change rebuilds the images

**Each `make live-*` target rents a real pod or volume, by hand, never in CI; it prints the price first, and its
tail is committed.**

### D7 · An archived change is a record; a card against it closes won't-fix

**A change under `openspec/changes/archive/` is a record: a finding against it is fixed in a new change.**

### D8 · A patch closes cards; it adds no verb, `gpunit.toml` key or exit code

**A `vX.Y.Z` change fixes what is there; a new verb, key or exit code needs a `vX.Y`.**

### D9 · The threat model lives in `docs/` and moves with every trust-boundary change

**`docs/threat-model.md` is edited by the change that adds a flow, secret, file mode, network call or log line.**

### D10 · The lifecycle module is `lifecycle.py`

**`up`, `status`, `down` and `ssh` live in `gpunit/lifecycle.py`.**

## The spec and the state

### D11 · `Spec` from `gpunit.toml`: strict keys, a digest, a required ceiling, checked ports

**`gpunit/spec.py::load_spec` refuses an unknown key, an image without a digest, a missing ceiling and a bad port,
before any request.**

### D12 · `[env]` passes as written, names no `GPUNIT_*` or `RUNPOD_*`; gpunit's names win

**The spec's `[env]` reaches the pod as written; a `GPUNIT_*` or `RUNPOD_*` name is refused, and gpunit's own names
are set after it.**

### D13 · The window keys, never beside `volume`

**`volume_gb`, `volume_ceiling` and `volume_datacenter` describe the window volume gpunit makes; beside `volume`, an
existing one, they are refused.**

### D14 · `datacenters` is an allow-list

**`datacenters` names the data centres a pod or volume may be placed in; none set allows any.**

### D15 · `.gpunit/` in the working directory, each record written whole, the directory 0700

**A session's state lives in `.gpunit/` beside the spec, each file replaced whole, the directory `0700`.**

### D16 · A keypair per session, deleted at teardown

**Each session makes its own SSH keypair in `.gpunit/`, and deletes it with the pod.**

### D17 · The ledger: best effort to write, refuses to read; `spend` joins on it

**`gpunit/ledger.py` records each pod's and volume's project under the home directory; a failed write blocks
nothing, and a faulty read refuses.**

### D18 · `serve`'s state under the home directory, one session per model

**`serve` keeps its state under `~/.local/state/gpunit`, one directory per model, so one session runs per model.**

## A session

### D19 · Placement: the catalogue floor, one create per card, a 400 moves on, the rest is `Lost`

**`up` filters `gpus` on the catalogue, tries one create per card in order, moves on after a 400, and treats any
other failure as `Lost`.**

### D20 · Teardown only when a create began here or was lost

**A session tears down only what its own create began, or a create whose outcome it lost.**

### D21 · The wait: a bounded poll; a failed read is not yet; two dead polls end any wait

**Each wait polls to a deadline; a failed read is "not yet", and two dead statuses in a row end it.**

### D22 · The host key is proven over the log

**The pod prints its key, with the session's nonce, before its command; the laptop compares it to the scan.**

### D23 · Teardown: a 404 keeps the record; the project's pods are swept

**`down` deletes the recorded pod and sweeps the project's by name and image; a 404 keeps the record.**

### D24 · gpunit's ssh is its own; the tools checked before any request

**Every `ssh` gpunit runs reads no `ssh_config` and offers the session key alone; `ssh`, `ssh-keygen` and
`ssh-keyscan` are checked before any request.**

### D25 · The pod stops at its ceiling and on any end; `down` deletes

**`boot/boot.py` stops the pod at its ceiling and whenever its command ends; `down` deletes it.**

### D26 · A pod outside `datacenters` is torn down

**A pod RunPod places outside `datacenters` is torn down before anything connects.**

### D27 · `session()` is a context manager over `open_session`; `run` is its first caller

**`gpunit.session` opens a session for a `with` block over `library.open_session`; `gpunit run` is built on it.**

### D28 · One exception per outcome; the provider's `Unplaceable` stays private

**A session raises `Refused`, `Lost`, `TeardownFailed` or `Interrupted`; `provider.Unplaceable` is caught where
the create is made.**

### D29 · Signals raise `Interrupted` once, are ignored during teardown, restored after

**`SIGINT`, `SIGTERM` and `SIGHUP` raise `Interrupted` in the block once; teardown runs with them ignored, and the
handlers are restored after.**

### D30 · The tunnel: a watched `ssh -N -L`, a backoff, one forward per loopback family

**The session forwards its ports over a watched `ssh -N -L`, reopened with a backoff, one forward per loopback
family.**

### D31 · A taken local port refuses, from any thread, unlatched

**A local port another process takes ends the block with `Refused`, raised in the main thread; a block that swallows
it still ends on a signal.**

### D32 · Exit codes: `0`, `1`, `2`, `3`, `128+n`

**`gpunit` exits `0` on success, `1` on a refusal or a failed teardown, `2` on a usage error, `3` on a lost create,
and `128+n` on signal `n`.**

### D33 · `run`'s command gets the host, the ports and `GPUNIT_SSH`, never the account key

**`gpunit run` hands its command the pod's address, the local ports and an `ssh` line, and strips the account key
from its environment.**

## Serve

### D34 · A model is a row: the bundled table and one user file

**`gpunit serve <model>` reads a row from `gpunit/serve/models.toml` or the operator's one user file; a user row of
a bundled name replaces it.**

### D35 · The price first, `y/N`; `--yes` skips it

**`serve` and `volume up` print the most the rent can cost and ask `y/N`; `--yes` answers for a script.**

### D36 · `serve`'s wait polls `/v1/models`; the local port is picked before the price

**`serve` picks a free local port before the price, and waits on `/v1/models` over the tunnel.**

### D37 · The chat: streamed, in memory, cleaned on screen

**The chat streams each reply, keeps the history in memory, not on disk, and cleans what it prints.**

### D38 · `--api`: a fresh key, the URL and key on stdout, a hold

**`serve --api` draws a fresh key, prints the URL and key on stdout, and holds the session until it is ended.**

### D39 · `pod.log` holds the log since the create; printed lines are cleaned

**`serve` keeps the pod's log since its create in `pod.log`, and cleans each line it prints.**

### D40 · The serve image: vLLM by digest; the launcher turns logging and telemetry off

**`serve/Dockerfile` builds on vLLM by digest; `serve/launch.py` turns request logging and telemetry off, then
starts vLLM.**

## The window volume

### D41 · `volume up` and `down`; the sweep asks a person at a terminal

**`gpunit volume up` makes or extends the window volume, `volume down` deletes it; a volume of its name in no
record is deleted only on a person's `y`.**

### D42 · The window's data centre

**`volume_datacenter` names the window's data centre; without it, `volume up` picks one that stocks a card in
`gpus`.**

### D43 · Every session mounts the window; the sweep runs first

**Every session mounts the recorded window volume, and every verb first deletes a window past its end.**

## Spend

### D44 · `spend`: whole UTC days, the provider's amounts, one rounding

**`gpunit spend` totals the provider's billing over whole UTC days, by project through the ledger, rounded once.**

## The pod's boot

### D45 · `boot.py`: one stdlib file for Python 3.10, no gpunit import

**`boot/boot.py` is one file on Python 3.10's standard library, one function a step, importing nothing of gpunit.**

### D46 · The ceiling in a forked watchdog; the stop in a `finally`, retried

**A forked watchdog stops the pod at its ceiling; the main flow stops it in a `finally`, retrying the call.**

### D47 · Boot's stop over `urllib`; the command's env without the key and the nonce

**`boot.py` stops the pod over `urllib`, and runs the command without `RUNPOD_API_KEY` and `GPUNIT_NONCE`.**

### D48 · sshd on boot's own config and a fresh host key

**`boot.py` starts sshd on a config of its own, with a host key it makes at boot.**

## The guide

### D49 · The layers, held by `tests/test_layers.py`

**A module imports its own layer, without a cycle, and the layers below; `tests/test_layers.py` holds it.**

### D50 · The guide: why, flow and where, never a value; symbols and decision ids cited, held by `tests/test_docs.py`

**`docs/` says why, how data flows and where to change it; it cites symbols and decision ids, and
`tests/test_docs.py` holds them.**

### D51 · A refactor changes no scenario, message or exit code

**A change that moves or renames code leaves every spec scenario, message and exit code as it was; tests change in
names and imports alone.**
