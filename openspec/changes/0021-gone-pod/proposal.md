---
bump: patch
debt: [0020·R7]
---

# A gone pod's record is cleared

A recorded pod whose read answers 404 and which the account's pod listing lacks is gone: `status` and `down` clear its record.

Reading map: [design](design.md) holds the rule, its decisions and the test cost, [tasks](tasks.md) holds the phases: the provider, the rule, the word.

## Why

A pod deleted outside gpunit leaves `.gpunit/pod` behind, and no command clears it. isekai saw this on 2026-11-08: its billing alert reads the record's presence, so the alert never ended.

`down` keeps the record on a 404, because a wrong key gets a 404 too ([D23](../../../docs/decisions.md)). A volume solved this in [D55](../../../docs/decisions.md): the read answers 404 and the account's listing lacks it. A pod gets the same rule.

## What Changes

- `Provider.pod(id)` reads one pod and raises `Unknown` on a 404, else `Lost`. `Provider.pod_ids()` lists every pod id of the account. `get` is unchanged.
- `lifecycle.pod_gone` holds the rule: `Unknown` from the read, then the id absent from `pod_ids()`. A `Lost` from either is not gone.
- `status` clears a gone pod's record, says so on stderr, and prints the no-session output. Exit stays `0`.
- `down` runs the same check on any failed delete of the recorded pod. Gone clears the record and is no failure. Anything else keeps today's behaviour.
- Gone is no delete: no ledger line. `.gpunit/pending` is unchanged.
- A new decision, D57, holds the rule. D23 loses its 404 clause and D55 its last sentence.
- Requirement changes, one line each:
  - `Down never reads a 404 as gone, and sweeps every listed pod` (session) is removed, and `Down clears a record only when its pod is gone, and sweeps every listed pod` is added.
  - `Status reports the record, in words or JSON` (cli) gains the gone case.
- Debt `0020·R7` closes: the principles row for pinned inputs names its breach.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `session`: the down requirement is renamed and gains the gone case.
- `cli`: the status requirement gains the gone case.

## Impact

- Code: `gpunit/provider.py`, `gpunit/runpod.py`, `gpunit/lifecycle.py`, `tests/fakes.py`.
- Tests: `tests/test_runpod.py`, `tests/test_down.py`, `tests/test_status.py`.
- Docs: `docs/decisions.md`, `docs/principles.md`, `docs/usage.md`, `docs/data-flow.md`, `README.md`, `THREAT_MODEL.md`, and the `session` and `cli` specs through the delta.
- No new verb, config key or exit code ([D8](../../../docs/decisions.md)). No new network call: `pod` reads `GET /pods/<id>` as `get` does, and `pod_ids` walks `GET /pods` as `list` does.

## Not in this change

- A pod warning in `spend`, twin to the volume's.
- isekai's banner copy and its gpunit pin: isekai's follow-up, after this release.
- A live proof: the fake-provider steps hold the acceptance ([D6](../../../docs/decisions.md)).
