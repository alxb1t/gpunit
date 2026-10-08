---
version: v0.1.2
backlog: [0002·R6]
---

# 0003 — consumer-fit

**The lifecycle a real consumer needs, made for every consumer.** An interrupt before the create sweeps nothing;
the host-key read survives a boot that logs heavily; the command a pod runs never holds the stop key; a stop the
key cannot make says so. **A patch: it adds no verb, no `gpunit.toml` key, no handover variable and no exit code.**

| read | for |
|---|---|
| this file | why, and what changes |
| [design](design.md) | each fix, where it lands, and why |
| [tasks](tasks.md) | the phases, in build order |
| `specs/` | `run` · `session` · `boot` |

## Why

**A first consumer's own lifecycle already holds these rules, and gpunit does not.** An interrupt while `run` opens
deletes every listed pod of the project, another working copy's session among them. A boot that logs thousands of
lines before the key is read loses the key line from `tail=5000`, and a healthy pod is torn down. The account-wide
key reaches the consumer's app, which never needs it. A key that cannot stop the pod retries forever with an
outage's message.

## What Changes

- **An interrupt sweeps only once a create began:** with no record, no pending marker and no lost create, `run`
  tears nothing down ([D1](design.md#d1)).
- **The host-key read falls back to the boot's start:** when the tail holds no key line, the log is read
  `since=` the record's `created`, now stamped before the first create ([D2](design.md#d2)).
- **The command runs without `RUNPOD_API_KEY`**, and boot refuses an image without `env` ([D3](design.md#d3)).
- **A 401 or 403 on the stop names the key** and keeps retrying ([D4](design.md#d4)).
- **README:** the key is not in the command's environment; boot needs `env`; the pins at `v0.1.2`
  ([D5](design.md#d5)).
- **`0002·R6` closes moot:** its trigger was the archive, which has happened ([D6](design.md#d6)).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `run`:
  - *Run tears down on every exit* — an interrupt before any create began tears nothing down.
- `session`:
  - *The host key is verified before anything connects* — a tail with no key line is read again from the boot's
    start.
- `boot`:
  - *Boot refuses what it cannot run on* — `env` joins `sshd` and `curl`.
  - *The pod stops itself* — a 401 or 403 names the key.
  - *The command runs as a child* — without `RUNPOD_API_KEY` in its environment.

## Impact

- **Files:** `gpunit/run.py`, `gpunit/session.py`, `gpunit/provider.py`, `gpunit/runpod.py`, `boot/boot.sh`,
  `README.md`, `live/gpunit.toml`, `live/last_run.txt`, and their tests.
- **Behaviour:** a command that read `RUNPOD_API_KEY` on the pod no longer finds it. Every other change sweeps
  less, reads more of the log, or says more.
- **Consumers:** `boot.sh`'s sha256 changes; an image pinned at `v0.1.1` keeps working.
- **Dependencies:** none ([Dependencies](design.md#dependencies)).
- **Spend:** `make live` rents one pod for at most ten minutes, by hand ([D7](design.md#d7)).

## Not in this change

- **A volume-size check, an app wait, a laptop watchdog, a `.env`** — the consumer's, by gpunit's founding
  decisions.
- **A handover variable for the booted image** — a consumer reads `.gpunit/pod`. Trigger: a consumer that cannot.
- **A line in `CLAUDE.md` on what a patch may hold** — hand-edited outside a change.
