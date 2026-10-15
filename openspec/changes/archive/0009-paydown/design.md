# Design — 0009 paydown

How each fix lands: a dead-pod rule shared by every wait, a log kept while the pod lives, a nonce in the host-key
line, a grace before boot's stop, the drift corrected, and a live proof of a crash. **Verdict: feasible** — each fix is
local to the file it names, re-checked at HEAD.

## Context

See [proposal](proposal.md) — *Why*. What holds at the cut, `main` at `96ef901` (`v0.5.0`):

- **`up`'s wait** keeps the dead-pod rule inline: `_wait`'s `mapped()` tears down on two polls in a row reading
  `DEAD = ("EXITED", "ERROR", "TERMINATED")` (`gpunit/lifecycle.py:29`, `:272-288`); a failed read (`None`) resets it.
- **`serve`'s wait** (`gpunit/serve/session.py:137-157`) loops on `_answers` and `WAIT_S` only, polling every
  `POLL_S` (5); every `PROGRESS_S` (30) it reads `provider.log(pod_id, tail=LOG_TAIL)` and prints the last line.
  **The hold** (`:159-172`) polls every `HOLD_S` (30) and refuses after `QUIET_S` (60) without an answer. A refusal in
  either raises out of `library._open`'s block, whose `finally` tears the pod down (`gpunit/library.py:119-136`).
- **`serve`'s body** opens on `State(home(name))` (`gpunit/serve/session.py:58-62`); the `Record` it holds carries
  `created`, the UTC time of the create (`gpunit/lifecycle.py:78-84`).
- **`provider.log`** with `since` sends `since` and no `tail`; a read ends after `LOG_IDLE_S` (3) of quiet or
  `LOG_READ_S` (10) in all (`gpunit/runpod.py:34-35`, `:168-188`).
- **The host key:** `_HOST_KEY` and `_BOOT_STEP` (`gpunit/provider.py:10-12`); `fingerprint(lines)` keeps the last
  key line a step line follows (`:27-39`). `_verify_host_key` reads the tail, then the log since the create
  (`gpunit/lifecycle.py:303-316`). `Provider.create(spec, gpu, pubkey, ceiling_s)` (`gpunit/provider.py:112`), and
  `RunPod.create` builds the pod's `env` from `spec.env`, `PUBLIC_KEY` and `GPUNIT_CEILING`
  (`gpunit/runpod.py:118`). `lifecycle._create` calls it (`gpunit/lifecycle.py:247-266`).
- **`boot.sh`:** the required variables (`boot/boot.sh:45-47`), `trap stop EXIT` (`:59`), the key line on stdout
  (`:89`), `step: the command` (`:94`), `env -u RUNPOD_API_KEY "$@"` (`:95`), `the command exited $code` (`:105`),
  `exit "$code"` (`:106`).
- **`boot.sh` is in the serve and live images:** `serve/Dockerfile:9` (`gpunit-vllm`, pinned at `gpunit/serve/models.toml:2`,
  built by `.github/workflows/build-serve-image.yml`), and `live/Dockerfile` and `live/Dockerfile.dead`
  (`gpunit-live` and `gpunit-live-dead`, pinned at `live/gpunit.toml:4` and `live/gpunit.dead.toml:4`).
- **The drift:** `README.md:223` reads "`spend --days` under 1"; `tests/test_spend.py:156` tags the ledger test
  `spend:report:unreadable-billing-fails`; `spend`'s docstring says "when the billing cannot be read"
  (`gpunit/spend.py:61`); `ledger.read` refuses with `the ledger could not be read` (`gpunit/ledger.py:53`).
- **The tests that turn red:** `tests/fakes.py` (`KEY_LINE`, `FakeProvider.create`), `tests/fixtures/log.txt`,
  `tests/test_runpod.py` (the `create` calls, `:76-237`; the `fingerprint` tests, `:174-205`),
  `tests/test_hostkey.py`, `tests/test_boot.py` (the waits at `:256` and `:273`; the key line at `:277-310`),
  `tests/test_serve_session.py` (`test_a_model_that_never_answers_is_refused_and_torn_down`, `:177-192`, which reads
  the progress line from a `tail` read).

## Goals / Non-Goals

**Goals:** no wait outlives its pod; the last lines a crashed command wrote reach the laptop; a key line an echo
supplies is never the key; each card closed.

**Non-Goals:** a new verb, `gpunit.toml` key or exit code; ending a wait on a log line; a status check in
`gpunit run`'s command phase.

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| [D1](#d1) | one `DeadPod` rule in `lifecycle.py`, used by `up`'s wait, `serve`'s wait and its hold | one rule for a dead pod, wherever gpunit waits | a second copy in `serve` |
| [D2](#d2) | `pod.log`: the log since the create, re-read every 30 s, replaced only by a read as long | the log is gone once the pod stops | reading the log after `EXITED`; appending tail reads |
| [D3](#d3) | a per-pod nonce in `GPUNIT_NONCE`, printed in the key line, kept from the command; strict | an echo cannot know it | a warning for an old line; dropping the step line |
| [D4](#d4) | `boot.sh` sleeps 60 s after the command exits, before the stop | gpunit reads the log every 30 s | ending the wait on `the command exited` |
| [D5](#d5) | the drift fixed where it lives | a doc says what the code does | — |
| [D6](#d6) | `0008·R5` and `0007·R6`'s design half close won't-fix | archived text is a record | editing the archive |
| [D7](#d7) | `make live-serve-dead`: `qwen3-4b` with an argument vLLM refuses, by the Python API | the crash, reproduced without a row | a row in the table; killing vLLM over SSH |
| [D8](#d8) | `gpunit-vllm`, `gpunit-live` and `gpunit-live-dead` rebuilt, their digests pinned, before the live runs | `boot.sh` is in each | a run on the old images |

### D1

`lifecycle.py` gains `DeadPod`, the rule `_wait` keeps inline today:

```python
class DeadPod:
    """Two polls in a row reading a dead status; a failed read is not yet."""

    def __init__(self) -> None:
        self._last = False

    def seen(self, info: PodInfo | None) -> bool:
        dead = info is not None and info.status in DEAD
        twice, self._last = dead and self._last, dead
        return twice
```

`up`'s `mapped()` calls `seen(info)` and tears down as before; its line and its scenarios do not change. `serve`'s
`_wait` and `_hold` call `provider.get(pod_id)` once per poll and `seen` on the answer; on `True` they print the kept
log ([D2](#d2)) and `log.refuse("the pod stopped while the model loaded")` or `log.refuse("the pod stopped while
serving")`. The refusal leaves `library._open`'s block, which tears the pod down. A read returns `None` on any fault,
so the rule fails open.

```
poll:  RUNNING · EXITED · RUNNING · EXITED · EXITED
seen:  no      · no     · no      · no     · yes  ─▶ refuse, tear down
```

### D2

`serve`'s body removes `home(name) / "pod.log"` once the session is open, after `up`'s guards, or once `up` refuses
after its create began, so only a run refused before its create keeps the last session's file; it reads `created` from `State(home(name)).read()` then too. A `_Kept` holder in `gpunit/serve/session.py` keeps the path and the line count:

- **`take(lines)`** writes `lines` to `pod.log` when they are at least as many as it holds, opening it with
  `os.open(path, O_WRONLY | O_CREAT | O_TRUNC, 0o600)`; a shorter or empty read changes nothing.
- **`tail(n)`** returns the file's last `n` lines.

`_wait`'s progress tick becomes `lines = provider.log(pod_id, tail=LOG_TAIL, since=created)`, then `take(lines)`, then
the `loading:` line from `lines[-1]` as today. `_hold` does the same on each of its polls. Before a dead-pod refusal, and the hold's quiet one,
each of `tail(30)` is said as `pod: <line>`, then `the pod's log is kept at <path>`. `KEEP_TAIL = 30`.

A since-read holds the whole log since the create, so the newest read is the fullest; a read cut by `LOG_READ_S` is
shorter, and `take` keeps the longer one. The file is per model, like the session's `.gpunit/`.

### D3

- **gpunit:** `lifecycle.NONCE` is a `Callable[[], str]`, `lambda: secrets.token_hex(16)`; the tests replace it, as
  they replace `CLOCK`. `up` draws one before `_create`, and `Provider.create` gains a keyword `nonce: str`, which
  `RunPod.create` puts in the pod's `env` as `GPUNIT_NONCE`.
- **`boot.sh`:** `GPUNIT_NONCE` is required once the ceiling and `trap stop EXIT` are armed, so its refusal stops
  the pod an older gpunit made; the key line becomes
  `echo "gpunit host key $GPUNIT_NONCE: <fingerprint>"`; the command runs as
  `env -u RUNPOD_API_KEY -u GPUNIT_NONCE "$@" &`.
- **`fingerprint(lines, nonce)`:** `_HOST_KEY` becomes `^gpunit host key ([0-9a-f]{32}): (SHA256:[A-Za-z0-9+/]+)\s*$`;
  a key line counts only when its nonce equals `nonce`, and the step line still accepts it, as `0006` D1 settled.
- **An older `boot.sh`:** `old_boot(lines)` in `provider.py` is true when a line matching
  `^gpunit host key: SHA256:[A-Za-z0-9+/]+\s*$` has a step line after it. `_verify_host_key`'s `read` calls it on the log
  since the create, whose key line is boot's own, when `fingerprint` finds nothing in either read, and tears down at once with
  `the image's boot.sh prints no session nonce; ADD boot.sh from gpunit v0.6.0`.

```
key(n) · step                        ─▶ key            n = the session's nonce
key(n) · step · key(m) · step        ─▶ the first key  m ≠ n: an echo cannot know n
key: … · step  (no key(n) anywhere)  ─▶ refuse: an older boot.sh
```

A command that reads boot's `/proc` can still learn the nonce; `0006` already names a root command as trusted.

### D4

After `say "the command exited $code"`, `boot.sh` runs `sleep "$GRACE_S"` with `GRACE_S=60`, then `exit "$code"`, so
`trap stop EXIT` stops the pod a minute later. A refusal exits through `refuse`, and the ceiling's subshell calls
`stop` itself: neither reaches the sleep. gpunit reads the log every 30 s ([D2](#d2)), inside the grace. In the tests
`sleep` is a stub that logs its argument, so `tests/test_boot.py` sees `60` before the stop's `curl`.

### D5

- **`0007·R6`:** `README.md:223`'s row reads "`spend --days` under 1 or over 3660".
- **`0007·R7`:** the scenario `spend:report:unreadable-ledger-fails` is added by this change's
  [spend delta](specs/spend/spec.md); `tests/test_spend.py`'s ledger test is retagged with it; `spend`'s docstring
  becomes "refuse when the billing or the ledger cannot be read".

### D6

`0008·R5` asks to edit `openspec/changes/archive/0008-a-30b-class-row/proposal.md`; `0007·R6`'s second half asks to edit
`0007`'s archived `design.md`. An archived change records what was decided then; the living specs carry the
scenarios. Each closes won't-fix, listed in the proposal's `backlog:`.

### D7

`live/serve_dead.py` runs `session.serve("qwen3-4b", 600, api=True, yes=True, …, provider=RunPod(os.environ))`
with `table.load` wrapped to add `--no-such-flag` to the row's `args`; vLLM refuses the flag and exits `2`. It collects
gpunit's lines through `log.redirect`, printing each, and passes only when `check(lines, code)` returns no failure:

- the exit code is `1`;
- a line holds `refused: the pod stopped while the model loaded`;
- a `pod:` line holds `no-such-flag`, and one holds `the command exited 2`;
- the line `pod <id> deleted` comes at most 15 s after the refusal's line, by their UTC times.

`check` is a pure function; `tests/test_serve_dead.py` binds it to fake lines, under `serve:wait:dead-pod-ends-the-wait`,
the scenario it proves live. The `Makefile` gains `live-serve-dead`, which runs the script; `serve` prints the price
before it rents. It is never in the gate.

### D8

`gpunit-vllm` is built through `.github/workflows/build-serve-image.yml` with the tag `v0.6-rc1`; `gpunit-live` and
`gpunit-live-dead` by `docker buildx build --platform linux/amd64 --push` from the repository root. Each digest replaces
the old one at `gpunit/serve/models.toml:2`, `live/gpunit.toml:4` and `live/gpunit.dead.toml:4`. The `qwen3.8-27b` row
shares the image line, so it moves too, unrun.

## Dependencies

None.

## Risks / Trade-offs

- **A since-read cut by `LOG_READ_S` holds the log's start, not its end** → vLLM's boot log is hundreds of lines
  (`live/serve_last_run.txt`), well inside one read; `make live-serve-dead` checks the exit line arrives.
- **In the hold, the quiet bound (60 s) can refuse during boot's grace, before `EXITED`** → the session still closes,
  `pod.log` still holds the crash, and the quiet refusal prints its last lines.
- **A consumer on an older `boot.sh` cannot open a session on `v0.6.0`** → the refusal names the fix; README's step 2
  names `v0.6.0`.
- **The grace bills 60 s more for each crashed command** → ~$0.01 on an A40; gpunit deletes a pod it watches before
  the stop anyway.
- **A command can learn the nonce from boot's `/proc`** → a command that hostile is trusted with the key already.
- **[D1](#d1) in `serve` and [D4](#d4) ship unproven on a real pod** → `make live-serve-dead` was written but not
  run: a fresh host pulled `gpunit-vllm` for over 15 minutes with no SSH. It runs in the next version, on a volume.
  Until then the offline tests are the only proof that the crash reaches `pod.log` inside the grace.

## Migration Plan

A consumer moving to `v0.6.0` updates its `ADD` line and checksum to `boot.sh` at `v0.6.0` and rebuilds its image, in
the same step as the gpunit pin.

## Verdict

Feasible: the dead-pod rule exists and moves; the log, the nonce and the grace are a few lines each, each with a test;
the one unknown — that the crash's lines reach the laptop inside the grace — is left to `make live-serve-dead` in the
next version (see *Risks*).
