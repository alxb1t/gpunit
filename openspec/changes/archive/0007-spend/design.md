# Design — 0007 spend

How a pod gets its project after it is gone, and how the provider's billing becomes one report: a ledger written where
gpunit first learns an id, two billing reads on the seam, a join, and a window of whole UTC days.
**Verdict: feasible** — the billing is read from the provider, the ledger is a file, and nothing is estimated.

## Context

See [proposal](proposal.md) — *Why*. What holds at the cut, `main` at `4d9688b` (`v0.3.1`):

- **`up`** records the pod after the create: `Record(pod_id, …)` written at `gpunit/lifecycle.py:85`; the create is
  `_create`, which returns the id of the first card the provider placed (`gpunit/lifecycle.py:245-261`).
- **`down`** deletes the recorded pod, then lists the project's live pods and deletes each the record does not name
  (`gpunit/lifecycle.py:153-190`, the sweep at `:179-186`). `State.clear_session` removes the record
  (`gpunit/state.py`), so no id survives teardown.
- **The seam:** `Provider` is a protocol of `gpu · volume · create · get · log · list · delete · stop`
  (`gpunit/provider.py:83-118`); `RunPod` implements it over `_call` (`gpunit/runpod.py:244`) on
  `API = "https://api.runpod.io/v2"` (`:28`); a body that cannot be read raises `Lost`.
- **The verbs** are built in `_parser`; `parse` refuses an unreadable spec path with exit `2`, except for `serve`,
  which has none (`gpunit/cli.py`).
- **The tests** run `up`, `down` and `serve` in-process (`tests/conftest.py`, `tests/helpers.py`), and
  `FakeProvider` is what `ty` checks against the protocol (`tests/fakes.py`).
- **The billing, read live on 2026-10-12** for 2026-10-06 → 10-12, UTC: pods `GET /v2/billing/pods` — records
  `podId`, `startTime`, `endTime`, `gpuAmount`, `cpuAmount`, `diskAmount`, `totalAmount` per pod per bucket; volumes
  `GET /v2/billing/network-volumes` — records `networkVolumeId`, `startTime`, `endTime`, `standardAmount`,
  `highPerformanceAmount`, `totalAmount`. The query takes `bucketSize` (`hour` to `year`), `startTime`, `endTime`.
  The week's pods came to $1.46 over fifteen records' pods, its storage to $0.33.

## Goals / Non-Goals

**Goals:** a report whose every amount is the provider's; each pod under its project where gpunit knew it.

**Non-Goals:** an estimate; storage by project; a back-fill; a budget; a public function.

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| [D1](#d1) | `gpunit/ledger.py`: one JSON line per pod id, at the create and at the sweep; best-effort | billing carries no name; an id learned once is attributable forever | a field on the pod; the record kept after teardown |
| [D2](#d2) | `Provider.pod_billing` and `volume_billing` over `[start, end)` in day buckets | the amount charged, per second, disk included | price × seconds |
| [D3](#d3) | `gpunit/spend.py`: the window, the join, the render, the JSON; an unreadable billing refuses | a table of zeros would read as a free week | printing what was read |
| [D4](#d4) | the `spend` verb: `--days N` (default 7), `--json`, no spec | it needs only the key | a spec path |
| [D5](#d5) | tests isolate `HOME`; `FakeProvider` scripts billing | no test may write the operator's ledger | patching the ledger's path in each test |
| [D6](#d6) | the last phase is a read-only live comparison, by hand | only the console shows the provider's own total | trusting the join |

### D1

```
up ─▶ _create ─▶ provider.create answers an id ─▶ ledger.record(project, id, card, image)
down ─▶ sweep lists a pod no record names ─▶ ledger.record(project, id, None, image) ─▶ delete
```

`ledger.record` appends `{"id", "project", "card", "image", "at"}` — `at` is `log.utc()` — to
`~/.local/state/gpunit/ledger.jsonl`, the directory made `0700` and the file `0600`. An `OSError` says
`warning: the ledger could not be written: …` and returns; nothing raised reaches a session or a teardown.
`ledger.read()` returns `{id: Entry}`, the first line for an id winning, a missing file as empty, a line that is not
JSON or lacks a key skipped. The sweep records before it deletes, so a pod it fails to delete is still named.

### D2

`provider.py` gains `PodCost(pod_id, start, amount)` and `VolumeCost(volume_id, start, amount)`, and the protocol
`pod_billing(start, end) -> list[PodCost]` and `volume_billing(start, end) -> list[VolumeCost]`, each raising `Lost` on
an answer that is not `200` or a body that does not read. `RunPod` calls `GET /billing/pods` and
`GET /billing/network-volumes` with `bucketSize=day`, `startTime` and `endTime`, and takes each record's `totalAmount`.
`tests/fixtures/billing_pods.json` and `billing_volumes.json` hold trimmed copies of the live answers of 2026-10-12.

### D3

```
now ─▶ window [day(now) − (N−1) .. day(now) + 1)
    ─▶ pod_billing, volume_billing   (Lost → refuse, print nothing)
    ─▶ per pod id: Σ amount ─▶ project = ledger.read().get(id) or "unattributed"
    ─▶ lines: project (pods, $) desc · unattributed · volumes desc · total
```

Amounts are summed as `Decimal(str(x))` and printed to the cent; the total sums the unrounded figures and is
rounded once. `render` prints:

```
spend, 2026-10-06 → 2026-10-12 (UTC)
pods      isekai               6 pods  $0.57
pods      unattributed         6 pods  $0.20
storage   db7sc8cild                   $0.31
total                                  $1.79
```

stdout holds the table; stderr holds `the current UTC day is still being billed; its figures can change`. `--json`
prints `{"from", "to", "projects": [{"project", "pods", "amount"}], "unattributed": {"pods", "amount"},
"storage": [{"volume", "amount"}], "total"}`, amounts as numbers of cents rounded.

### D4

`spend` is a subparser with `--days` (an integer of at least 1, else a usage error) and `--json`; it has no `--spec`.
`parse` returns early for it, as it does for `serve`; `_run` hands it `RunPod()` and exits `0`, `1` on a refusal.
`USAGE` names it. A missing key refuses as every verb does.

### D5

`tests/conftest.py` gains an autouse fixture setting `HOME` to a directory under the test's `tmp_path`, so `ledger.path()`
and `serve`'s `home()` land in it. `FakeProvider` takes `pod_costs` and `volume_costs` scripts, answers them by the
asked window, and records the window. `tests/test_ledger.py`, `tests/test_spend.py` and additions to `tests/test_cli.py`
and `tests/test_runpod.py` hold the scenarios.

### D6

A **HUMAN** phase, free: with `RUNPOD_API_KEY` set, `uv run gpunit spend --days 7`; the RunPod console's billing for the
same UTC days; both totals and the word `equal` written to `live/spend_last_run.txt`. A difference is a halt.

## Dependencies

None.

## Risks / Trade-offs

- **The billing's shape is read from one live answer** → the fixtures come from it, and phase 5 compares the total with
  the console's.
- **The current day is partial** → named on stderr.
- **A pod before the ledger, or whose create was lost, is unattributed** → shown as such, never dropped.
- **Rounding** → one rounding at the total; a line's cents may not add to it by a cent.
- **The ledger is per machine** → another machine's pods are unattributed here; the report says so by the line.

## Verdict

Feasible: two reads and a file, a join of a few lines, and a comparison with the console to prove the sum.
