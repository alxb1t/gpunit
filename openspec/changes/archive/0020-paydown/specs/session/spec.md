## MODIFIED Requirements

### Requirement: One live session per project

The system SHALL name the pod `gpunit-<project>` and SHALL refuse `up` when `.gpunit/pod` exists, when
`.gpunit/pending` exists, when `.gpunit/waiting` names a live process other than its own, or when the provider lists a live pod of that name whose image matches the spec's;
and SHALL fail the listing, not pass it, when a pod of that name carries no image. A `.gpunit/waiting` whose process is
not alive SHALL be removed, saying so.

#### Scenario: a recorded pod refuses up
- **Key:** `session:one:recorded-refuses`
- **WHEN** `.gpunit/pod` exists
- **THEN** `up` refuses naming `gpunit down` and makes no create

#### Scenario: a listed pod refuses up
- **Key:** `session:one:listed-refuses`
- **WHEN** no record exists and the provider lists a live `gpunit-isekai` pod on the spec's image
- **THEN** `up` refuses naming the pod's id and makes no create

#### Scenario: a look-alike image is not ours
- **Key:** `session:one:look-alike-image-ignored`
- **WHEN** the provider lists a live `gpunit-isekai` pod on an image that only begins with the spec's
- **THEN** the listing does not count it

#### Scenario: a wait in the checkout refuses up
- **Key:** `session:one:waiting-refuses`
- **WHEN** `.gpunit/waiting` names a live process other than this one
- **THEN** `up` refuses saying a session is waiting for stock in this checkout, and makes no create

#### Scenario: a stale wait mark is removed
- **Key:** `session:one:stale-waiting-removed`
- **WHEN** `.gpunit/waiting` names a process that is not alive
- **THEN** `up` removes the mark, says so, and goes on

### Requirement: A stall in stock is waited out when asked

The system SHALL, when `stock_wait` or `--stock-wait` sets a duration, and every create of a round answers 400, write
the attempt line, wait 60 seconds and try the cards again, in order, until one is placed or the duration has passed;
then it SHALL refuse as when none was placed and exit `4`. No pending mark SHALL remain between rounds, and no create
SHALL count as begun; `.gpunit/waiting`, holding the process's id, SHALL guard the checkout from the first wait, and
SHALL be removed on every way out by that process alone. Before each later round it SHALL check again what it checks before the first, refusing as
there: a record, a pending mark, a listed pod, and a window volume the session's ceiling plus its wait for SSH would
outlast. A refusal of any other kind SHALL NOT wait. A signal during the wait SHALL end it, rent nothing, tear nothing
down, and exit `128 + n`; inside `gpunit.session()` it SHALL raise `Interrupted`.

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
- **THEN** it raises `Interrupted` for signal 15, no pod is created, no pending mark remains, and no pod is listed or
  deleted after the signal

#### Scenario: a round after the wait refuses beside another session
- **Key:** `session:stock:guards-rechecked`
- **WHEN** `stock_wait = "10m"`, every create of the first round answers 400, and during the wait another session
  writes `.gpunit/pod`, marks `.gpunit/pending`, or has a pod listed
- **THEN** `up` exits `1` naming `gpunit down`, makes no create in the second round, and leaves the other record as
  it was

#### Scenario: a round after the wait refuses past the window's end
- **Key:** `session:stock:window-rechecked`
- **WHEN** a window volume ends 30 seconds after the session's ceiling plus its wait for SSH would, `stock_wait =
  "10m"`, and every create of the first round answers 400
- **THEN** `up` exits `1` naming the volume's end, makes no create in the second round, and writes no record

#### Scenario: the wait marks the checkout
- **Key:** `session:stock:waiting-marked`
- **WHEN** `stock_wait = "10m"`, every create of the first round answers 400, and the second round places a pod
- **THEN** `.gpunit/waiting` holds the process's id during the wait, and is gone once the pod is placed, and after a
  give-up or a signal
