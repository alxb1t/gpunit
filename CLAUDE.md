# gpunit — shared context for Claude Code

A RunPod GPU session any project can open, use and close: the `gpunit` CLI and the pod's `boot/boot.sh`.

> **This file is what is true of this repo. It is not a script.** What to do comes from the task you were given.

## The quality gate — `make gate`

The gate is **`make gate`**, run at the repository root. The `Makefile` recipe is the one list of its commands;
prose names `make gate` and never copies them. It syncs the locked environment, formats, lints, type-checks, runs
the tests offline on faked provider answers, and validates the specs. A new command lands through a change whose
cut names the gate recipe in a task.

## How a change is cut here

Each version is one change, cut, built, checked and released with the MinionsFactory `mf-*` skills. The OpenSpec
CLI is recorded, not pinned: `@fission-ai/openspec@1.11.0`, resolved on `PATH`.

## Layout — where things live here

- **`gpunit/`** — the package: `cli.py` (verbs, exit codes), `spec.py` (`gpunit.toml`), `state.py` (`.gpunit/`),
  `provider.py` (the `Provider` seam), `runpod.py` (RunPod's REST v2), `lifecycle.py` (`up · status · down · ssh`),
  `run.py` (`run`), `log.py` (stderr lines).
- **`boot/boot.sh`** — the pod's entrypoint: the ceiling, sshd, the fingerprint, the command.
- **`tests/`** — `fakes.py` (`FakeProvider`, `FakeOpener`), `fixtures/` (v2 bodies), one `test_*.py` per module;
  every test carries `@pytest.mark.spec("<scenario key>")`.
- **`live/`** — the metered proof on a real pod, run by hand.
- **`openspec/`** — the living specs in `specs/`; the changes in `changes/`, the shipped ones in `changes/archive/`.
- **`.minions/`** — run artefacts, **gitignored**; nothing in it is tracked.
- **`CHANGELOG.md`** — Keep a Changelog: each phase appends under `## [Unreleased]`, the release cuts it.

## Invariants

- **No runtime dependency:** `dependencies = []` in `pyproject.toml`; the stdlib carries the package.
- **The key never on argv:** `runpod.py` sends it in a request header, `boot.sh` on a file descriptor
  (`test_gpu_reads_the_memory_and_the_secure_price`, `test_the_commands_end_stops_the_pod`).
- **The ceiling is required:** no default, no pod without it (`test_no_ceiling_no_pod`).
- **A 404 is never gone:** `down` keeps the record (`test_a_404_keeps_the_record`).
- **`make live` is never in CI:** it rents a real pod; the gate fakes every provider answer.

## Guardrails (hold for every role)

- **Never commit a secret, or a real absolute path from the machine the run is on.**
- **Dependencies are minimal and human-approved.** Argue for a new one, and wait for approval before installing it.
- **Never weaken the gate to pass.** A deleted test, a blanket suppression, a loosened config: halt and say so.
- **State lives on disk.** Rebuild where the work is from the active change's `tasks.md` and git.
