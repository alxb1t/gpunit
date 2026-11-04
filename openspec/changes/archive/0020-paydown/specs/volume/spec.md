## MODIFIED Requirements

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
