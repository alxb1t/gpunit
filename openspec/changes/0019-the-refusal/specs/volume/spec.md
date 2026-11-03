## ADDED Requirements

### Requirement: Volume up waits out a stall in stock when asked

`gpunit volume up` SHALL, when `stock_wait` or `--stock-wait` sets a duration and no card is in stock in a data centre
it may use, write the attempt line, wait 60 seconds and read the stock again, until a data centre is found or the
duration has passed; then it SHALL refuse as without a wait and exit `4`. Ctrl-C during the wait SHALL create nothing
and exit `130`.

#### Scenario: a later read finds stock
- **Key:** `volume:stock:found-later`
- **WHEN** `stock_wait = "10m"`, the first stock read finds no card, and the second finds one in `EU-RO-1`
- **THEN** the volume is created in `EU-RO-1`, and stderr holds one attempt line

#### Scenario: Ctrl-C ends the wait
- **Key:** `volume:stock:ctrl-c-exits-130`
- **WHEN** `volume up` waits for stock and Ctrl-C arrives during the wait
- **THEN** nothing is created, no pending mark exists, and the command exits `130`

## MODIFIED Requirements

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
