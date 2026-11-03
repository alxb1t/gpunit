# Design — 0018 the vanished volume

One check tells a volume RunPod no longer knows from a refused read, and the three paths that hold a window record use
it. **Verdict: feasible.**

## Context

A window's record is `.gpunit/volume` (`gpunit/state.py::Window`). Three paths keep it when RunPod has lost the volume:

```
volume up    record live ─▶ _extend: no read ─▶ the session's read refuses, forever
volume down  delete ─▶ 404 ─▶ "the record is kept"      (a wrong key gets a 404 too)
sweep        past its end ─▶ delete ─▶ 404 ─▶ warns, record kept
```

`RunPod.volume` raises `Unknown` on a `404` (`gpunit/runpod.py::RunPod.volume`). `RunPod.volumes` lists the ids of one
name (`gpunit/runpod.py::RunPod.volumes`), through `gpunit/runpod.py::RunPod._walk`, which raises `Lost` on any failed
page. A revoked or mistyped key fails the listing with a `401`; a key without volume read fails it with a `403`. The
sweep, `gpunit/lifecycle.py::sweep_window`, is given a `State` and no spec, so it has no volume name to list by.
`gpunit/lifecycle.py::delete_volume` records the ledger's `deleted` line on a `204`.

## Goals / Non-Goals

**Goals:** a gone volume's record clears in `volume up`, `volume down` and the sweep, each saying so; every other
answer keeps the record as today.

**Non-Goals:** a pod's `404` (D23 stays); exit codes; a second RunPod account.

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| <a id="d1"></a>**D1** | `gpunit/lifecycle.py::gone(provider, volume_id) -> bool`: `True` only when `provider.volume(volume_id)` raises `Unknown` and `provider.volume_ids()` answers without `volume_id`. A `Lost` from either, a read that answers, or a listing that holds the id is `False` | a key that fails the listing cannot pass for gone | the `404` alone: a wrong key gets one too |
| <a id="d2"></a>**D2** | `Provider.volume_ids() -> list[str]`, every volume id of the key's account; raise `Lost`. `RunPod.volume_ids` walks `/network-volumes` through `_walk`, as `volumes` does, keeping every id. `FakeProvider` answers its `account_volumes` script, default empty | the sweep has no name; one listing serves all three paths | `volumes(name)` with a name passed into the sweep: `status` has no spec |
| <a id="d3"></a>**D3** | `gpunit/volume.py::up`, with a live window recorded, asks `lifecycle.gone` before `_extend`. Gone: `state.clear_window()`, no `deleted` ledger line, `volume <id> is gone; creating a new one`, then the create a clean start makes | isekai's ask: a lost volume is made anew | extending a record nothing checked |
| <a id="d4"></a>**D4** | A delete answering `404` asks `lifecycle.gone`. In `gpunit/volume.py::down`, gone: `state.clear_window()`, `volume <id> is gone; the record is cleared`, and no failure. In `gpunit/lifecycle.py::sweep_window`, gone: the `204` branch's clears, and `volume <id> passed its ceiling at <ends> and is gone; the record is cleared`. No gone path writes the ledger's `deleted` line, which `gpunit/lifecycle.py::delete_volume` writes on a `204` alone | the record holds nothing billing; a misjudged gone still bills, and `spend` names it only without a `deleted` line | a second verb to clear it; a `deleted` line, which silences `spend` |
| <a id="d5"></a>**D5** | `gpunit/lifecycle.py::up`'s volume read refuses, for a window volume (`spec.volume_gb` set), with `; run gpunit volume up` after the fault; it clears nothing | one writer of the record; the next `volume up` repairs it | the session clearing the record |
| <a id="d6"></a>**D6** | D55 in `docs/decisions.md`, per [D55's text](#d55s-text). `docs/usage.md`'s `**A 404 is not "gone".**` line: before → after in [D55's text](#d55s-text). The comment `# A 404 is never gone: a wrong key gets one too.` in `gpunit/volume.py::down` → `# A 404 is gone only when the listing lacks it too: decision D55.` | the rule review reads | |

The listing is the endpoint `RunPod.volumes` already calls, no secret moves, and each new line names a volume id, as
the lines beside it do. `THREAT_MODEL.md`'s T48 names the second-account residual, `spend`'s warning as its control and the
console as its delete; F9 and T31 say a gone verdict clears the record without a delete (decision D9).

## D55's text

```markdown
### D55 · A volume is gone when its read and the account's listing both lack it

**A recorded volume whose read answers `404` and which the account's listing, read with the same key, does not hold is
gone: `volume up` makes a new window, `volume down` and the ceiling's sweep clear the record. Gone is no delete: the
ledger records no `deleted` line for it, so `gpunit spend` still names it once it passes its end and bills. A pod's
`404` still keeps its record (decision D23).**

`gpunit/lifecycle.py::gone` holds the check; `gpunit/provider.py::Provider.volume_ids` is the listing.

- **Why:** A key that fails the listing cannot pass for gone, and a volume deleted outside gpunit left a record
  nothing cleared. A valid key of another RunPod account reads the volume as gone too, its listing being its own
  account's; a volume truly gone never bills again, so `spend`'s warning names only one misjudged so.
- **Made by:** `0018·D1`.
```

`docs/usage.md`, before → after:

- before: `- **A 404 is not "gone".** A wrong key gets a 404 too; `down` keeps the record and exits `1`.`
- after: `- **A 404 is not "gone".** A wrong key gets a 404 too; `down` keeps a pod's record and exits `1`. A window
  volume is gone only when the account's listing lacks it too; then its record clears (decision D55).`

## Tests

| layer | adds | removes |
|---|---|---|
| unit | `tests/test_volume.py`: `volume:gone:up-recreates`, `volume:gone:down-clears`, `volume:gone:listed-kept`, `volume:gone:listing-lost-kept`; `tests/test_status.py`: `volume:gone:sweep-clears`; `tests/test_up.py`: `session:volume:window-unreadable-names-up`; `tests/test_serve_session.py`: `volume:gone:serve-recreates`; a `volume_ids` step in `tests/test_runpod.py::test_the_volume_listing_walks_the_cursor_and_keeps_the_name` | none |
| end-to-end | none | none |

The suite stands at 567 tests, by `uv run pytest --collect-only -q` at the base. Changed, not removed:
`test_up_again_extends` and `test_up_again_never_pulls_the_end_in` script `v1`'s read;
`test_a_refused_delete_keeps_the_record`'s `404` case scripts `v1` in the account's listing. This change deletes and
merges no test.

## Dependencies

None.

## Risks / Trade-offs

- **A valid key of a second RunPod account reads as gone** — its listing answers without the volume, which may still
  bill in the first account → gpunit is used with one account; a gone path writes no `deleted` line, so `gpunit spend`
  with the first account's key still attributes the volume and, past its end, names it as still billing (T48).
- **One more read per `volume up` on a live window** → a `GET` that bills nothing.

## Verdict

**feasible.** Every file and symbol named exists at `bebc030`, and no verb, `gpunit.toml` key or exit code moves, so
the change is a patch (decision D8).
