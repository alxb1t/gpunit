# Tasks — 0007 spend

The ledger, the billing seam, the report and its verb, the handover, then one read-only comparison with the console,
per [design](design.md). Every new test carries `@pytest.mark.spec` with the key its task names.

## Progress

- [x] 1 — The ledger
- [x] 2 — The billing seam
- [ ] 3 — The report
- [ ] 4 — The handover
- [ ] 5 — ⚠️ **HUMAN** — compare the total with the console

## 1 — The ledger

- [x] 1.1 **HALT CHECK** — no ledger and no billing read exist yet.
  Verify: `ls gpunit/ledger.py 2>&1 | grep -c 'No such file'` prints `1`, and `grep -c 'billing' gpunit/provider.py` prints `0`.
- [x] 1.2 In `tests/conftest.py`, add an autouse fixture that sets `HOME` to a directory under the test's `tmp_path`, per [D5](design.md#d5).
  Verify: `grep -c 'HOME' tests/conftest.py` prints a number of at least `1`.
- [x] 1.3 Write `gpunit/ledger.py` per [D1](design.md#d1) and call `ledger.record` in `_create` and in `down`'s sweep in `gpunit/lifecycle.py`; in `tests/test_ledger.py` bind the four `spend:ledger:*` scenarios.
  Verify: `grep -c 'ledger.record' gpunit/lifecycle.py` prints `2`, and `grep -o 'spend:ledger:[a-z-]*' tests/test_ledger.py | sort -u | wc -l | tr -d ' '` prints `4`.

## 2 — The billing seam

- [x] 2.1 Add `PodCost`, `VolumeCost`, `pod_billing` and `volume_billing` to `gpunit/provider.py` and implement them in `gpunit/runpod.py` per [D2](design.md#d2); write `tests/fixtures/billing_pods.json` and `tests/fixtures/billing_volumes.json`; in `tests/test_runpod.py` bind `spend:report:total-is-the-providers` to both reads and a 500 raising `Lost`.
  Verify: `grep -c 'def pod_billing' gpunit/provider.py gpunit/runpod.py | grep -c ':1$'` prints `2`, and `ls tests/fixtures | grep -c billing` prints `2`.
- [x] 2.2 Give `FakeProvider` in `tests/fakes.py` scripted `pod_costs` and `volume_costs` that record the window asked.
  Verify: `grep -c -E 'def (pod_billing|volume_billing)' tests/fakes.py` prints `2`, and `uv run ty check` exits 0.

## 3 — The report

- [ ] 3.1 Write `gpunit/spend.py` per [D3](design.md#d3); in `tests/test_spend.py` bind every `spend:report:*` and `spend:window:*` scenario of the change's `spend` spec.
  Verify: `grep -o -E 'spend:(report|window):[a-z-]+' tests/test_spend.py | sort -u | wc -l | tr -d ' '` prints `9`.
- [ ] 3.2 Add the `spend` verb to `gpunit/cli.py` per [D4](design.md#d4); in `tests/test_cli.py` bind `cli:verbs:spend-bad-days-exits-2`.
  Verify: `uv run gpunit spend --help | grep -c -- '--days'` prints a number of at least `1`, and `grep -c 'cli:verbs:spend-bad-days-exits-2' tests/test_cli.py` prints `1`.

## 4 — The handover

- [ ] 4.1 Add *What it cost* to `README.md` — the verb, the report's lines, what unattributed means, the day still billing — and name `ledger.py` and `spend.py` in `CLAUDE.md`'s layout.
  Verify: `grep -c 'What it cost' README.md` prints `1`, and `grep -c 'spend.py' CLAUDE.md` prints `1`.

## 5 — ⚠️ **HUMAN** — compare the total with the console

- [ ] 5.1 **HUMAN** — with `RUNPOD_API_KEY` set, run `uv run gpunit spend --days 7`; read the RunPod console's billing for the same UTC days; write both totals, and the word `equal` when they are, to `live/spend_last_run.txt` under a header `<date> — gpunit spend --days 7, 0007-spend`. A difference is a halt: say so, and keep the figures.
  Verify: `grep -c '^totals equal' live/spend_last_run.txt` prints `1`.
