# Design — 0006 paydown

How each card closes: a stricter host-key rule, a wait that reads the pod's status, four `serve` fixes, the text that
fell behind, and a live proof of the dead path. **Verdict: feasible** — each fix is local to the file its card names,
re-checked at HEAD.

## Context

See [proposal](proposal.md) — *Why*. What holds at the cut, `main` at `fb683e2` (`v0.3.0`):

- **`fingerprint`** keeps the last `gpunit host key:` line of the lines it is given (`gpunit/provider.py:25-32`);
  `_verify_host_key`'s `read` calls it on the log's tail, then on the log since the create
  (`gpunit/lifecycle.py:284-290`). `LOG_WAIT_S` is 60.
- **Boot prints** the key line on stdout (`boot/boot.sh:88`), then `say "step: the command"` — `<UTC> step: the command`
  on stderr (`:92-93`) — before it starts the command. The pod's log API carries both streams.
- **`_wait`** polls `provider.get` every `POLL_S` (5) until host and port are mapped, for `spec.timeout_s`
  (`gpunit/lifecycle.py:262-278`); `PodInfo.status` is read from v2's `status`
  (`gpunit/provider.py:52-57`, `gpunit/runpod.py:151-164`): `PROVISIONING`, `STARTING`, `RUNNING`, `EXITED`,
  `ERROR`, `TERMINATED`. `_tear_down` says the reason, runs `down`, and refuses with it
  (`gpunit/lifecycle.py`, the last function).
- **`chat.run`**'s request block catches `OSError`, `HTTPException` and `ValueError` together and `continue`s
  (`gpunit/serve/chat.py:61-67`); `urllib.error.HTTPError` is an `OSError`.
- **`serve`:** `Row.spec` forwards `Port(remote=PORT, local=PORT)` (`gpunit/serve/table.py:60`); `serve` builds the spec
  then `_agree` (`gpunit/serve/session.py:52-57`), and `library._open` refuses a busy local port only after that
  (`gpunit/library.py:90`, `:265-274`); `_agree`'s `ask` is at `:108`; `down` builds a spec with `.spec(0, None, None, "")`
  (`:75`). `outcome` handles `Refusal`, `Lost`, `TeardownFailed`, `Interrupted` (`gpunit/run.py:33-45`).
- **The row** `qwen3-4b` lists `NVIDIA RTX A5000`, `NVIDIA RTX A4500`, `NVIDIA GeForce RTX 4090` with `vram_gb = 24`
  (`gpunit/serve/models.toml:10-11`); the A4500 has 20 GB.
- **Text:** README step 3 (`README.md:51-54`) and the step-5 comment in `boot/boot.sh:92` say the command never sees
  the key; README's serve diagram says the ceiling ends a session (`:120`); `gpunit/state.py:1` says the working
  directory; the `live-serve` comment says 30m (`Makefile:24`), README `:209`, `:212`, and `live/price.py:13-15` omit
  the SSH wait; the cli spec's exit codes omit `128 + n` (`openspec/specs/cli/spec.md:24-28`).
- **`CLAUDE.md`** states no patch rule (its *Invariants* are at `:38-44`).
- **The tests that turn red** with these changes: `tests/fakes.py` (`KEY_LINE`), `tests/test_hostkey.py`,
  `tests/test_runpod.py` (the `fingerprint` tests), `tests/test_library.py` (`:280`), `tests/test_up.py` (`:225`),
  `tests/test_serve_session.py` (`:173`), `tests/test_serve_table.py` (`:72`).

## Goals / Non-Goals

**Goals:** each card closed by the fix its text names, or closed moot; the dead path proven on a real pod.

**Non-Goals:** a new verb, key or exit code; a change to the `Provider` seam; a fix for a command that prints both
lines.

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| [D1](#d1) | `fingerprint` accepts a key line only when a `<UTC> step: the command` line follows it | the command starts after that line | the first key line (a restart would tear down) |
| [D2](#d2) | `_wait` tears down on two terminal polls in a row; fail open | a restart may show `EXITED` once; a failed read is not yet | one poll; reading `desiredStatus` |
| [D3](#d3) | the four `serve` fixes | the cards' own fixes | a bind address for the port |
| [D4](#d4) | the stale text corrected where it lives | a rule says what the code does | editing archived changes |
| [D5](#d5) | `CLAUDE.md` states the patch rule | three patches now ride on it | leaving it to a grilling |
| [D6](#d6) | `make live-dead`: the live image without `curl`, its own spec | it shows what the provider reports for a dead boot | trusting the documented statuses |
| [D7](#d7) | five cards close moot | an archived change is a record | rewriting it |

### D1

`provider.py` gains `_BOOT_STEP = re.compile(r"^\S+ step: the command\s*$")`. `fingerprint(lines)` walks the lines: a
key line sets `pending`; a step line moves `pending` to `accepted` and clears it; the result is `accepted`. A key line
no step follows is never accepted, and a later boot's key replaces `pending`. The read in `_verify_host_key` is
unchanged: it already asks the tail, then the log since the create. The residual risk — a command that prints the key
line and then a step line itself — is named in the proposal; a command that can do so is trusted with the key by
README already.

```
key1 · step · … command output … · key2 · step     ─▶ key2
key1 · step · forged key                           ─▶ key1
key1 (no step yet)                                 ─▶ none; the poll goes on
```

### D2

`_wait`'s `mapped()` keeps `dead = 0`. A poll answering `EXITED`, `ERROR` or `TERMINATED` adds one; any other answer,
including `None`, resets it to zero; at two it calls `_tear_down(spec, provider, state, f"pod {id} is {status}: the
container is not running")`. A poll that maps host and port returns as before. The raise ends `_poll`, so no further
poll is made. `DEAD = ("EXITED", "ERROR", "TERMINATED")` is a constant in `lifecycle.py`.

### D3

- **`0005·R2`:** in `chat.run`, a `urllib.error.HTTPError` (the server answered) and `ValueError` and `HTTPException`
  keep dropping the turn; any other `OSError` — refused, reset, timed out — calls `log.refuse("the server stopped
  answering; the pod's ceiling may have ended it")`, which ends the chat and closes the session.
- **`0005·R6`:** `serve` asks the OS for a free local port (`socket.bind(("127.0.0.1", 0))`) before building the spec;
  `Row.spec(ceiling_s, volume, max_hourly, key, local_port)` forwards remote `PORT` to it; `down` passes `PORT`.
- **`0005·R7`:** `_agree` catches `KeyboardInterrupt` around `ask`, writes a newline, says `not rented` and re-raises;
  `outcome` gains `except KeyboardInterrupt: return 130` after `Interrupted`.
- **`0005·R5`:** the row's cards become `NVIDIA RTX A5000`, `NVIDIA GeForce RTX 4090`, `NVIDIA L4`, each 24 GB.

### D4

- `0003·R2`: README step 3 and `boot/boot.sh`'s step-5 comment say what v0.1.2's CHANGELOG says: the command does not
  inherit the key, and a root command can still read it from boot's `/proc`.
- `0005·R2` (text): README's serve diagram ends "down: `/exit`, end of input, Ctrl-C; the chat ends if the server stops
  answering".
- `0005·R3`: the cli spec's exit codes gain `128 + n` (the delta).
- `0005·R4`: `gpunit/state.py`'s docstring says the directory it is given.
- `0005·R10`: the `live-serve` comment and README say `30m` plus the SSH wait; `live/price.py` takes an optional spec
  path and counts `ceiling + timeout`.

### D5

`CLAUDE.md` gains under *Invariants*: **A patch closes cards and fixes; it adds no verb, `gpunit.toml` key or exit
code.**

### D6

`live/Dockerfile.dead` is `live/Dockerfile` without `curl`: `boot.sh` refuses at once, and the container exits.
`live/gpunit.dead.toml` names its digest (a placeholder of `0` × 64 until it is built), `ceiling = "5m"`,
`timeout = 120`. `make live-dead` prints the price (`live/price.py live/gpunit.dead.toml`), runs `gpunit up --spec
live/gpunit.dead.toml` expecting exit `1`, prints the elapsed seconds, then `gpunit status`. Whatever status the
provider reports — `EXITED`, or a flap that never shows two in a row — is written to `live/last_run.txt`. If the abort
does not fire, the session ends at `timeout`, still torn down, and the task does not close: the plan, not the rule, is
what to revisit.

### D7

`0003·R3`, `R4`, `R5` and `0005·R8`, `R9` name `0003-consumer-fit`'s and `0005-serve`'s design and tasks, both
archived. They are listed under `backlog:` and no task touches them.

## Dependencies

None.

## Risks / Trade-offs

- **A command that prints both the key line and the step line** → not caught; the command is already trusted with the
  key.
- **The provider reports `EXITED` once for a restart** → two polls in a row are required.
- **`boot.sh`'s sha256 changes with its comment** → an image pinned by checksum at an older tag is unaffected; a
  consumer moving to `v0.3.1` updates its checksum as it does for any tag.
- **The live-dead pod flaps and never reads `EXITED` twice** → the session ends at `timeout`, torn down; the abort
  stays fail-open, and the proof says so.

## Verdict

Feasible: each fix is a few lines in the file its card names, each with a test, and the one unknown — what the
provider reports for a dead boot — is read on a real pod before release.
