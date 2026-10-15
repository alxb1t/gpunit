# Tasks — 0010 on-demand volumes

The seam, the spec and the record, the verbs, the session, `serve`, `spend`, the live runs and the handover, then the
images and the metered runs, per [design](design.md). Every new test carries `@pytest.mark.spec` with the key its task
names.

## Progress

- [x] 1 — The seam
- [x] 2 — The spec and the record
- [ ] 3 — The verbs
- [ ] 4 — The session
- [ ] 5 — Serve
- [ ] 6 — Spend
- [ ] 7 — The live runs and the handover
- [ ] 8 — ⚠️ **HUMAN** — the images
- [ ] 9 — ⚠️ **HUMAN · METERED** — make live-volume, make live-serve, make live-serve-dead, make live-dead

## 1 — The seam

- [x] 1.1 **HALT CHECK** — none of this change exists yet, and every card it closes is still in the backlog.
  Verify: `grep -c -E 'def create_volume|volume_gb|sweep_window' gpunit/provider.py gpunit/spec.py gpunit/lifecycle.py | grep -v ':0$' | wc -l | tr -d ' '` prints `0`, `test -e gpunit/volume.py; echo $?` prints `1`, and `grep -c -E '^- \*\*(0009·L1|0009·R6|0009·S3) ' .minions/backlog.md` prints `3`.
- [x] 1.2 Add `stock`, `volume_datacenters`, `create_volume`, `volumes` and `delete_volume` to `Provider` in `gpunit/provider.py`, `RunPod` in `gpunit/runpod.py` and `FakeProvider` in `tests/fakes.py`, per [D1](design.md#d1); in `tests/test_runpod.py` bind the reads under `volume:up:datacenter-from-stock`, the lost create under `volume:up:lost-create-exits-3`, and the listing and delete under `volume:down:sweeps-by-name`.
  Verify: `grep -c -E 'def (stock|volume_datacenters|create_volume|volumes|delete_volume)\(' gpunit/runpod.py` prints `5`, and `uv run pytest -q tests/test_runpod.py` exits 0.

## 2 — The spec and the record

- [x] 2.1 Add `volume_gb`, `volume_ceiling` and `volume_datacenter` to `gpunit/spec.py` with their refusals, per [D2](design.md#d2); in `tests/test_spec.py` bind `spec:file:volume-keys`, `spec:file:volume-gb-needs-ceiling`, `spec:file:volume-and-volume-gb-refused` and `spec:file:volume-gb-out-of-range`.
  Verify: `grep -o -E 'spec:file:volume-[a-z-]+' tests/test_spec.py | sort -u | wc -l | tr -d ' '` prints `4`, and `uv run pytest -q tests/test_spec.py` exits 0.
- [x] 2.2 Add `Window` and the volume files to `gpunit/state.py` per [D4](design.md#d4), and `record_volume` and `volumes` to `gpunit/ledger.py` per [D9](design.md#d9); in `tests/test_ledger.py` bind `spend:ledger:volume-is-recorded`, and in `tests/test_state.py` test the window's round trip.
  Verify: `grep -c '^class Window' gpunit/state.py` prints `1`, `grep -c '^def record_volume' gpunit/ledger.py` prints `1`, and `uv run pytest -q tests/test_ledger.py tests/test_state.py` exits 0.

## 3 — The verbs

- [ ] 3.1 Write `gpunit/volume.py` with `up` and `down`, per [D3](design.md#d3) and [D5](design.md#d5); in `gpunit/lifecycle.py` rename `_placeable` to `placeable` and add `sweep_window`, per [D7](design.md#d7); in `tests/test_volume.py` bind every `volume:up:`, `volume:extend:` and `volume:down:` scenario.
  Verify: `grep -o -E 'volume:(up|extend|down):[a-z0-9-]+' tests/test_volume.py | sort -u | wc -l | tr -d ' '` prints `12`, and `uv run pytest -q tests/test_volume.py` exits 0.
- [ ] 3.2 Add `volume up` and `volume down` on the spec to `gpunit/cli.py`, with the `USAGE` line, per [D8](design.md#d8); in `tests/test_cli.py` bind `cli:verbs:volume-without-action-exits-2`.
  Verify: `grep -c 'cli:verbs:volume-without-action-exits-2' tests/test_cli.py` prints `1`, and `uv run gpunit volume 2>&1 | grep -c 'volume up'` prints a number of at least `1`.

## 4 — The session

- [ ] 4.1 In `gpunit/lifecycle.py`, mount the window volume in `up` and call `sweep_window` first in `up`, `down` and `status`, per [D6](design.md#d6) and [D7](design.md#d7); in `tests/test_up.py` bind `session:volume:window-mounted`, `session:volume:window-missing-refuses`, `session:volume:outlives-window-refuses` and `volume:ceiling:session-refuses`.
  Verify: `grep -o -E '(session:volume:window-[a-z-]+|session:volume:outlives-window-refuses|volume:ceiling:session-refuses)' tests/test_up.py | sort -u | wc -l | tr -d ' '` prints `4`, and `uv run pytest -q tests/test_up.py` exits 0.
- [ ] 4.2 Print the window volume's line in `status`, per [D7](design.md#d7); in `tests/test_status.py` bind `volume:status:named` and `volume:ceiling:overdue-deleted`.
  Verify: `grep -o -E 'volume:(status:named|ceiling:overdue-deleted)' tests/test_status.py | sort -u | wc -l | tr -d ' '` prints `2`, and `uv run pytest -q tests/test_status.py` exits 0.

## 5 — Serve

- [ ] 5.1 Add `volume up --serve <row> --ceiling` and `volume down --serve <row>` to `gpunit/cli.py`, and mount a recorded window volume in `gpunit/serve/session.py`'s `serve`, per [D8](design.md#d8); in `tests/test_serve_session.py` bind `serve:volume:window-mounted` and `serve:volume:never-created`, and in `tests/test_cli.py` bind `cli:verbs:volume-serve-without-ceiling-exits-2`.
  Verify: `grep -o -E 'serve:volume:(window-mounted|never-created)' tests/test_serve_session.py | sort -u | wc -l | tr -d ' '` prints `2`, and `grep -c 'cli:verbs:volume-serve-without-ceiling-exits-2' tests/test_cli.py` prints `1`.

## 6 — Spend

- [ ] 6.1 In `gpunit/spend.py`, bill a window volume under its project and name an overdue one, per [D9](design.md#d9); in `tests/test_spend.py` bind `spend:report:window-volume-under-project` and `spend:report:overdue-volume-named`.
  Verify: `grep -o -E 'spend:report:(window-volume-under-project|overdue-volume-named)' tests/test_spend.py | sort -u | wc -l | tr -d ' '` prints `2`, and `uv run pytest -q tests/test_spend.py` exits 0.

## 7 — The live runs and the handover

- [ ] 7.1 Write `live/gpunit.volume.toml` and the `Makefile`'s `live-volume`; run `live-serve` and `live-serve-dead` inside a window; make `live-dead` print its reason; per [D10](design.md#d10).
  Verify: `make -n live-volume | grep -c 'volume up'` prints a number of at least `1`, `make -n live-serve | grep -c 'volume down --serve'` prints a number of at least `1`, and `make -n live-dead | grep -c 'reason:'` prints a number of at least `1`.
- [ ] 7.2 In `README.md`, add the window's keys to the spec sample, a *Working window* section, the volume verbs and the exit `3` row's volume; in `CLAUDE.md`, name `volume.py` and `make live-volume`; per [D12](design.md#d12).
  Verify: `grep -c '^## Working window' README.md` prints `1`, `grep -c 'volume_ceiling' README.md` prints a number of at least `1`, and `grep -c 'make live-volume' CLAUDE.md` prints `1`.

## 8 — ⚠️ **HUMAN** — the images

- [ ] 8.1 **HUMAN** — run `.github/workflows/build-serve-image.yml` with the tag `v0.7-rc1`, and write its digest into `gpunit/serve/models.toml`'s `image` line, per [D11](design.md#d11).
  Verify: `grep -c '155fc05ac7f62d873d2dd33daf940c78ae0ace7150265963c5689c23766d7613' gpunit/serve/models.toml` prints `0`.
- [ ] 8.2 **HUMAN** — build `live/Dockerfile` and `live/Dockerfile.dead` for `linux/amd64` from the repository root, push them as `ghcr.io/alxb1t/gpunit-live` and `ghcr.io/alxb1t/gpunit-live-dead`, and write their digests into `live/gpunit.toml`, `live/gpunit.volume.toml` and `live/gpunit.dead.toml`, per [D11](design.md#d11).
  Verify: `grep -c 'defd497b569eed55e7a634b8834624121edcf46041888ec5529c8ddee4e3c466' live/gpunit.toml live/gpunit.volume.toml | grep -v ':0$' | wc -l | tr -d ' '` prints `0`, and `grep -c 'd801300ce252333a3a455a91ea0d5d7cde331d6f85c1a21f8799f7f5d8682d65' live/gpunit.dead.toml` prints `0`.

## 9 — ⚠️ **HUMAN · METERED** — make live-volume, make live-serve, make live-serve-dead, make live-dead

- [ ] 9.1 **HUMAN · METERED** — with `RUNPOD_API_KEY` set, run `make live-volume`, `make live-serve`, `make live-serve-dead` and `make live-dead`; confirm through the RunPod console that no pod and no `gpunit-` volume is left; append the tails of `make live-volume` and `make live-dead` to `live/last_run.txt`, and those of `make live-serve` and `make live-serve-dead` to `live/serve_last_run.txt`, each under a header `<date> — make <target>, 0010-on-demand-volumes`, per [D10](design.md#d10). A failed target is a halt: say so and keep its lines.
  Verify: `grep -c '^2026-.*0010-on-demand-volumes' live/last_run.txt` prints `2`, `grep -c '^2026-.*0010-on-demand-volumes' live/serve_last_run.txt` prints `2`, and `grep -c 'refused: the pod stopped while the model loaded' live/serve_last_run.txt` prints a number of at least `1`.
