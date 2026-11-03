## ADDED Requirements

### Requirement: A volume RunPod no longer knows is cleared

A recorded volume is **gone** when its read answers `404` and the account's listing of its volumes, read with the same
key, answers without it. A listing that fails, or that holds the volume, SHALL keep the record. A gone volume's record
SHALL be removed by `gpunit volume up`, which SHALL then create a window as on a clean start, saying `volume <id> is
gone; creating a new one`; by `gpunit volume down`, saying `volume <id> is gone; the record is cleared` and exiting `0`;
and by the sweep of a volume past its ceiling, saying it is gone. Gone is no delete: the ledger SHALL record no
`deleted` line for a gone volume, so `gpunit spend` still names one misjudged gone, as another RunPod account's key
reads it, once it passes its end and bills. A session SHALL remove no record: it SHALL refuse a window volume it cannot
read, naming `gpunit volume up`.

#### Scenario: up makes a new window for a gone volume
- **Key:** `volume:gone:up-recreates`
- **WHEN** `v1` is recorded with its end an hour away, its read answers `404`, the account lists `v7` alone, and `volume up` runs with `--yes`
- **THEN** stderr says `volume v1 is gone; creating a new one`, a volume is created, `.gpunit/volume` records it, and
  the ledger records no delete of `v1`

#### Scenario: down clears a gone volume
- **Key:** `volume:gone:down-clears`
- **WHEN** `v1` is recorded, its delete and its read answer `404`, and the account lists no volume
- **THEN** stderr says `volume v1 is gone; the record is cleared`, `.gpunit/volume` is gone, the ledger records no
  delete of `v1`, and the command exits `0`

#### Scenario: the ceiling's sweep clears a gone volume
- **Key:** `volume:gone:sweep-clears`
- **WHEN** `v1` is recorded with its end passed, its delete and its read answer `404`, the account lists no volume, and `status` runs
- **THEN** stderr says `v1` is gone, `.gpunit/volume` is gone, the ledger records no delete of `v1`, and a `spend` the
  next day that bills `v1` says it passed its ceiling and still bills

#### Scenario: a volume the listing holds is kept
- **Key:** `volume:gone:listed-kept`
- **WHEN** `v1` is recorded, its read answers `404`, and the account lists `v1`
- **THEN** `volume up` extends `v1` and creates nothing, and `volume down` keeps the record and exits `1`

#### Scenario: a listing or a read that fails keeps the record
- **Key:** `volume:gone:listing-lost-kept`
- **WHEN** `v1` is recorded, and its read answers `404` while the account's listing fails, or its read fails while the
  account's listing answers without it
- **THEN** `volume up` extends `v1` and creates nothing, and `volume down` keeps the record and exits `1`

#### Scenario: serve's row volume is made anew
- **Key:** `volume:gone:serve-recreates`
- **WHEN** a row's window records `v1`, its read answers `404`, the account lists no volume, and `volume up --serve` runs with `--ceiling` and `--yes`
- **THEN** stderr says `volume v1 is gone; creating a new one`, and a volume is created

## MODIFIED Requirements

### Requirement: A live window volume is extended

`gpunit volume up` on a recorded volume whose end has not passed, and which is not **gone**, SHALL create nothing, SHALL ask the price of the new
window, and on `y` SHALL set the volume's end to the later of its recorded end and now plus `volume_ceiling`, in
`.gpunit/volume` and the ledger. It SHALL never move the end earlier: `gpunit volume down` ends a window early.

#### Scenario: up again extends
- **Key:** `volume:extend:moves-the-end`
- **WHEN** a volume is recorded with its end an hour away, and `volume up` runs with `volume_ceiling = "4h"` and `--yes`
- **THEN** no create is made, and `.gpunit/volume`'s end is four hours from now

#### Scenario: up again never pulls the end in
- **Key:** `volume:extend:never-earlier`
- **WHEN** a volume is recorded with its end four hours away, and `volume up` runs with `volume_ceiling = "30m"` and `--yes`
- **THEN** no create is made, and `.gpunit/volume`'s end and the ledger's last line for the volume keep the end four hours away

### Requirement: The window volume is deleted by its verb

`gpunit volume down` SHALL delete the recorded volume and remove `.gpunit/volume` once that delete answers `204`. With
a volume recorded beside `.gpunit/volume.pending`, the create came back: it SHALL remove the mark and list nothing.
Only while the mark exists and no volume is recorded, a lost create being the one way a volume of this checkout goes
unrecorded, SHALL it list the volumes named `gpunit-<project>`, skip each the home directory's ledger records, and
name each other one and ask `delete volume <id>, named gpunit-<project> but in no record? [y/N]`, deleting it on `y`
alone; it SHALL remove `.gpunit/volume.pending` only when every such volume was answered and every delete answered
`204`. A stdin that is not a terminal SHALL be no answer, and SHALL be asked nothing. No answer SHALL keep the volume
and the mark, name `gpunit volume down`, and exit `1`. Ctrl-C at the question SHALL end the sweep: it SHALL keep that
volume, every volume not yet asked about and the mark, name `gpunit volume down`, and exit `130`. Any other delete
answer SHALL keep the record or the mark it concerns, say so, and exit `1`; a `404` SHALL do so too, unless the
recorded volume is gone.

#### Scenario: down deletes the volume
- **Key:** `volume:down:deletes`
- **WHEN** a volume is recorded and its delete answers `204`
- **THEN** stderr says the volume is deleted, `.gpunit/volume` is gone, and the command exits `0`

#### Scenario: a lost create is swept
- **Key:** `volume:down:sweeps-by-name`
- **WHEN** `.gpunit/volume.pending` exists, no volume is recorded, the provider lists one named `gpunit-<project>`, and the answer is `y`
- **THEN** that volume is deleted, the pending mark is removed, and the command exits `0`

#### Scenario: a refused delete keeps the record
- **Key:** `volume:down:refused-delete-kept`
- **WHEN** the delete answers `409`, or `404` while the account's listing holds the volume
- **THEN** `.gpunit/volume` remains, stderr names the answer, and the command exits `1`

#### Scenario: no pending mark, no sweep
- **Key:** `volume:down:no-sweep-without-pending`
- **WHEN** a volume `v1` is recorded, no `.gpunit/volume.pending` exists, and the provider lists `v1` and `v8` named `gpunit-<project>`
- **THEN** `v1` alone is deleted, no volume is listed, and the command exits `0`

#### Scenario: a record beside the mark clears it unswept
- **Key:** `volume:down:recorded-window-clears-the-mark`
- **WHEN** a volume `v1` is recorded beside `.gpunit/volume.pending`, and the provider lists `v1` and `v8` named `gpunit-<project>`
- **THEN** `v1` alone is deleted, no volume is listed, the pending mark is removed, and the command exits `0`, or `1`
  when `v1`'s delete answers other than `204`, the record then kept

#### Scenario: a volume the ledger records is not swept
- **Key:** `volume:down:ledger-volume-kept`
- **WHEN** `.gpunit/volume.pending` exists, no volume is recorded, the provider lists `v5` and `v9`, and the ledger records `v5`
- **THEN** only `v9` is asked about and deleted, and `v5` is neither named nor deleted

#### Scenario: the sweep asks before each delete
- **Key:** `volume:down:sweep-asks`
- **WHEN** `.gpunit/volume.pending` exists, no volume is recorded, and the provider lists `v9`
- **THEN** `volume down` asks `delete volume v9, … [y/N]`; `y` deletes it, any other answer keeps it, and either removes
  the mark and exits `0`; no answer keeps `v9` and the mark, names `gpunit volume down`, and exits `1`

#### Scenario: no terminal, no answer
- **Key:** `volume:down:sweep-needs-a-terminal`
- **WHEN** `.gpunit/volume.pending` exists, no volume is recorded, the provider lists `v9`, and stdin is not a terminal and holds `y`
- **THEN** `v9` is not deleted, the mark remains, stderr names `v9` and `gpunit volume down` at a terminal or a delete by
  hand, and the command exits `1`

#### Scenario: Ctrl-C ends the sweep
- **Key:** `volume:down:ctrl-c-ends-the-sweep`
- **WHEN** `.gpunit/volume.pending` exists, no volume is recorded, the provider lists `v8` and `v9`, and Ctrl-C answers the question about `v8`
- **THEN** no question names `v9`, no volume is deleted, the mark remains, stderr names `gpunit volume down`, and the command exits `130`

### Requirement: A window volume past its ceiling is deleted by the next command

`up`, `run`, `status`, `volume up`, `volume down` and `serve` SHALL, before anything else, delete a recorded volume
whose end has passed, saying so, `serve` before its price; `down` SHALL do so after it deletes its pods, which may hold
the volume. A delete that answers `204` beside `.gpunit/volume.pending` SHALL remove the mark too: the create came
back. A delete that fails SHALL keep the record and warn, unless it answers `404` and the volume is gone. `up`, `run` and `serve` SHALL then refuse, naming
`gpunit volume up`, `serve` before its price.

#### Scenario: an overdue volume is deleted first
- **Key:** `volume:ceiling:overdue-deleted`
- **WHEN** a volume is recorded with its end passed, and `status` runs
- **THEN** the volume is deleted before the report, and stderr says it passed its ceiling

#### Scenario: a session after the ceiling refuses
- **Key:** `volume:ceiling:session-refuses`
- **WHEN** the spec sets `volume_gb`, the recorded volume's end has passed, and `up` runs
- **THEN** the volume is deleted, `up` refuses naming `gpunit volume up`, and no pod is created

#### Scenario: down deletes the overdue volume after its pod
- **Key:** `volume:ceiling:down-after-the-pod`
- **WHEN** a pod is recorded, the recorded volume's end has passed, its delete is refused while the pod exists, and `down` runs
- **THEN** the pod is deleted, then the volume, `.gpunit/volume` is gone, and the command exits `0`

#### Scenario: the sweep clears a mark beside the record
- **Key:** `volume:ceiling:overdue-clears-the-mark`
- **WHEN** a volume `v1` is recorded beside `.gpunit/volume.pending` with its end passed, the provider lists `v1` and `v8` named `gpunit-<project>`, and `volume down` runs
- **THEN** `v1` alone is deleted, the pending mark is removed, no volume is listed, nothing is asked, and the command exits `0`

#### Scenario: serve sweeps before its price
- **Key:** `volume:ceiling:serve-sweeps-first`
- **WHEN** a row's window volume is recorded with its end passed, and `serve` runs on that row
- **THEN** the volume is deleted, `serve` refuses naming `gpunit volume up` and exits `1`, and no price is read or asked
