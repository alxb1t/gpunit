# Tasks — 0018 the vanished volume

The check and the paths that clear a gone record, then `volume up`'s new window, per [design](design.md). Each new test
carries `@pytest.mark.spec` with the key its task names.

## Progress

- [x] 1 — Gone
- [ ] 2 — Anew

## 1 — Gone

- [x] 1.1 Add `volume_ids` to `gpunit/provider.py::Provider` and `gpunit/runpod.py::RunPod`, and `account_volumes` with
  `volume_ids` to `tests/fakes.py::FakeProvider`, per [D2](design.md#d2). Add a `volume_ids` step to
  `tests/test_runpod.py::test_the_volume_listing_walks_the_cursor_and_keeps_the_name`.
  Verify: `grep -c 'def volume_ids' gpunit/provider.py gpunit/runpod.py tests/fakes.py` prints `1` for each file, and `uv run pytest -q --no-cov tests/test_runpod.py` exits 0.
- [x] 1.2 Add `gpunit/lifecycle.py::gone` per [D1](design.md#d1).
  Verify: `grep -c '^def gone' gpunit/lifecycle.py` prints `1`.
- [x] 1.3 Clear a gone record in `gpunit/volume.py::down` and `gpunit/lifecycle.py::sweep_window`, per
  [D4](design.md#d4); edit `down`'s comment per [D6](design.md#d6). Add the tests of `volume:gone:down-clears` and
  the `volume down` half of `volume:gone:listed-kept` and `volume:gone:listing-lost-kept` to `tests/test_volume.py`,
  and `volume:gone:sweep-clears` to `tests/test_status.py`. Script `v1` in the account's listing for the `404` case of
  `test_a_refused_delete_keeps_the_record`.
  Verify: `grep -c 'is gone; the record is cleared' gpunit/volume.py gpunit/lifecycle.py` prints `1` for each file, `grep -c 'volume:gone:sweep-clears' tests/test_status.py` prints `1`, and `uv run pytest -q --no-cov tests/test_volume.py tests/test_status.py` exits 0.
- [x] 1.4 Add D55 to the end of `docs/decisions.md`, and edit `docs/usage.md`'s 404 line, per
  [D55's text](design.md#d55s-text).
  Verify: `grep -c '^### D55 · A volume is gone when' docs/decisions.md` prints `1`, `grep -c 'decision D55' docs/usage.md` prints `1`, and `uv run pytest -q --no-cov tests/test_docs.py` exits 0.

## 2 — Anew

- [ ] 2.1 Ask `lifecycle.gone` in `gpunit/volume.py::up` before `_extend`, per [D3](design.md#d3). Add the tests of
  `volume:gone:up-recreates` and the `volume up` half of `volume:gone:listed-kept` and `volume:gone:listing-lost-kept`
  to `tests/test_volume.py`. Script `v1`'s read in `test_up_again_extends` and `test_up_again_never_pulls_the_end_in`.
  Verify: `grep -c 'is gone; creating a new one' gpunit/volume.py` prints `1`, `grep -c 'volume:gone:up-recreates' tests/test_volume.py` prints `1`, and `uv run pytest -q --no-cov tests/test_volume.py` exits 0.
- [ ] 2.2 Add `; run gpunit volume up` to `gpunit/lifecycle.py::up`'s refusal of an unreadable window volume, per
  [D5](design.md#d5), and the test of `session:volume:window-unreadable-names-up` to `tests/test_up.py`.
  Verify: `grep -c 'session:volume:window-unreadable-names-up' tests/test_up.py` prints `1`, and `uv run pytest -q --no-cov tests/test_up.py` exits 0.
- [ ] 2.3 Add the test of `volume:gone:serve-recreates` to `tests/test_serve_session.py`.
  Verify: `grep -c 'volume:gone:serve-recreates' tests/test_serve_session.py` prints `1`, and `uv run pytest -q --no-cov -m "not e2e" tests/test_serve_session.py` exits 0.
