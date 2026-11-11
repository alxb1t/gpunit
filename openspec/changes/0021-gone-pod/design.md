# A gone pod's record is cleared — design

A pod is gone when its read answers 404 and the account's listing lacks it; `status` and `down` then clear its record. Verdict: ready to build, in the phases of [tasks](tasks.md).

## Context

`.gpunit/pod` outlives a pod deleted outside gpunit, and no command clears it: `status` reports `UNKNOWN` and exits `0`, `down` keeps the record on a 404 and exits `1`. isekai's billing alert reads the record's presence, so it never ends (seen 2026-11-08).

D23 keeps the record on a 404 because a wrong key gets a 404 too. D55 settled the same question for a volume: the read answers 404 and the listing, read with the same key, lacks it. A pod-scoped key gets `GET pods` 403, so a wrong key fails the listing and cannot pass for gone (`THREAT_MODEL.md`, G5 measured).

```
status / down
   │  pod read (get / delete) says it is not there
   ▼
Provider.pod(id)          ── Lost    ─▶ not gone: record kept
   │ Unknown (404)
   ▼
Provider.pod_ids()        ── Lost    ─▶ not gone: record kept
   │ id listed            ─────────────▶ not gone: record kept
   │ id absent
   ▼
gone: clear_session(), one stderr line, no ledger line
```

## Goals / Non-Goals

- Goal: a gone pod's record is cleared by `status` and by `down`, and by every caller of `down`.
- Goal: a wrong key, a lost answer and a listed pod keep the record as today.
- Non-goal: a pod warning in `spend`; isekai's banner copy.
- Non-goal: a live proof ([D10](#d10)).

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| [D1](#d1) | `Provider.pod(id)` raises `Unknown` on a 404, else `Lost`; `get` is unchanged | the waits read `get`'s `None` as "not yet" | making `get` raise: it would end a wait on a lost answer |
| [D2](#d2) | `Provider.pod_ids()` lists every pod id of the account, any name, image or status | `list()` drops `TERMINATED` and filters on the spec's image, not the record's | reusing `list()`: a record's pod of another image would read as gone |
| [D3](#d3) | `lifecycle.pod_gone(provider, pod_id)` holds the rule, as `lifecycle.gone` does for a volume | one place for the rule; a `Lost` from either read is not gone | one function for pods and volumes: their reads and listings differ in name and type |
| [D4](#d4) | `status` clears a gone record, prints `pod <id> is gone; its record is cleared` on stderr, then the no-session output; exit `0` | stdout's contract is unchanged; the person sees why the session went | a new exit code or stdout line: a patch adds none ([D8](../../../docs/decisions.md)) |
| [D5](#d5) | `down` runs the gone check on any failed delete of the recorded pod, not only a 404 | gone is proved by the read and the listing, so what a gone pod's DELETE answers does not matter | checking on a 404 alone: the answer of a gone pod's DELETE is not known |
| [D6](#d6) | Gone is no delete: no ledger line, and `.gpunit/pending` is unchanged; no threat-model row for a key of another account | `pending` marks a create that may have made an unrecorded pod, which only the sweep disproves; the person runs one account | clearing `pending` on gone: it would hide an unrecorded pod |
| [D7](#d7) | Decision D57 holds the rule; D23 is retitled and loses its 404 clause; D55's last sentence is amended; D23's anchor links are repointed | `tests/test_docs.py` checks the citations; the old title would state a rule no longer in force | a new decision beside an unchanged D23: two rules in force |
| [D8](#d8) | `FakeProvider` scripts `pod()` and `pod_ids()`; an unscripted pod read raises `Lost` | tests that rely on a pod 404 failing the teardown stay as they are | an unscripted read answering a pod or 404: each such test would need a script |
| [D9](#d9) | Debt `0020·R7` closes here: the principles row for pinned inputs names its breach | the change opens `docs/principles.md`, the card's trigger | leaving it for another change |
| [D10](#d10) | No live proof | read on 2026-11-10, RunPod REST v2: `GET pod w7qrzhsta9d4gy` answered `404 pod not found` and the account's pod listing was empty, a deleted pod not listed even as `TERMINATED` | a metered run: nothing it shows is outside the fakes |

### D1

`RunPod.pod` reads `GET /pods/<id>` as `RunPod.get` does and builds the same `PodInfo`. A 404 raises `Unknown`; any other failed read, a 200 whose body does not parse, raises `Lost`. `get` keeps returning `None`.

### D2

`RunPod.pod_ids` walks `GET /pods` through `RunPod._walk`, as `RunPod.volume_ids` does, and keeps every `id`. `Provider` gains both methods with docstrings in the form of `volume` and `volume_ids`.

### D3

```
pod(id) raises Unknown  → id not in pod_ids()   → gone
pod(id) raises Lost     →                       → not gone
pod_ids() raises Lost   →                       → not gone
pod(id) answers         →                       → not gone
```

### D4

`status` calls `pod_gone` only when `get` gave `None`, so a live pod costs no extra call. A gone pod's record is cleared with `state.clear_session()`. A window volume line still follows in words, as with no record.

### D5

In `_delete_pods`, the branch order is: a code in `DELETED` clears and says deleted; else a gone pod clears and says `pod <id> is gone; its record is cleared`, and fails nothing; else a 404 keeps the record as today; else any code keeps it as today. The project sweep then runs as before.

### D6

`status` never reads `.gpunit/pending`, and `down` clears it only when its sweep is clean, so a gone record leaves it as it is. No ledger line is written: the ledger's `deleted` lines are volumes only. The threat model gets no row for another account's key: the person uses none, so the case does not apply, and D57's Why says so.

### D7

| page | change |
|---|---|
| `docs/decisions.md` | add D57 `A pod is gone when its read and the account's listing both lack it`, Why naming the other-account case as not applying; retitle D23 `Teardown: the recorded pod and the project's pods are swept` and drop its 404 clause and Why; D55's last sentence names D57 |
| `README.md`, `docs/principles.md`, `docs/data-flow.md` | the D23 anchor becomes `d23--teardown-the-recorded-pod-and-the-projects-pods-are-swept`; their prose states the new rule and links D57 |
| `docs/usage.md` | the `status` row and the 404 note state the new rule |
| `THREAT_MODEL.md` | T47 states the new rule and its controls; the new log line is named |

D57, to land after D56 in `docs/decisions.md`:

```
### D57 · A pod is gone when its read and the account's listing both lack it

**A recorded pod whose read answers `404` and which the account's listing, read with the same key, does not hold is
gone: `status` and `down` clear its record. Gone is no delete: the ledger records no line for it, and `.gpunit/pending`
stays for the sweep to clear.**

`gpunit/lifecycle.py::pod_gone` holds the check; `gpunit/provider.py::Provider.pod` is the read and
`gpunit/provider.py::Provider.pod_ids` the listing.

- **Why:** A key that fails the listing cannot pass for gone, and a pod deleted outside gpunit left a record nothing
  cleared. A valid key of another RunPod account reads a pod as gone too; the person runs one account, so the case
  does not apply.
- **Made by:** `0021·D1`.
```

D23, in place:

```
**`down` deletes the recorded pod and sweeps the project's by name and image; a failed delete keeps the record unless
the pod is gone (decision D57).**

- **Why:** A false "gone" leaves a pod billing, and the project's pods are swept whatever the record says.
- **Made by:** `0001·D9`, `0002·D5`, `0021·D1`.
```

### D8

`FakeProvider.pod` answers the pod's entry in `pods` through `_raise_or`; an id with no entry raises `Lost`. `FakeProvider.pod_ids` answers `account_pods`, empty by default.

### D9

The card's fix is one cell of the principles row: the breach names `gpunit/serve/table.py::_args` and T55. The card is deleted by `mf-release`, not by this change.

### D10

The acceptance holds on the fakes: a record whose pod reads 404 and is missing from `pod_ids()` is cleared by `status` and by `down`; a 404 with the listing `Lost`, or the pod still listed, keeps the record; a live pod is unchanged.

## Tests

Every test is a unit or integration test on faked provider answers; the change adds no end-to-end run and no engine matrix ([T1](../../../CODING_STANDARDS.md)). Placement follows [T2](../../../CODING_STANDARDS.md): a step in an existing test where one reaches the state.

| layer | file | added | because |
|---|---|---|---|
| unit | `tests/test_runpod.py` | `test_a_pod_read_answers_the_pod_unknown_or_lost`, ids `200`, `404`, `500` | no existing test reads one pod and tells a 404 from a lost answer; `test_get_reads_the_direct_ssh_address_or_none` reads `None` for both |
| unit | `tests/test_runpod.py` | a step in `test_the_listing_names_the_projects_live_pods`: `pod_ids()` on a page with a `TERMINATED` pod and a pod of another name | the page is already there |
| fake | `tests/fakes.py` | `FakeProvider.pod` and `FakeProvider.pod_ids`, the scripts the tests below use | the protocol gains both methods, and the fake must satisfy it |
| integration | `tests/test_down.py` | `test_a_404_keeps_the_record` parametrized, ids `gone`, `listing-lost`, `still-listed` | the test already reaches a recorded pod and a 404 |
| integration | `tests/test_status.py` | `test_status_clears_a_gone_pod`, ids `gone`, `still-listed`, `listing-lost`, `read-lost` | no status test reaches a record whose read fails |

The count of the tests in `tests/test_down.py`, `tests/test_status.py` and `tests/test_runpod.py`, by `uv run pytest tests/test_down.py tests/test_status.py tests/test_runpod.py --collect-only -q`: 74 at the base, 83 after the change, nine added.

No test is deleted or merged. The tests that rely on a pod 404 failing the teardown — in `tests/test_library.py` and `tests/test_run.py`, each building `FakeProvider(deletes={"pod-1": 404})` — stay as they are: an unscripted pod read raises `Lost` ([D8](#d8)), so the record is kept.

## Dependencies

None.

## Risks / Trade-offs

- **A key of another RunPod account** reads a pod as gone: its read answers 404 and its listing is its own. The record clears while the pod bills on. Accepted: the person uses no other account's key ([D6](#d6)); D57's Why says so. A pod-scoped key cannot do it, its listing failing with 403.
- **A listing that lags** a pod just made could omit it. `status` and `down` read a record made earlier, and the pod's read answers 404 before the listing is consulted, so a pod RunPod knows is never gone.
- **`status` now reads the pod and the listing** for a record whose read failed, and makes no extra call for a live pod.

## Verdict

Ready to build, in the phases of [tasks](tasks.md): each ends on a green `make check`, the last on a green `make gate`.
