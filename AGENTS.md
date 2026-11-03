# gpunit — shared context for coding agents

A RunPod GPU session any project can open, use and close: the `gpunit` CLI and the pod's `boot/boot.py`.

> **This file is what is true of this repo. It is not a script.** What to do comes from the task you were given.

**Before work, read [the coding standards](CODING_STANDARDS.md) and [how a change lands](CONTRIBUTING.md): mandatory
shared context.** **Before designing, building or reviewing, also read [the architecture](ARCHITECTURE.md),
[the decisions in force](docs/decisions.md) and [the threat model](THREAT_MODEL.md).**

## The quality gate — `make gate`

The gate is **`make gate`**, run at the repository root. The `Makefile` recipe is the one list of its commands;
prose names `make gate` and never copies them. It syncs the locked environment, formats, lints, type-checks (and
`boot/boot.py` as Python 3.10), runs the tests offline on faked provider answers with `boot/boot.py` at 100 % line
and branch coverage, and validates the specs. A new command lands through a change whose cut names the gate recipe
in a task. `make e2e` runs the tests that need a real loopback socket, out of the gate (decision D54).

## The run's lines

- **Worktrees:** `../` — each version's worktree sits beside the primary, named by its change id.
- **Workspace setup:** `uv sync --locked` — restores the environment a fresh worktree lacks.

## Tests

A test is placed by its cost: every gate run pays for it again.

- **The lowest layer that can fail for it** — unit, then integration, then end-to-end only for what a browser
  alone shows.
- **A step in an existing test before a new one** — one that already reaches the page, record or fixture.
- **Engines only where they differ** — client behaviour on each engine; server-rendered output on one.
- **Deleted or merged only as a change's `## Tests` table names it** — each removed test mapped to the test that
  carries its proofs, or to a decision in force at the base that retires it.

## Where things live

The package's modules, their layers and the test seams: [docs/modules.md](docs/modules.md). Beside the package:
`boot/` (the pod's entrypoint), `serve/` (the serve image), `live/` (the metered proofs), `tests/`, `docs/` (the
guide), `openspec/` (the specs and the changes) and `CHANGELOG.md`. **`.minions/` holds run artefacts and is
gitignored**; nothing in it is tracked.

## What holds

The rules the code follows, each with the test that holds it: [docs/principles.md](docs/principles.md). The
decisions behind them: [docs/decisions.md](docs/decisions.md).

## Guardrails (hold for every role)

- **Never commit a secret, or a real absolute path from the machine the run is on.**
- **Dependencies are minimal and human-approved.** Argue for a new one, and wait for approval before installing it.
- **Never weaken the gate to pass.** A deleted test, a blanket suppression, a loosened config: halt and say so.
  A test deleted or merged as the change's `## Tests` table names it is not a weakening.
- **State lives on disk.** Rebuild where the work is from the active change's `tasks.md` and git.
