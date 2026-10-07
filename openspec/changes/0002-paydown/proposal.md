---
version: v0.1.1
backlog: [0001·R3, 0001·R4, 0001·R5, 0001·R6, 0001·R7, 0001·R8, 0001·R9, 0001·R10, 0001·R12, 0001·R13, 0001·S3, 0001·S4]
---

# 0002 — paydown

**core's converge backlog, closed before a consumer pins gpunit.** The security cards — the ssh line takes the
user's ssh_config, the API key follows a redirect — and the cards that open the same files. **A patch: it adds no
verb, no `gpunit.toml` key and no exit code.**

| read | for |
|---|---|
| this file | why, and what changes |
| [design](design.md) | each fix, the card it closes, and why that fix |
| [tasks](tasks.md) | the phases, in build order |
| `specs/` | `session` · `spec` · `run` · `boot` |

## Why

**isekai pins gpunit next, by tag.** `v0.1.0` left its converge cards open in `.minions/backlog.md`, the security ones among them:
a user's `ForwardAgent yes` hands their agent to the pod (S4), and a redirect from the API sends the account key
to another host (S3). One leaks a pod: `up` crashes after the create when `ssh-keyscan` is missing (R6). Each card
is one line and a test, and most name "the next change that opens" a file this change opens anyway.

## What Changes

- **Every ssh line is gpunit's own:** no ssh_config is read, only the session's key is offered
  ([D1](design.md#d1), S4).
- **The OpenSSH client is checked before anything is rented**, and `gpunit ssh` without `ssh` refuses instead of
  a traceback ([D2](design.md#d2), R5, R6).
- **A port outside 1–65535 is refused** in `gpunit.toml` ([D3](design.md#d3), R9).
- **The API client follows no redirect**; a 3xx is an answer like any non-2xx ([D4](design.md#d4), S3).
- **A delete's success is 200 or 204**, for `down` and the sweep alike ([D5](design.md#d5), R7).
- **The log read ends when the stream goes quiet**, not after a fixed 10 s ([D6](design.md#d6), R8).
- **A command killed by signal `n` makes `run` exit `128 + n`** ([D7](design.md#d7), R3).
- **A tunnel that keeps dying is reopened with backoff**, 1 s doubling to 30 s ([D8](design.md#d8), R4).
- **Boot's sshd runs with PAM on**, so a `!`-locked root logs in by key ([D9](design.md#d9), R13).
- **The curl refusal gets its own scenario** ([D10](design.md#d10), R12).
- **README:** the archived design's link, the pins at `v0.1.1`, the ssh line ([D11](design.md#d11)).
- **R10 closes moot:** the design it names is archived, and the archive is history ([D12](design.md#d12)).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `session`:
  - *Ssh opens a shell on the session* — `-F none` and `IdentitiesOnly=yes`; a refusal when `ssh` cannot run.
  - *Up refuses without the OpenSSH client* (added) — `ssh`, `ssh-keygen`, `ssh-keyscan` checked before any
    request.
  - *The host key is verified before anything connects* — the log read ends on a quiet stream.
  - *Down never reads a 404 as gone, and sweeps every listed pod* — a success is 200 or 204.
- `spec`:
  - *The spec is one TOML file* — a port outside 1–65535 is refused.
  - *Secrets come from the environment only* — the key never follows a redirect.
- `run`:
  - *Run tears down on every exit* — a command killed by signal `n` counts as `128 + n`.
  - *A dead tunnel is reopened* — with backoff, reset after a tunnel that lived.
- `boot`:
  - *Boot refuses what it cannot run on* — the scenario `boot:refuse:no-curl`.
  - *Sshd on a fresh host key, and the fingerprint printed* — PAM's account check on.

## Impact

- **Files:** `gpunit/session.py`, `gpunit/cli.py`, `gpunit/spec.py`, `gpunit/provider.py`, `gpunit/runpod.py`,
  `gpunit/run.py`, `boot/boot.sh`, `README.md`, `live/gpunit.toml`, `live/last_run.txt`, and their tests.
- **Behaviour:** a user's ssh_config no longer applies to `gpunit ssh`, the tunnel or `GPUNIT_SSH`. Every other
  change refuses earlier, fails safe, or is faster.
- **Consumers:** `boot.sh`'s sha256 changes; a Dockerfile pinned at `v0.1.0` keeps working, and moves to `v0.1.1`
  by its own change.
- **Dependencies:** none ([Dependencies](design.md#dependencies)).
- **Spend:** `make live` rents one pod for at most ten minutes, by hand ([D13](design.md#d13)).

## Not in this change

- **A line in `CLAUDE.md` on what a patch may hold** — hand-edited outside the change.
- **Migrating isekai or Synthetic Portraits** — each is a version of its own repo.
- **`serve`** — its own minor.
- **Editing the archived `0001-core`** — R10 closes moot instead.
