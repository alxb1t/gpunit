# Tasks — 0011 paydown

The window, the sweep, the ledger and the boot, then the metered run, per [design](design.md). Every new test carries
`@pytest.mark.spec` with the key its task names.

## Progress

- [ ] 1 — The window
- [ ] 2 — The sweep
- [ ] 3 — The ledger
- [ ] 4 — The boot
- [ ] 5 — ⚠️ **HUMAN · METERED** — make live-volume

## 1 — The window

`0010·R4`, `0010·S4`, `0010·R6`.

- [ ] 1.1 **HALT CHECK** — none of this change's fixes exists yet, and every card it closes is still in the backlog.
  Verify: `grep -c -E '^- \*\*0010·(R4|R5|R6|R7|R8|R9|R10|R11|S3|S4) ' .minions/backlog.md` prints `10`, and `grep -c -E 'isatty|record_deleted|step: the ceiling|max\(window\.ends' gpunit/volume.py gpunit/ledger.py gpunit/provider.py gpunit/lifecycle.py gpunit/serve/session.py gpunit/spend.py | grep -v ':0$' | wc -l | tr -d ' '` prints `0`.
- [ ] 1.2 In `gpunit/volume.py`'s `_extend`, take the later end, per [D1](design.md#d1); in `tests/test_volume.py` bind `volume:extend:never-earlier`; in `README.md`'s *Working window*, the bullet becomes "`volume up` again extends a live volume to now plus `volume_ceiling`, never earlier than its end, after the price".
  Verify: `grep -c 'max(window.ends, log.utc(ceiling_s))' gpunit/volume.py` prints `1`, `grep -c 'volume:extend:never-earlier' tests/test_volume.py` prints `1`, `grep -c 'never earlier than its end' README.md` prints `1`, and `uv run pytest -q tests/test_volume.py` exits 0.
- [ ] 1.3 In `gpunit/lifecycle.py`'s `sweep_window`, clear the pending mark on a `204`, per [D2](design.md#d2); in `tests/test_volume.py` bind `volume:ceiling:overdue-clears-the-mark`.
  Verify: `grep -A20 '^def sweep_window' gpunit/lifecycle.py | grep -c 'clear_volume_pending'` prints `1`, `grep -c 'volume:ceiling:overdue-clears-the-mark' tests/test_volume.py` prints `1`, and `uv run pytest -q tests/test_volume.py tests/test_status.py tests/test_down.py tests/test_up.py` exits 0.
- [ ] 1.4 In `gpunit/serve/session.py`'s `serve`, sweep and refuse at the top of `body()`, before `_agree`, per [D3](design.md#d3); in `tests/test_serve_session.py` bind `volume:ceiling:serve-sweeps-first`, asserting no `gpu` call and no question.
  Verify: `grep -c 'lifecycle.sweep_window' gpunit/serve/session.py` prints `1`, `grep -c 'volume:ceiling:serve-sweeps-first' tests/test_serve_session.py` prints `1`, and `uv run pytest -q tests/test_serve_session.py` exits 0.

## 2 — The sweep

`0010·S3`, `0010·R9`, `0010·R10`, `0010·R11`.

- [ ] 2.1 Add `TtyInput` to `tests/fakes.py`, per [D5](design.md#d5), and feed it as stdin in `test_a_lost_create_is_swept`, `test_a_failed_sweep_keeps_the_pending_mark`, `test_a_volume_the_ledger_records_is_not_swept` and `test_the_sweep_asks_before_each_delete` in `tests/test_volume.py`.
  Verify: `grep -c '^class TtyInput' tests/fakes.py` prints `1`, `grep -c 'TtyInput(' tests/test_volume.py` prints `4`, and `uv run pytest -q tests/test_volume.py` exits 0.
- [ ] 2.2 In `gpunit/volume.py`'s `_sweep`, ask only when `sys.stdin.isatty()`, per [D5](design.md#d5); in `tests/test_volume.py` bind `volume:down:sweep-needs-a-terminal` with a `StringIO` stdin holding `y`.
  Verify: `grep -c 'sys.stdin.isatty()' gpunit/volume.py` prints `1`, `grep -c 'volume:down:sweep-needs-a-terminal' tests/test_volume.py` prints `1`, and `uv run pytest -q tests/test_volume.py` exits 0.
- [ ] 2.3 In `gpunit/volume.py`, make `_ask` re-raise `KeyboardInterrupt`, `_agree` refuse on it, and `_sweep` return `128 + signal.SIGINT`, per [D4](design.md#d4); in `tests/test_volume.py` bind `volume:down:ctrl-c-ends-the-sweep`, `input` raising `KeyboardInterrupt`.
  Verify: `grep -c '128 + signal.SIGINT' gpunit/volume.py` prints `1`, `grep -c 'volume:down:ctrl-c-ends-the-sweep' tests/test_volume.py` prints `1`, and `uv run pytest -q tests/test_volume.py tests/test_serve_session.py tests/test_cli.py` exits 0.
- [ ] 2.4 Reword `gpunit/volume.py`'s lost-create line, and assert it in `test_a_lost_create_keeps_the_pending_mark`; in `test_a_volume_the_ledger_records_is_not_swept`, assign `captured = capsys.readouterr()` and assert `"v5"` in neither `captured.out` nor `captured.err`, per [D6](design.md#d6).
  Verify: `grep -c 'which finds it and asks before deleting it' gpunit/volume.py tests/test_volume.py | grep -c ':1$'` prints `2`, `grep -c '"v5" not in captured.err' tests/test_volume.py` prints `1`, and `uv run pytest -q tests/test_volume.py` exits 0.
- [ ] 2.5 In `README.md`, the *Working window*'s lost-create bullet adds "a stdin that is not a terminal is no answer, and Ctrl-C ends the sweep"; the exit row `128+n` adds "; Ctrl-C at `volume down`'s sweep question is `130`".
  Verify: `grep -c 'not a terminal is no answer' README.md` prints `1`, and `grep -c 'sweep question is' README.md` prints `1`.

## 3 — The ledger

`0010·R5`.

- [ ] 3.1 In `gpunit/ledger.py`, add `Deleted`, `record_deleted` and `deleted`, per [D7](design.md#d7); in `tests/test_ledger.py` bind `spend:ledger:delete-is-recorded` to the line's keys, `id`, `kind` and `at`.
  Verify: `grep -c -E '^def (record_deleted|deleted)\(' gpunit/ledger.py` prints `2`, `grep -c 'spend:ledger:delete-is-recorded' tests/test_ledger.py` prints `1`, and `uv run pytest -q tests/test_ledger.py` exits 0.
- [ ] 3.2 Call `ledger.record_deleted` after each `204` in `volume.down`, `volume._sweep` and `lifecycle.sweep_window`, per [D7](design.md#d7); in `tests/test_volume.py` bind `spend:ledger:delete-is-recorded` to each delete.
  Verify: `cat gpunit/volume.py gpunit/lifecycle.py | grep -c 'ledger.record_deleted('` prints `3`, `grep -c 'spend:ledger:delete-is-recorded' tests/test_volume.py` prints `1`, and `uv run pytest -q tests/test_volume.py tests/test_status.py tests/test_down.py tests/test_up.py` exits 0.
- [ ] 3.3 In `gpunit/spend.py`, skip the ids of `ledger.deleted()` in the overdue warning, per [D7](design.md#d7); in `tests/test_spend.py` bind `spend:report:deleted-volume-not-named`.
  Verify: `grep -c 'ledger.deleted()' gpunit/spend.py` prints `1`, `grep -c 'spend:report:deleted-volume-not-named' tests/test_spend.py` prints `1`, and `uv run pytest -q tests/test_spend.py` exits 0.
- [ ] 3.4 In `README.md`'s *What it cost*, the ledger bullet adds "`volume down` and the sweeps add a line for each volume they delete"; the window-volume bullet names a volume "that the ledger does not record as deleted".
  Verify: `grep -c 'add a line for each volume they delete' README.md` prints `1`, and `grep -c 'does not record as deleted' README.md` prints `1`.

## 4 — The boot

`0010·R7`.

- [ ] 4.1 In `gpunit/provider.py`, add `_BOOT_START` and make `old_boot` need it on the first line; in `gpunit/lifecycle.py`, make `_verify_host_key.read`'s comment name that line, per [D8](design.md#d8).
  Verify: `grep -c '^_BOOT_START = ' gpunit/provider.py` prints `1`, and `grep -c 'step: the ceiling' gpunit/lifecycle.py` prints `1`.
- [ ] 4.2 Add `CEILING_LINE` to `tests/fakes.py`; open the reads of the `twin-whole-log` case in `test_an_old_key_line_echoed_into_a_full_tail_is_no_older_boot` and the `step` case in `test_an_older_boot_is_refused_at_once` with it; bind `session:hostkey:cut-read-not-judged` in `tests/test_hostkey.py`.
  Verify: `grep -c '^CEILING_LINE = ' tests/fakes.py` prints `1`, `grep -c 'session:hostkey:cut-read-not-judged' tests/test_hostkey.py` prints `1`, and `uv run pytest -q tests/test_hostkey.py tests/test_runpod.py tests/test_up.py` exits 0.

## 5 — ⚠️ **HUMAN · METERED** — make live-volume

- [ ] 5.1 **HUMAN · METERED** — with `RUNPOD_API_KEY` set, run `make live-volume` (~$0.10), and confirm no pod or network volume is left; append its tail and `tail -1 ~/.local/state/gpunit/ledger.jsonl` to `live/last_run.txt`, under a header `<date> — make live-volume, 0011-paydown`, per [D10](design.md#d10).
  Verify: `grep -c '^20[0-9-]* — make live-volume, 0011-paydown' live/last_run.txt` prints `1`, and `grep -c '"kind": "deleted"' live/last_run.txt` prints `1`.
