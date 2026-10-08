# Design — 0003 consumer-fit

How each fix lands: the sweep's guard, the log's second read, the key kept from the command, the refused stop.
**Verdict: feasible.** Each fix is a few lines in the file that owns the rule, re-checked at HEAD.

## Context

See [proposal](proposal.md) — *Why*. What holds at the cut, `main` at `91bf658` (`v0.1.1`):

- **The interrupt's teardown:** a signal while opening raises `_Interrupted` (`gpunit/run.py:45-46`). `_run`'s
  `except _Interrupted: pass` (`:117-118`) falls into the `finally`, which runs `session.down` whenever
  `teardown` is true (`:119-124`). `down` deletes every live pod the listing names (`gpunit/session.py:145-185`).
  `up` writes `.gpunit/pending` just before the first create (`:71`) and `.gpunit/pod` just after it (`:76-77`).
- **The host-key read:** `_verify_host_key` polls `fingerprint(provider.log(record.id, tail=LOG_TAIL))`
  (`gpunit/session.py:280-282`), `LOG_TAIL = 5000` (`:31`). `Provider.log(pod_id, *, tail)`
  (`gpunit/provider.py:95-97`); `RunPod.log` queries `tail=<n>&source=container` (`gpunit/runpod.py:161-175`).
  `FakeProvider.log` records `(pod_id, tail)` (`tests/fakes.py:95-98`).
- **`created`** is `log.utc()` — `YYYY-MM-DDTHH:MM:SSZ` (`gpunit/log.py:12-14`) — stamped after the create returns
  (`gpunit/session.py:76`).
- **The child's environment:** `"$@" &` (`boot/boot.sh:89`) inherits boot's, `RUNPOD_API_KEY` included. Boot's
  tool checks are `sshd` (`:38`) and `curl` (`:40`).
- **The stop:** `stop()` retries every answer but `200` with one message, "the stop answered HTTP <n>; trying
  again" (`boot/boot.sh:19-34`).
- **Boot's refusal tests** run on a `PATH` of the stubs plus `bash`, `date`, `touch` (`tests/test_boot.py:163-176`),
  so `env` is absent there.
- **README** step 2 names `openssh-server` and `curl` (`README.md:39`); the pins are `v0.1.1` (`:43`, `:54`).

## Goals / Non-Goals

**Goals:** each fix with a test bound to its scenario key; `make live` on a rebuilt live image.

**Non-Goals:** a new key, verb, handover variable or exit code; a change to what `down` sweeps when it runs.

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| [D1](#d1) | `_run` tears down only when the record, the pending marker or a lost create says a create began | the sweep is for a pod this session may have made | a narrower `down` |
| [D2](#d2) | `Provider.log` gains `since`; a poll whose tail holds no key reads again from `created`, stamped before the first create | a boot's log read from its start cannot lose the line | a larger tail |
| [D3](#d3) | `env -u RUNPOD_API_KEY "$@" &`; boot refuses without `env`, naming coreutils | the stop key is boot's, not the app's | `unset` in a subshell |
| [D4](#d4) | a 401 or 403 says the key cannot stop this pod and to delete it by hand, then retries | an outage still gets its stop; the operator learns the fault | giving up on a 401 |
| [D5](#d5) | README: no key in the command's environment; `env` needed; pins at `v0.1.2` | the README is what a consumer copies | — |
| [D6](#d6) | `0002·R6` closes moot | the archived design is a record | editing the archive |
| [D7](#d7) | `make live` by hand on a rebuilt live image | the gate fakes the pod; `boot.sh` changes | trusting the stubs |

### D1

`_run` sets `lost = True` in `except Lost`. In the `finally`, it tears down when `teardown and (lost or
state.pod.exists() or state.pending.exists())`. Otherwise it logs `no create began; nothing to tear down` and
counts the teardown as done, so a signal still exits `128 + n`. Test: a `FakeProvider` whose `gpu()` sends
`SIGINT` to the process; `run` exits `130`, `provider.named("list")` holds `up`'s listing alone, and
`provider.named("delete")` is empty.

### D2

`Provider.log(pod_id, *, tail, since=None)`: when `since` is set, the read starts there and `tail` is not sent.
`RunPod.log` queries `since=<since>&source=container` then. `_verify_host_key`'s attempt is
`fingerprint(log(tail=LOG_TAIL)) or fingerprint(log(tail=LOG_TAIL, since=record.created))`. `up` takes
`created = log.utc()` before `_create`, so the stamp precedes the boot. `FakeProvider.log` records `since` and
answers a separate script for it.

```
poll ─▶ tail=5000 ─▶ key? ──yes──▶ printed
                       │ no
                       ▼
                 since=created ─▶ key? ──yes──▶ printed
                                   │ no
                                   ▼
                                not yet
```

### D3

Step 1 adds `command -v env >/dev/null || refuse "env is not on PATH; install coreutils in the image"` after the
curl check. Step 5 runs `env -u RUNPOD_API_KEY "$@" &`; `env` execs the command, so `$!` is still the command's
pid. Test: boot runs `sh -c 'env > "$HOME/env.txt"'`; the file holds no `RUNPOD_API_KEY`, and the stub curl's log
says `header-ok`. `test_no_env_refuses` uses `refuses_without` with `env`, which its `PATH` already lacks.

### D4

In `stop()`, a `401` or `403` logs `the stop answered HTTP <n>: the key cannot stop this pod; delete it by hand`
before the wait. Every other answer keeps its message. Test: `CURL_CODES` of `401`, `403`, `200`.

### D5

README step 2: "It needs `openssh-server`, `curl` and coreutils' `env` in the image." Step 3 adds one sentence:
the command on the pod does not see `RUNPOD_API_KEY`. The `ADD` URL and `uv add` pin `v0.1.2`.

### D6

`0002·R6` asked to fix `0002-paydown`'s proposal and design before the archive. The archive came first, and an
archived change is a record. The card is listed under `backlog:`; no task touches it.

### D7

A **HUMAN · METERED** phase: rebuild `live/Dockerfile` for `linux/amd64`, push it, write the digest into
`live/gpunit.toml`, run `make live` with `RUNPOD_API_KEY` set, and append the tail to `live/last_run.txt`. It is
also the first live run of `AllowUsers root`, which `v0.1.1` added after its own live run.

## Dependencies

None.

## Risks / Trade-offs

- **The laptop's clock runs ahead of RunPod's** → `since=created` starts after the boot, and the fallback misses
  the line. The tail read still runs first; the stamp precedes the create by the create's own round-trip.
- **A consumer's command needed `RUNPOD_API_KEY` on the pod** → it now gets nothing, and README says so.
  A command that must call the provider is out of gpunit's model: the pod's own stop is boot's.
- **A `since=` read stalls on a live boot** → the 3 s quiet read and the 10 s cap end it.

## Verdict

Feasible. Each fix is local, each has a test, and `make live` proves the boot on a real pod.
