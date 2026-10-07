---
version: v0.1
---

# 0001 — core

**A RunPod GPU session any project can open, use and close without knowing it is RunPod.** The `gpunit` CLI
(`up · status · down · ssh · run`), a RunPod provider behind a seam, `boot/boot.sh` for the pod's half, and the
spend rules two repos paid for, made a library's. **A minor: it delivers one feature, the session.**

| read | for |
|---|---|
| this file | why, and what changes |
| [design](design.md) | the package, the provider seam, the lifecycle, the boot, the gate, `make live` |
| [tasks](tasks.md) | the phases, in build order |
| `specs/` | `cli` · `spec` · `session` · `run` · `boot` |

## Why

**isekai's and Synthetic Portraits' copies of the same scripts, drifted.** isekai carries 605 lines of bash that place a RunPod pod, verify its
host key, tunnel to it and tear it down on every way out; Synthetic Portraits carries 361 lines of an older
version on an older API. Every new GPU project would write a third copy, and every fix lands in one.

**The spend rules live in bash, untested.** A 404 read as "gone", a create whose answer was lost, a pod that
outlives its laptop — each has billed once and is guarded once, in one repo. They belong in a library with a test
each.

## What Changes

- **The `gpunit` package and CLI**, stdlib-only, with the verbs `up`, `status`, `down`, `ssh`, `run`
  ([D1](design.md#d1), [D10](design.md#d10)).
- **A `Provider` seam with one RunPod implementation** on RunPod's REST v2 ([D2](design.md#d2), [D3](design.md#d3)).
- **`gpunit.toml`**, the spec a consumer writes: project, image by digest, the GPU preference list, floors, the
  volume, the ports, the ceiling ([D4](design.md#d4)).
- **The session lifecycle**: the catalogue floor, one GPU type per create, the lost create, the bounded wait, the
  host key verified over the API log, the record, the sweep ([D7](design.md#d7)–[D9](design.md#d9)).
- **`run`**: the tunnel and the command as children, teardown on every exit ([D10](design.md#d10)).
- **`boot/boot.sh`**, the pod's half: the ceiling, the self-stop, sshd on a fresh host key, the fingerprint
  ([D11](design.md#d11)).
- **The gate** grows from `openspec validate` to isekai's five commands; **`make live`** proves the lifecycle on a
  real pod, by hand ([D13](design.md#d13), [D14](design.md#d14)).

## Capabilities

### New Capabilities

- `cli`: the verbs, the exit codes, what is printed where.
- `spec`: `gpunit.toml` — what it holds, what is refused, where secrets come from.
- `session`: `up`, `status`, `down` — placement, the wait, the host key, the record, the sweep, the spend rules.
- `run`: the tunnel, the hand-over, teardown on every exit.
- `boot`: the pod's half — what `boot.sh` requires, arms, prints and stops.

### Modified Capabilities

None.

## Impact

- **Files:** `pyproject.toml`, `uv.lock`, `gpunit/` (new package), `boot/boot.sh`, `live/`, `tests/`, `Makefile`,
  `README.md`, `CLAUDE.md`.
- **Behaviour:** none changes — the repo holds no code today.
- **Dependencies:** no runtime dependency; `ruff`, `ty` and `pytest` for the gate ([Dependencies](design.md#dependencies)).
- **Spend:** `make live` rents one pod for at most ten minutes, by hand, its price printed first ([D14](design.md#d14)).
  Nothing else in the change bills.

## Not in this change

- **Serving a model** — the `gpunit-vllm` image, the model table, `serve`, a chat. Trigger: core released and
  isekai migrated.
- **A Python `session()` promised to callers** — it exists and the CLI uses it; its signature is not public.
  Trigger: a consumer that calls it from Python.
- **A tailnet connection mode.** Trigger: a box that cannot run `gpunit serve --api` beside its agent.
- **Creating or deleting volumes; a volume size check** — the consumer's.
- **A second provider.** Trigger: RunPod's secure cloud fails to place a session.
- **Migrating isekai or Synthetic Portraits** — each is a version of its own repo.
- **A laptop-side ceiling or watchdog** — the ceiling lives on the pod.
- **RunPod's HTTP proxy; community cloud** — closed.
