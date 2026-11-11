# gpunit — shared context for coding agents

A RunPod GPU session any project can open, use and close: the `gpunit` CLI and the pod's `boot/boot.py`.

> **This file is what is true of this repo. It is not a script.** What to do comes from the task you were given.

**Before work, read [the coding standards](CODING_STANDARDS.md) and [how a change lands](CONTRIBUTING.md): mandatory
shared context.** **Before designing, building or reviewing, also read [the architecture](ARCHITECTURE.md),
[the principles](docs/principles.md), [the decisions in force](docs/decisions.md) and
[the threat model](THREAT_MODEL.md).**

## The quality gate — `make gate`

The gate is **`make gate`**, run at the repository root. The `Makefile` recipe is the one list of its commands;
prose names `make gate` and never copies them. It syncs the locked environment, formats, lints, type-checks (and
`boot/boot.py` as Python 3.10), runs the tests offline on faked provider answers with `boot/boot.py` at 100 % line
and branch coverage, and validates the specs. A new command lands through a change whose cut names the gate recipe
in a task.

- **One test:** `uv run pytest tests/test_docs.py::test_the_front_page_fits_one_screen`.
- **The `e2e` mark:** the tests that need a real loopback socket. `make gate` skips them and `make e2e` runs them
  (decision D54).

## The run's lines

- **Worktrees:** `../` — each version's worktree sits beside the primary, named by its change id.
- **Workspace setup:** `uv sync --locked` — restores the environment a fresh worktree lacks.

## Where things live

The package's modules, their layers and the test seams: [docs/modules.md](docs/modules.md). Beside the package:
`boot/` (the pod's entrypoint), `serve/` (the serve image), `live/` (the metered proofs), `tests/`, `docs/` (the
guide), `openspec/` (the specs and the changes) and `CHANGELOG.md`. **`.minions/` holds run artefacts and is
gitignored**; nothing in it is tracked.

## Guardrails (hold for every role)

- **Never commit a secret, or a real absolute path from the machine the run is on.**
- **Dependencies are minimal and human-approved.** Argue for a new one, and wait for approval before installing it.
- **Never weaken the gate to pass.** A deleted test, a blanket suppression, a loosened config: halt and say so.
  A test deleted or merged as the change's `## Tests` table names it is not a weakening.
- **State lives on disk.** Rebuild where the work is from the active change's `tasks.md` and git.
