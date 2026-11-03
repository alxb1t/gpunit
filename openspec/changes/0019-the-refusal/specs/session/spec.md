## ADDED Requirements

### Requirement: A stall in stock is waited out when asked

The system SHALL, when `stock_wait` or `--stock-wait` sets a duration, and every create of a round answers 400, write
the attempt line, wait 60 seconds and try the cards again, in order, until one is placed or the duration has passed;
then it SHALL refuse as when none was placed and exit `4`. No pending mark SHALL remain between rounds. A refusal of
any other kind SHALL NOT wait. A signal during the wait SHALL end it, rent nothing, and exit `128 + n`; inside
`gpunit.session()` it SHALL raise `Interrupted`.

#### Scenario: the wait places a pod on a later round
- **Key:** `session:stock:placed-later`
- **WHEN** `stock_wait = "10m"`, every create of the first round answers 400, and the second round's first create answers 201
- **THEN** the session is on that card, stderr holds one attempt line, and the clock waited 60 seconds

#### Scenario: the wait gives up with the refusal
- **Key:** `session:stock:gives-up`
- **WHEN** `--stock-wait 2m` and every create answers 400
- **THEN** `up` exits `4` after its rounds, no record or pending mark exists, and no round starts after the two minutes

#### Scenario: a card that does not fit never waits
- **Key:** `session:stock:no-fit-never-waits`
- **WHEN** `stock_wait = "1h"` and every card costs more than `max_hourly`
- **THEN** `up` exits `5` at once, and no attempt line is written

#### Scenario: a signal ends the wait
- **Key:** `session:stock:signal-ends-the-wait`
- **WHEN** `gpunit.session()` waits for stock and `SIGTERM` arrives during the wait
- **THEN** it raises `Interrupted` for signal 15, no pod is created, and no pending mark remains

## MODIFIED Requirements

### Requirement: A GPU is placed from the preference list

The system SHALL read each named GPU's memory from the provider's catalogue, SHALL refuse a name the catalogue
does not know, SHALL skip a card under `vram_gb` or over `max_hourly`, SHALL try the remaining cards in order
with one create each, SHALL move to the next on a refusal the provider attributes to capacity or a rule (a 400),
SHALL exit `5` when no card meets `vram_gb` and `max_hourly`, and SHALL exit `4` when none was placed.

#### Scenario: an unknown card refuses
- **Key:** `session:place:unknown-card-refuses`
- **WHEN** `gpus` names a card the catalogue answers 404 for
- **THEN** `up` refuses naming the card and makes no create

#### Scenario: a card under the floor is skipped
- **Key:** `session:place:under-floor-skipped`
- **WHEN** the first card has less memory than `vram_gb` and the second has enough
- **THEN** the first create is for the second card, and stderr says the first was skipped

#### Scenario: a 400 moves on
- **Key:** `session:place:400-moves-on`
- **WHEN** the create for the first card answers 400 and the second answers 201
- **THEN** the session is on the second card and exits `0`

#### Scenario: none placed
- **Key:** `session:place:none-placed`
- **WHEN** every create answers 400
- **THEN** `up` exits `4`, no record exists, and `.gpunit/pending` is gone
