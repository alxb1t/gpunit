# gpunit — shared context for Claude Code

A RunPod GPU session any project can open, use and close: the `gpunit` CLI and the pod's `boot/boot.py`.

> **This file is what is true of this repo. It is not a script.** What to do comes from the task you were given.

**Read [docs/README.md](docs/README.md) first:** the guide's map, and where to start for a task.

## The quality gate — `make gate`

The gate is **`make gate`**, run at the repository root. The `Makefile` recipe is the one list of its commands;
prose names `make gate` and never copies them. It syncs the locked environment, formats, lints, type-checks (and
`boot/boot.py` as Python 3.10), runs the tests offline on faked provider answers with `boot/boot.py` at 100 % line
and branch coverage, and validates the specs. A new command lands through a change whose cut names the gate recipe
in a task.

## How a change is cut here

Each version is one change, cut, built, checked and released with the MinionsFactory `mf-*` skills. The OpenSpec
CLI is recorded, not pinned: `@fission-ai/openspec@1.11.0`, resolved on `PATH`. The version lives in
`gpunit/version.py`, which hatch reads; the release bumps it there.

## Where things live

The package's modules, their layers and the test seams: [docs/modules.md](docs/modules.md). Beside the package:
`boot/` (the pod's entrypoint), `serve/` (the serve image), `live/` (the metered proofs), `tests/`, `docs/` (the
guide), `openspec/` (the specs and the changes) and `CHANGELOG.md`. **`.minions/` holds run artefacts and is
gitignored**; nothing in it is tracked.

## What holds

The rules the code follows, each with the test that holds it: [docs/principles.md](docs/principles.md). The
decisions behind them: [docs/decisions.md](docs/decisions.md).

## The rules for a change

- An archived change is a record; a finding against it is fixed in a new change (decision D7).
- A patch closes cards and fixes; it adds no verb, `gpunit.toml` key or exit code (decision D8).
- A change that touches a trust boundary updates `docs/threat-model.md`: a new flow, secret, file mode, network call
  or log line (decision D9).
- A decision made or overturned edits `docs/decisions.md`; the change's own `design.md` keeps the history.
- A new module edits `tests/test_layers.py`'s `LAYERS` and `docs/modules.md` together.
- A refactor changes no spec scenario, message or exit code (decision D51).
- The live targets rent a real pod or volume: they run by hand, never in CI (decision D6).

## Guardrails (hold for every role)

- **Never commit a secret, or a real absolute path from the machine the run is on.**
- **Dependencies are minimal and human-approved.** Argue for a new one, and wait for approval before installing it.
- **Never weaken the gate to pass.** A deleted test, a blanket suppression, a loosened config: halt and say so.
- **State lives on disk.** Rebuild where the work is from the active change's `tasks.md` and git.
