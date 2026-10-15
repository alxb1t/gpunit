## ADDED Requirements

### Requirement: A window volume is created from the spec

`gpunit volume up` SHALL, when the spec sets `volume_gb`, create one standard network volume named
`gpunit-<project>` of `volume_gb` GB, in `volume_datacenter` when set, else in the data centre the first card of `gpus`
is in stock in, among those offering standard volumes, the highest stock winning; SHALL print the data centre, the
price of $0.07 per GB a month and the most the window can cost, and create nothing without `y` unless `--yes` is given;
SHALL mark `.gpunit/volume.pending` before the create and write `.gpunit/volume` — the id, the data centre, the size and
the UTC end, now plus `volume_ceiling` — once the create answers; and SHALL append the volume to the ledger. A spec
without `volume_gb` SHALL be refused naming `volume_gb`. No card in stock in such a data centre SHALL refuse naming the
cards. A create whose answer did not arrive SHALL keep the pending mark and exit `3`, naming `gpunit volume down`.

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
- **THEN** `volume up` refuses naming the cards, exits `1`, and creates nothing

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

### Requirement: A live window volume is extended

`gpunit volume up` on a recorded volume whose end has not passed SHALL create nothing, SHALL ask the price of the new
window, and on `y` SHALL move the volume's end to now plus `volume_ceiling` in `.gpunit/volume` and the ledger.

#### Scenario: up again extends
- **Key:** `volume:extend:moves-the-end`
- **WHEN** a volume is recorded with its end an hour away, and `volume up` runs with `volume_ceiling = "4h"` and `--yes`
- **THEN** no create is made, and `.gpunit/volume`'s end is four hours from now

### Requirement: The window volume is deleted by its verb

`gpunit volume down` SHALL delete the recorded volume, SHALL list the volumes named `gpunit-<project>` and delete each
the record does not name, and SHALL remove `.gpunit/volume` and `.gpunit/volume.pending` only when every delete
answered `204`; any other answer, a `404` among them, SHALL keep the record, say so, and exit `1`.

#### Scenario: down deletes the volume
- **Key:** `volume:down:deletes`
- **WHEN** a volume is recorded and its delete answers `204`
- **THEN** stderr says the volume is deleted, `.gpunit/volume` is gone, and the command exits `0`

#### Scenario: a lost create is swept
- **Key:** `volume:down:sweeps-by-name`
- **WHEN** `.gpunit/volume.pending` exists, no volume is recorded, and the provider lists one named `gpunit-<project>`
- **THEN** that volume is deleted, the pending mark is removed, and the command exits `0`

#### Scenario: a refused delete keeps the record
- **Key:** `volume:down:refused-delete-kept`
- **WHEN** the delete answers `409`, or `404`
- **THEN** `.gpunit/volume` remains, stderr names the answer, and the command exits `1`

### Requirement: A window volume past its ceiling is deleted by the next command

`up`, `run`, `down`, `status`, `volume up`, `volume down` and `serve` SHALL, before anything else, delete a recorded
volume whose end has passed, saying so; a delete that fails SHALL keep the record and warn. `up`, `run` and `serve`
SHALL then refuse, naming `gpunit volume up`.

#### Scenario: an overdue volume is deleted first
- **Key:** `volume:ceiling:overdue-deleted`
- **WHEN** a volume is recorded with its end passed, and `status` runs
- **THEN** the volume is deleted before the report, and stderr says it passed its ceiling

#### Scenario: a session after the ceiling refuses
- **Key:** `volume:ceiling:session-refuses`
- **WHEN** the spec sets `volume_gb`, the recorded volume's end has passed, and `up` runs
- **THEN** the volume is deleted, `up` refuses naming `gpunit volume up`, and no pod is created

### Requirement: Status names the window volume

`gpunit status` SHALL print, after its session line, a line naming the recorded volume's id, its data centre and its
end, or `overdue` past it; `status --json` SHALL be unchanged.

#### Scenario: the volume line
- **Key:** `volume:status:named`
- **WHEN** a volume `v1` in `EU-RO-1` is recorded with its end at `14:30Z`
- **THEN** stdout holds a line naming `v1`, `EU-RO-1` and `14:30Z`
