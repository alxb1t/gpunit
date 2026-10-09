---
version: v0.2
---

# 0004 — the Python session

**`with gpunit.session(spec, environ=…) as s:` — a GPU session for a Python consumer, and `gpunit run` rebuilt on
it.** The session's host, forwarded ports, ssh line and booted image on an object; teardown on every way out;
signals and the tunnel gpunit's. The pod is told its volume in gpunit's own words. **A minor: it delivers one
feature, the library.**

| read | for |
|---|---|
| this file | why, and what changes |
| [design](design.md) | the object, the signals, the tunnel thread, `run` on top, the volume's names |
| [tasks](tasks.md) | the phases, in build order |
| `specs/` | `library` (new) · `cli` · `spec` · `session` |

## Why

**A consumer written in Python has only a subprocess today.** It must run `gpunit run -- <itself>`, pipe gpunit's
lines, and juggle signals around a child, and a pipe that dies mid-teardown can cut the teardown short. A consumer
that renders from Python wants the session as an object, and its own log for gpunit's lines.

**The pod side still speaks the provider's nouns.** A command that wants its volume reads `/runpod-volume`, and
learns which volume to expect from a variable it sets itself. A consumer then needs code to move providers.

## What Changes

- **`gpunit.session()` and `Session`**, public: `s.host`, `s.port(remote)`, `s.ssh`, `s.image`, `s.pod_id`;
  teardown when the block ends ([D1](design.md#d1)).
- **`Refused`, `Lost`, `TeardownFailed`, `Interrupted`**, the failures a caller catches ([D2](design.md#d2)).
- **Signals in-process:** SIGTERM and SIGHUP end the block as SIGINT does; none cuts the teardown
  ([D3](design.md#d3)).
- **The tunnel in a thread**, reopened with the backoff `run` already has ([D4](design.md#d4)).
- **A `say` sink** for gpunit's lines; the default sink survives a closed stderr ([D5](design.md#d5)).
- **`gpunit run` on `session()`**, its exit codes from the failures ([D6](design.md#d6)).
- **`gpunit/session.py` → `gpunit/lifecycle.py`**, so `gpunit.session` names the function alone
  ([D10](design.md#d10)).
- **`GPUNIT_VOLUME_ID` and `GPUNIT_VOLUME_PATH`** in the pod's environment; `[env]` may name no `GPUNIT_*`
  variable ([D7](design.md#d7)).
- **README:** the Python API ([D8](design.md#d8)).

## Capabilities

### New Capabilities

- `library`: the session as a Python object — what it yields, what it raises, how signals, the tunnel, the log and
  the environment behave.

### Modified Capabilities

- `cli`:
  - *A closed stderr ends no teardown* (added) — the default sink swallows a dead pipe.
- `spec`:
  - *The spec is one TOML file* — `[env]` naming a `GPUNIT_*` variable is refused.
- `session`:
  - *The volume pins the data centre* — the pod is told `GPUNIT_VOLUME_ID` and `GPUNIT_VOLUME_PATH`.

## Impact

- **Files:** `gpunit/__init__.py`, `gpunit/library.py` (new), `gpunit/lifecycle.py` (was `gpunit/session.py`),
  `gpunit/cli.py`, `gpunit/log.py`, `gpunit/run.py`, `gpunit/spec.py`, `gpunit/runpod.py`, `tests/test_library.py`
  (new), `tests/conftest.py`, `tests/test_ssh.py`, `tests/test_run.py`, `tests/test_spec.py`, `tests/test_runpod.py`,
  `tests/test_cli.py`, `README.md`, `CLAUDE.md`, `live/last_run.txt`.
- **Behaviour:** the CLI's specs hold unchanged; a spec whose `[env]` names `GPUNIT_*` is now refused.
- **`boot.sh`:** unchanged, so no image needs a rebuild.
- **Dependencies:** none ([Dependencies](design.md#dependencies)).
- **Spend:** `make live` rents one pod for at most ten minutes, by hand ([D9](design.md#d9)).

## Not in this change

- **A second provider, or a `provider` key** — trigger: a provider beside RunPod.
- **A fake session shipped for consumers** — each fakes at its own seam. Trigger: two consumers writing the same fake.
- **`serve`** — its own minor.
