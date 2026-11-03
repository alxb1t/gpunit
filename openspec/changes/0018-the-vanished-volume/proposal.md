---
bump: patch
---

# 0018 — the vanished volume

**A recorded window whose volume RunPod no longer knows is cleared and made anew, not trusted.** `volume down` and the
ceiling's sweep clear it too, telling a gone volume from a wrong key by the account's listing.

| read | for |
|---|---|
| this file | why, and what changes |
| [design](design.md) | the check, the three paths, the session's line, the tests |
| [tasks](tasks.md) | the phases, in build order |
| `specs/` | `volume`, `session` |

## Why

**A volume deleted outside gpunit leaves a record nothing clears.** `volume up` extends the record without asking
RunPod (`gpunit/volume.py::_extend`), the session's read then refuses, and `volume down` keeps the record on the
delete's `404`, since a wrong key gets one too. The way out today is `rm .gpunit/volume` by hand. isekai hit it on
2026-10-28 and 2026-11-02.

## What Changes

- **Gone is two reads:** the volume's read answers `404`, then the account's listing answers without it
  ([D1](design.md#d1)). A new provider call lists every volume id ([D2](design.md#d2)).
- **`volume up` makes a new window** for a gone volume ([D3](design.md#d3)).
- **`volume down` and the ceiling's sweep clear a gone record** ([D4](design.md#d4)).
- **The session's refusal names `gpunit volume up`**, and clears nothing ([D5](design.md#d5)).
- **D55** records the rule in `docs/decisions.md`; `docs/usage.md` says it ([D6](design.md#d6)).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `volume`:
  - *A volume RunPod no longer knows is cleared* (added): the two reads, and what `volume up`, `volume down` and the
    sweep do with a gone volume.
  - *A live window volume is extended*: only a volume that is not gone.
  - *The window volume is deleted by its verb*: a `404` keeps the record unless the volume is gone.
  - *A window volume past its ceiling is deleted by the next command*: the same for the sweep.
- `session`:
  - *The volume pins the data centre*: an unreadable window volume refuses naming `gpunit volume up`.

## Impact

- **Code:** `gpunit/lifecycle.py` (`gone`, `sweep_window`, `up`'s refusal), `gpunit/volume.py` (`up`, `down`),
  `gpunit/provider.py` and `gpunit/runpod.py` (`volume_ids`).
- **Tests:** `tests/fakes.py`, `tests/test_volume.py`, `tests/test_status.py`, `tests/test_up.py`,
  `tests/test_runpod.py`, `tests/test_serve_session.py`.
- **Docs:** `docs/decisions.md` (D55), `docs/usage.md`.
- **Consumers:** none break. A record that was stuck now clears; every other answer behaves as before.
- **Dependencies:** none ([Dependencies](design.md#dependencies)).
- **Spend:** none. No live run.

## Not in this change

- **Exit codes and the refusal's contract.** Change `0019-the-refusal`, beside this one.
- **A pod's `404`.** D23 stays: a pod's record is kept on a `404`.
- **A key of a second RunPod account.** Trigger: gpunit used with more than one account; see
  [Risks](design.md#risks--trade-offs).
- **isekai's re-pin.** isekai's half, and its live proof.
