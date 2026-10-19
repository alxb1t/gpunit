---
version: v0.11.1
backlog: [0015·R7]
---

# 0016 — readme and docs

**The repo a stranger lands on: an Apache-2.0 license, a one-screen README whose every claim links what holds it, a CI
badge over `make gate`, and the GitHub description and topics.** The user's guide moves whole to `docs/usage.md`, and
the live proofs to `docs/proofs.md`.

| read | for |
|---|---|
| this file | why, and what changes |
| [design](design.md) | the license, the metadata, the workflow, the front page, the move, the tests, the GitHub side |
| [tasks](tasks.md) | the phases, in build order |
| `specs/` | `architecture` |

## Why

**gpunit is public but reads as unfinished.** It has no license, so it is all rights reserved. GitHub shows no
description, no topics and no license. Nothing shows the gate passing. The README is a long user's guide, and it gives
a reader who wants to know what this is and why to trust it nothing to scan.

**The evidence already exists.** The decisions, the principles, the tests and the dated live tails are in the repo.
The front page only has to point at them.

## What Changes

- **`LICENSE`**, Apache-2.0; `license` and `license-files` in `pyproject.toml` ([D1](design.md#d1)).
- **`pyproject.toml`'s `description` and `keywords`** become the text GitHub mirrors ([D2](design.md#d2)).
- **`.github/workflows/gate.yml`** runs `make gate` on every push and pull request ([D3](design.md#d3)).
- **`README.md` becomes a one-screen front page** ([D4](design.md#d4)).
- **`docs/usage.md`** holds README's user's guide, whole ([D5](design.md#d5)). **`docs/proofs.md`** holds the live
  proofs and their dated runs ([D6](design.md#d6)).
- **The citations follow the move:** the threat model, `extending.md`, `pins.md` and the guide's map
  ([D7](design.md#d7)). **D52** and **D53** record the front page and the gate workflow in `docs/decisions.md` ([D8](design.md#d8)).
- **Tests hold the README's length, and the workflows' triggers and pins** ([D9](design.md#d9)).
- **`0015·R7`** closes won't-fix ([D10](design.md#d10)).
- **GitHub's description and topics** are set from `pyproject.toml`, and the first CI run goes green, by hand
  ([D11](design.md#d11)).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `architecture`:
  - *The front page fits one screen* (added): `README.md` holds at most 60 lines.
  - *Every push runs the gate* (added): the gate workflow runs `make gate` on push and pull request, and every
    workflow pins its actions by commit.

## Impact

- **Repo files:** `LICENSE` (new), `pyproject.toml`, `README.md`, `.github/workflows/gate.yml` (new).
- **Docs:** `docs/usage.md` and `docs/proofs.md` (new); `docs/README.md`, `docs/decisions.md`, `docs/extending.md`,
  `docs/pins.md`, `docs/threat-model.md`.
- **Tests:** `tests/test_docs.py`, and a new `tests/test_ci.py`.
- **Consumers:** none break. README's anchors move to `docs/usage.md`; a bookmark to one lands on the front page.
- **GitHub:** the description, the topics and the license show. The workflow runs on every push.
- **Dependencies:** none ([Dependencies](design.md#dependencies)).
- **Spend:** none. No live run.

## Not in this change

- **The write-up.** The operator writes it later, in their own effort.
- **A recorded demo.** Trigger: a live run recorded for the front page, replacing a line.
- **PyPI.** Trigger: a consumer outside the operator's own projects.
- **GitHub Releases for the older tags.** `v0.11.1`'s Release is made by hand after the release.
- **A homepage URL** and a custom social preview image.
