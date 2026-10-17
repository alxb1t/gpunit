# Design — 0011 paydown

How each of `0010`'s cards closes: an end that only moves later, a mark the sweep clears, `serve`'s sweep before its
price, a sweep that stops at Ctrl-C and needs a terminal, a `deleted` ledger line, and an older `boot.sh` judged from
the log's start. **Verdict: feasible** — each fix is a few lines in the file it names, re-checked at HEAD.

## Context

See [proposal](proposal.md) — *Why*. What holds at the cut, `main` at `2ba6db0` (`v0.7.0`), `.minions/backlog.md`
read 2026-10-16:

- **`R4`:** `_extend` sets `extended = replace(window, ends=log.utc(ceiling_s))` (`gpunit/volume.py:157`), whatever
  the recorded end. `Window.ends` is one UTC form, `Z`, so ends order as strings (`gpunit/state.py:44-45`).
- **`S4`:** `volume.down` runs `lifecycle.sweep_window` before it reads the window (`gpunit/volume.py:74-76`);
  `sweep_window` (`gpunit/lifecycle.py:228-244`) clears the window on a `204` and never the mark.
- **`R6`:** `serve` reads the window at `gpunit/serve/session.py:59` and asks the price in `body()` at `:66`;
  the first sweep is `lifecycle.up`'s (`gpunit/lifecycle.py:80`), inside `library._open`. README says every command
  sweeps first (`README.md:221-222`).
- **`R9`:** `_ask` turns `KeyboardInterrupt` into `None` (`gpunit/volume.py:204-214`); `_sweep` (`:98-129`) then
  asks about the next volume. `_agree` (`:189-201`) shares `_ask`: Ctrl-C at `volume up`'s price refuses, exit `1`.
- **`S3`:** `grep -n isatty gpunit/volume.py` prints nothing; the sweep's tests feed `io.StringIO` as stdin
  (`tests/test_volume.py:234`, `:272`, `:317`, `:342`).
- **`R10`:** `volume.up` says `run gpunit volume down, which finds and deletes it` (`gpunit/volume.py:62`).
- **`R11`:** `test_a_volume_the_ledger_records_is_not_swept` asserts `"v5" not in capsys.readouterr().out`
  (`tests/test_volume.py:323`).
- **`R5`:** `spend` warns on each window volume billed today whose end fell before today (`gpunit/spend.py:79-87`).
  The ledger holds `Entry` and `VolumeEntry` lines (`gpunit/ledger.py:16-35`); `_parsed` skips a line that lacks any
  of a kind's keys (`:97-105`).
- **`R7`:** `_verify_host_key.read` judges `old_boot(lines)` when `len(lines) < LOG_TAIL` (`gpunit/lifecycle.py:388`).
  `RunPod.log` returns what arrived when its `LOG_READ_S` (10) deadline passes or the stream faults
  (`gpunit/runpod.py:191`, `:201`). Every `boot.sh` from `v0.2.0` to `v0.7.0` logs
  `say "step: the ceiling, ${GPUNIT_CEILING}s"` before any other line (`git show v0.2.0:boot/boot.sh`, line 53;
  `boot/boot.sh:55`).
- **`R8`:** asks to edit `openspec/changes/archive/0010-on-demand-volumes/proposal.md:41`.
- **The tests that turn red:** the sweep's tests above (`S3`: a `StringIO` is no terminal);
  `test_an_old_key_line_echoed_into_a_full_tail_is_no_older_boot`'s `twin-whole-log` case and
  `test_an_older_boot_is_refused_at_once`'s `step` case in `tests/test_hostkey.py` (`R7`: neither read opens with
  boot's ceiling line).

## Goals / Non-Goals

**Goals:** every card closed; no delete of an unrecorded volume without a person at a terminal; README and the specs
say what the code does.

**Non-Goals:** a new verb, `gpunit.toml` key or exit code; a change to the `Provider` seam; Ctrl-C at `volume up`'s
price, which still refuses with exit `1`.

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| [D1](#d1) | `_extend`'s end is the later of the recorded end and now plus `volume_ceiling` | `volume up` extends; no session outlives its volume | refusing a shorter ceiling while a pod is recorded |
| [D2](#d2) | `sweep_window` clears `volume.pending` when its delete answers `204` | the record beside the mark means the create came back | reading the window before the sweep in `volume.down` |
| [D3](#d3) | `serve`'s `body` sweeps, then refuses a window the sweep removed, before `_agree` | README's *before anything else* kept in code | rewording README |
| [D4](#d4) | Ctrl-C at a sweep question ends the sweep: that volume, the rest and the mark kept, exit `130` | `130` is `serve`'s Ctrl-C at its question | going on to the next volume; exit `1` |
| [D5](#d5) | the sweep asks only when `sys.stdin.isatty()`; otherwise no answer | no script or agent confirms deleting an unrecorded volume | a `--yes` for the sweep; checking every `_ask` |
| [D6](#d6) | the lost-create message and the ledger-skip test match the code | text and test fell behind `062759c` | — |
| [D7](#d7) | a `deleted` ledger line on each `204` volume delete; `spend` skips a deleted volume in its warning | the ledger is what `spend` reads | warning only on a volume that still lists |
| [D8](#d8) | `old_boot` is true only on lines that open with boot's `step: the ceiling` line | such a read reaches the log's start; no seam change | `Provider.log` reporting a cut read |
| [D9](#d9) | `0010·R8` closes won't-fix | an archived change is a record (`0008·R5`) | editing the archive |
| [D10](#d10) | `make live-volume`, by hand, its tail and the ledger's `deleted` line in `live/last_run.txt` | `volume.py` changes; the other edges are offline-only | `make live-serve` |

### D1

`_extend` in `gpunit/volume.py` keeps the price question and its text; only the end changes, before → after:

```
extended = replace(window, ends=log.utc(ceiling_s))
extended = replace(window, ends=max(window.ends, log.utc(ceiling_s)))
```

The window and the ledger line are written as today, so an unmoved end writes the same end again. The log line stays
`volume <id> extended until <ends>`. `gpunit volume down` is the one way to end a window early.

### D2

In `lifecycle.sweep_window`, after `state.clear_window()` on a `204`, `state.clear_volume_pending()`. A record beside
the mark means the create came back, as `volume.down` already rules (`gpunit/volume.py:90-94`). Every command that
sweeps clears it, so `volume.down` then sees neither record nor mark, and lists nothing.

```
volume + volume.pending, end passed ─▶ sweep_window: delete 204 ─▶ clear window, clear mark ─▶ down lists nothing
```

### D3

`serve` reads the window at `gpunit/serve/session.py:59` as today, so `spec.volume_gb` says this session mounts the
row's window. `body()` then opens, before `_agree`, with:

```
state = State(home(name))
lifecycle.sweep_window(state, lambda: provider)
window = state.window()
if spec.volume_gb is not None and (window is None or window.ends_within(0)):
    log.refuse("no window volume is up; run gpunit volume up")
```

The refusal is `_in_window`'s first, made before the price: no price is read and nothing is asked. A refusal in
`body` is exit `1` through `run.outcome`. `lifecycle.up` sweeps again and finds nothing.

### D4

`_ask` prints the newline and re-raises `KeyboardInterrupt`; `_agree` catches it and refuses with its `refused` text,
so `volume up` keeps exit `1`. `_sweep` wraps its loop:

```
except KeyboardInterrupt:
    log.say(f"the sweep stopped at volume {volume_id}; it and the rest are kept; run gpunit volume down")
    return 128 + signal.SIGINT
```

The mark is kept: the return comes before `clear_volume_pending`. A volume deleted on an earlier `y` stays deleted.

### D5

In `_sweep`, the question is put only to a terminal: `answer = _ask(question) if sys.stdin.isatty() else None`.

- **`None` is today's no answer:** `volume <id> kept: no answer; run gpunit volume down`, the mark kept, exit `1`;
  off a terminal the line adds `at a terminal, or delete it by hand`, since a rerun there can never answer.
- **`_agree` is unchanged:** `volume up --yes` already serves a script.
- **An unrecorded volume no person answers for at a terminal** goes through the RunPod console or the RunPod MCP by
  hand.

`tests/fakes.py` gains `TtyInput`, an `io.StringIO` whose `isatty()` returns `True`. `input()` reads it as it reads a
`StringIO`, since neither has a file descriptor.

### D6

- **`0010·R10`:** `gpunit/volume.py:62` reads `run gpunit volume down, which finds it and asks before deleting it`.
- **`0010·R11`:** `tests/test_volume.py:323` keeps `capsys.readouterr()` and asserts `"v5"` in neither its `out` nor
  its `err`.

### D7

`gpunit/ledger.py` gains a line of `kind` `deleted`:

```
@dataclass(frozen=True)
class Deleted:
    id: str
    kind: str   # "deleted"
    at: str

def record_deleted(volume_id: str) -> None   # appends {"id", "kind": "deleted", "at"}
def deleted() -> set[str]                    # the ids of every line of kind "deleted"
```

- **The readers:** `T` gains `"Deleted"`. A `deleted` line lacks `project`, so `read` and `volumes` skip it, and a
  volume's end stays its last `volume` line's.
- **The writers:** `record_deleted` is called after each `204` — in `volume.down`, in `volume._sweep`, and in
  `lifecycle.sweep_window`.
- **`spend`:** reads `ledger.deleted()` once and skips its ids in the warning loop (`gpunit/spend.py:81`). The amounts
  do not change: a deleted window volume still bills under its project.

The line holds no project: `sweep_window` and `status` are not given one, and `spend` reads the id alone. An
unwritable ledger warns, as every line does, and blocks no delete.

### D8

`gpunit/provider.py` gains `_BOOT_START = re.compile(r"^\S+ step: the ceiling, \d+s\s*$")`, and `old_boot` returns
`False` unless `lines` is not empty and `_BOOT_START.match(lines[0])`. `_verify_host_key` keeps
`len(lines) < LOG_TAIL and old_boot(lines)`; its comment names the start line.

```
read opens with                     judged?
<UTC> step: the ceiling, Ns         yes — the read holds the log from boot's first line
command output (cut, or a tail)     no  — the poll waits its 60 s, then "no host-key line"
```

A command can echo a ceiling line, but only at the head of a read that missed boot's own; the outcome is the same
teardown, under another reason. `tests/fakes.py` gains:

```
CEILING_LINE = "2026-10-07T00:00:00Z step: the ceiling, 3600s"
```

### D9

`0010·R8` asks to edit `openspec/changes/archive/0010-on-demand-volumes/proposal.md`. An archived change records what
was decided then; the amendment under `0010`'s design D7, and the living volume spec, say what holds.

- **It closes won't-fix**, listed in the proposal's `backlog:`.
- **No task edits the archive.**

### D10

`make live-volume` makes a volume, writes it from a pod, reads it from the next, and deletes it in its trap. The human
appends its tail and the ledger's last line, `tail -1 ~/.local/state/gpunit/ledger.jsonl`, to `live/last_run.txt` under
`<date> — make live-volume, 0011-paydown`. That line is the `deleted` line `volume down` wrote for the real volume.

## Dependencies

None.

## Risks / Trade-offs

- **A deleted volume another machine deleted is still named by `spend`** → its `deleted` line is in that machine's
  ledger; the warning is loud and harmless, as `0010·R5` found.
- **A person on a terminal piping nothing can no longer answer by `echo y |`** → that is [D5](#d5)'s point; the
  console and the RunPod MCP remain.
- **A command that echoes boot's ceiling line can still name the wrong reason** → only at the head of a read that
  missed boot's lines, and the pod is torn down either way.
- **[D3](#d3) reads the window before and after the sweep** → each read is a local file.

## Verdict

Feasible: each card is a few lines in the file it names, with a test; the one live proof is `make live-volume`,
~$0.10 by hand.
