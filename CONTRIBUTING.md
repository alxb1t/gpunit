# Contributing to gpunit

How a change lands here, and the evidence it carries. Mandatory context, named by [AGENTS.md](AGENTS.md).

## How a change lands

Each version is one change, made with the MinionsFactory skills:

```
mf-plan ──▶ mf-cut-change ──▶ mf-build ──▶ mf-converge ──▶ mf-integrate ──▶ mf-release
```

`mf-build` closes with `mf-simplify`. `mf-integrate` merges `main` into the version when `main` has moved since the
cut. `mf-converge` may be skipped; the release then says so.

The OpenSpec CLI is recorded, not pinned: `@fission-ai/openspec@1.11.0`, resolved on `PATH`. The version lives in
`gpunit/version.py`, which hatch reads; the release bumps it there.

## The rules for a change

- An archived change is a record; a finding against it is fixed in a new change (decision D7).
- A patch closes cards and fixes; it adds no verb, `gpunit.toml` key or exit code (decision D8).
- A change that touches a trust boundary updates `THREAT_MODEL.md`: a new flow, secret, file mode, network call
  or log line (decision D9).
- A decision made or overturned edits `docs/decisions.md`; the change's own `design.md` keeps the history.
- A new module edits `tests/test_layers.py`'s `LAYERS` and `docs/modules.md` together.
- A refactor changes no spec scenario of behaviour, message or exit code; the `architecture` spec moves with the code,
  and tests change in names, imports, fakes and the expected value of a retyped seam answer alone (decision D51).
- The live targets rent a real pod or volume: they run by hand, never in CI (decision D6).

## The evidence a change carries

- **Its change directory** under `openspec/changes/`: proposal, design, tasks and spec delta.
- **Each `Verify:`**, run by the build before its box is ticked.
- **A green `make gate`** at every phase's commit.
- **A `Change: <change-id>` trailer** on each commit of a change; the bootstrap, the merge commits of the first line
  and the chores that set the repo files up carry none.
- **The check loop's findings**, in `.minions/findings/`, when converge ran.
