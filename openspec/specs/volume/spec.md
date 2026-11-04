## Purpose

A network volume that lives for a working window: made from the spec by `gpunit volume up`, mounted by every session in
its data centre, and deleted by `gpunit volume down` or by its own ceiling, so no storage bills between windows.

## Requirements

### Requirement: A window volume is created from the spec

`gpunit volume up` SHALL, when the spec sets `volume_gb`, create one standard network volume named
`gpunit-<project>` of `volume_gb` GB, in `volume_datacenter` when set, else in the data centre the first card of `gpus`
is in stock in, among those offering standard volumes and, when the spec sets `datacenters`, among those it names, the
highest stock winning; SHALL print the data centre, the
price of $0.07 per GB a month and the most the window can cost, and create nothing without `y` unless `--yes` is given;
SHALL mark `.gpunit/volume.pending` before the create and write `.gpunit/volume` — the id, the data centre, the size and
the UTC end, now plus `volume_ceiling` — once the create answers; and SHALL append the volume to the ledger. A spec
without `volume_gb` SHALL be refused naming `volume_gb`. No card in stock in such a data centre SHALL refuse naming the
cards, and `datacenters` when set, and exit `4`. Ctrl-C at the price question SHALL create nothing and exit `130`. A create whose answer did not arrive SHALL keep the pending mark and exit `3`, naming
`gpunit volume down`.

#### Scenario: the volume is made where the first card is in stock
- **Key:** `volume:up:datacenter-from-stock`
- **WHEN** `gpus = ["NVIDIA A40", "NVIDIA L40"]`, the A40 is in stock in `EU-RO-1` alone, and `EU-RO-1` offers standard volumes
- **THEN** the create names `gpunit-<project>`, `volume_gb` GB, `EU-RO-1` and the standard tier, and `.gpunit/volume` holds its id and `EU-RO-1`

#### Scenario: the data centre is given
- **Key:** `volume:up:datacenter-given`
- **WHEN** `volume_datacenter = "CA-MTL-4"`
- **THEN** the create names `CA-MTL-4`, and no stock is read

#### Scenario: no stock refuses
- **Key:** `volume:up:no-stock-refuses`
- **WHEN** no card of `gpus` is in stock in a data centre offering standard volumes
- **THEN** `volume up` refuses naming the cards, exits `4`, and creates nothing

#### Scenario: no is the default
- **Key:** `volume:up:no-by-default`
- **WHEN** `volume up` asks the price and the answer is empty
- **THEN** nothing is created, stderr says `not created`, and the command exits `1`

#### Scenario: the price names the window
- **Key:** `volume:up:price-names-the-window`
- **WHEN** `volume_gb = 60` and `volume_ceiling = "4h"`
- **THEN** the question names $0.07 per GB a month and at most `$0.03`, 60 GB for 4 h at 730 h a month, up to the cent

#### Scenario: no volume_gb, no volume
- **Key:** `volume:up:needs-volume-gb`
- **WHEN** the spec has no `volume_gb`
- **THEN** `volume up` refuses naming `volume_gb`, exits `1`, and makes no request

#### Scenario: a lost create exits 3
- **Key:** `volume:up:lost-create-exits-3`
- **WHEN** the create's answer is a 5xx
- **THEN** `.gpunit/volume.pending` remains, stderr names `gpunit volume down`, and the command exits `3`

#### Scenario: a pending mark refuses
- **Key:** `volume:up:pending-refuses`
- **WHEN** `.gpunit/volume.pending` exists
- **THEN** `volume up` refuses naming `gpunit volume down`, and creates nothing

#### Scenario: the stock choice stays within the allow-list
- **Key:** `volume:up:datacenter-within-allow-list`
- **WHEN** `datacenters = ["EU-SE-1"]`, and the first card is in stock `HIGH` in `EU-RO-1` and `LOW` in `EU-SE-1`, both
  offering standard volumes
- **THEN** the create names `EU-SE-1`

#### Scenario: no stock within the allow-list refuses
- **Key:** `volume:up:no-stock-in-allow-list-refuses`
- **WHEN** `datacenters = ["EU-SE-1"]`, and no card of `gpus` is in stock in `EU-SE-1`
- **THEN** `volume up` refuses naming the cards and `datacenters`, exits `4`, and creates nothing

#### Scenario: Ctrl-C at the price exits 130
- **Key:** `volume:up:ctrl-c-at-price-exits-130`
- **WHEN** `volume up` asks the price and Ctrl-C answers
- **THEN** nothing is created, stderr says `not created`, and the command exits `130`

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

### Requirement: Status names the window volume

`gpunit status` SHALL print, after its session line, a line naming the recorded volume's id, its data centre and its
end, or `overdue` past it; `status --json` SHALL be unchanged.

#### Scenario: the volume line
- **Key:** `volume:status:named`
- **WHEN** a volume `v1` in `EU-RO-1` is recorded with its end at `14:30Z`
- **THEN** stdout holds a line naming `v1`, `EU-RO-1` and `14:30Z`

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

### Requirement: Volume up waits out a stall in stock when asked

`gpunit volume up` SHALL, when `stock_wait` or `--stock-wait` sets a duration and no card is in stock in a data centre
it may use, write the attempt line, wait 60 seconds and read the stock again, until a data centre is found or the
duration has passed; then it SHALL refuse as without a wait and exit `4`. Ctrl-C during the wait SHALL create nothing
and exit `130`. It SHALL keep `.gpunit/waiting` through the wait as a session does, and SHALL refuse while another
live process's mark exists.

#### Scenario: a later read finds stock
- **Key:** `volume:stock:found-later`
- **WHEN** `stock_wait = "10m"`, the first stock read finds no card, and the second finds one in `EU-RO-1`
- **THEN** the volume is created in `EU-RO-1`, and stderr holds one attempt line

#### Scenario: Ctrl-C ends the wait
- **Key:** `volume:stock:ctrl-c-exits-130`
- **WHEN** `volume up` waits for stock and Ctrl-C arrives during the wait
- **THEN** nothing is created, no pending mark exists, and the command exits `130`

#### Scenario: volume up's wait marks the checkout
- **Key:** `volume:stock:waiting-marked`
- **WHEN** `volume up` waits for stock, and a second `volume up` runs in the checkout during the wait
- **THEN** the second refuses saying a session is waiting for stock in this checkout, and the first's mark is gone once it ends
