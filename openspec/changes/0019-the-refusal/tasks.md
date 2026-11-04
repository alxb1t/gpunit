# Tasks — 0019 the refusal

The codes, then the lines, then the wait, per [design](design.md). Each new test carries `@pytest.mark.spec` with the
key its task names.

## Progress

- [x] 1 — The codes
- [x] 2 — The lines
- [ ] 3 — The wait

## 1 — The codes

- [x] 1.1 Give `log.Refusal` its `code`, `log.refuse` its `code=` and `gpunit/log.py` `NO_CAPACITY` and `NO_FIT`;
  return `refused.code` in `gpunit/cli.py::_run` and `gpunit/run.py::outcome`, per [D2](design.md#d2).
  Verify: `grep -c 'NO_CAPACITY = 4' gpunit/log.py` prints `1`, `grep -c 'NO_FIT = 5' gpunit/log.py` prints `1`, and `uv run pytest -q --no-cov -m "not e2e"` exits 0.
- [x] 1.2 Refuse with `NO_CAPACITY` in `gpunit/volume.py::_datacenter` and `gpunit/lifecycle.py::up`'s none placed,
  and with `NO_FIT` in `gpunit/lifecycle.py::placeable`, per [D1](design.md#d1). Rename
  `test_none_placed_exits_1_with_no_record` to `test_none_placed_exits_4_with_no_record` in `tests/test_up.py`; assert
  `4` in `test_no_stock_refuses_naming_the_cards` and `test_no_stock_within_the_allow_list_refuses`
  (`tests/test_volume.py`). Add the tests of `cli:exits:no-capacity-exits-4` and `cli:exits:no-fit-exits-5` to
  `tests/test_up.py`.
  Verify: `grep -c 'cli:exits:no-fit-exits-5' tests/test_up.py` prints `1`, and `uv run pytest -q --no-cov tests/test_up.py tests/test_volume.py` exits 0.
- [x] 1.3 Re-raise Ctrl-C at `gpunit/volume.py::_agree` and return `130` for it in `gpunit/cli.py::_run`, per
  [D3](design.md#d3). `test_an_interrupt_at_the_price_creates_nothing` binds `volume:up:ctrl-c-at-price-exits-130` and
  asserts `130`.
  Verify: `grep -c 'volume:up:ctrl-c-at-price-exits-130' tests/test_volume.py` prints `1`, and `uv run pytest -q --no-cov tests/test_volume.py` exits 0.
- [x] 1.4 Amend D32 in `docs/decisions.md` and add the `4` and `5` rows to `docs/usage.md`'s exit table, per
  [The decisions' text](design.md#the-decisions-text).
  Verify: `grep -c '^### D32 · Exit codes: .0., .1., .2., .3., .4., .5., .128+n.$' docs/decisions.md` prints `1`, `grep -c '^| .4. | ' docs/usage.md` prints `1`, `grep -c '^| .5. | ' docs/usage.md` prints `1`, and `uv run pytest -q --no-cov tests/test_docs.py` exits 0.

## 2 — The lines

- [x] 2.1 Add `## The lines a caller reads` to `docs/usage.md`, per [D4](design.md#d4), and the test of
  `cli:lines:skipped-forms` to `tests/test_up.py`, asserting both `skipped:` forms whole.
  Verify: `grep -c '^## The lines a caller reads$' docs/usage.md` prints `1`, `grep -c 'cli:lines:skipped-forms' tests/test_up.py` prints `1`, and `uv run pytest -q --no-cov tests/test_up.py tests/test_docs.py` exits 0.

## 3 — The wait

- [ ] 3.1 Add `stock_wait` to `gpunit/spec.py` as `Spec.stock_wait_s`, per [D5](design.md#d5), and the test of
  `spec:file:stock-wait-duration` to `tests/test_spec.py`.
  Verify: `grep -c '"stock_wait"' gpunit/spec.py` prints `2`, the allowed key and its read, and `uv run pytest -q --no-cov tests/test_spec.py` exits 0.
- [ ] 3.2 Add `--stock-wait` to `up`, `run`, `serve` and `volume up` in `gpunit/cli.py`, named in `USAGE`, and set it
  on the row's spec in `gpunit/serve/session.py`, per [D5](design.md#d5). Add a `--stock-wait soon` usage case to
  `tests/test_cli.py`.
  Verify: `grep -c 'stock-wait' gpunit/cli.py` prints a number of at least `2`, and `uv run pytest -q --no-cov -m "not e2e" tests/test_cli.py` exits 0.
- [ ] 3.3 Add `gpunit/lifecycle.py::stock_round` and ask it in `lifecycle.up` and `gpunit/volume.py::_datacenter`, per
  [D6](design.md#d6). Add the tests of `session:stock:placed-later`, `session:stock:gives-up` and
  `session:stock:no-fit-never-waits` to `tests/test_up.py`, and of `volume:stock:found-later` and
  `cli:lines:attempt-form` to `tests/test_volume.py`.
  Verify: `grep -c '^def stock_round' gpunit/lifecycle.py` prints `1`, `grep -c 'session:stock:gives-up' tests/test_up.py` prints `1`, and `uv run pytest -q --no-cov tests/test_up.py tests/test_volume.py` exits 0.
- [ ] 3.4 Add the tests of `session:stock:signal-ends-the-wait` to `tests/test_library.py` and
  `volume:stock:ctrl-c-exits-130` to `tests/test_volume.py`, per [D7](design.md#d7): the clock's sleep raises.
  Verify: `grep -c 'session:stock:signal-ends-the-wait' tests/test_library.py` prints `1`, and `uv run pytest -q --no-cov -m "not e2e" tests/test_library.py tests/test_volume.py` exits 0.
- [ ] 3.5 Add D56 to the end of `docs/decisions.md`, per [The decisions' text](design.md#the-decisions-text), and
  `stock_wait` to `docs/usage.md`'s keys.
  Verify: `grep -c '^### D56 · A stall in stock is waited out on request$' docs/decisions.md` prints `1`, `grep -c 'stock_wait' docs/usage.md` prints a number of at least `1`, and `uv run pytest -q --no-cov tests/test_docs.py` exits 0.
