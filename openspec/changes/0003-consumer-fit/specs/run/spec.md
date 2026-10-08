## MODIFIED Requirements

### Requirement: Run tears down on every exit

The system SHALL tear the session down when the command exits, on `SIGINT`, `SIGTERM` and `SIGHUP`, and after a
lost create; SHALL ignore a second interrupt while tearing down; SHALL kill the tunnel first; and SHALL exit with
the command's code when the teardown succeeded — `128 + n` for a command killed by signal `n` — `1` when it did
not, even after a signal, `3` after a lost create. An interrupt that arrives before this run began a create — no
record or pending marker written since the run started, no lost create — SHALL tear nothing down and delete no pod,
not even one an earlier `gpunit up` recorded, and `run` SHALL exit `128 + n`.

#### Scenario: the command's exit tears down
- **Key:** `run:teardown:on-exit`
- **WHEN** the command exits `0`
- **THEN** the pod is deleted and `run` exits `0`

#### Scenario: the command's failure is passed through
- **Key:** `run:teardown:code-passed`
- **WHEN** the command exits `7` and the teardown succeeds
- **THEN** `run` exits `7`

#### Scenario: a command killed by a signal
- **Key:** `run:teardown:signalled-command`
- **WHEN** the command is killed by `SIGKILL` and the teardown succeeds
- **THEN** `run` exits `137`

#### Scenario: an interrupt tears down once
- **Key:** `run:teardown:interrupt`
- **WHEN** `SIGINT` arrives during the command, and again during the teardown
- **THEN** the teardown runs to its end once and `run` exits `130`

#### Scenario: an interrupt before the create sweeps nothing
- **Key:** `run:teardown:interrupt-before-create`
- **WHEN** `SIGINT` arrives while `up` reads the catalogue, before any create
- **THEN** `run` lists and deletes no pod after the signal, stderr says no create began, and `run` exits `130`

#### Scenario: an interrupt beside an earlier record deletes nothing
- **Key:** `run:teardown:interrupt-beside-record`
- **WHEN** a pod is already recorded by an earlier `gpunit up`, and `SIGINT` arrives during `up`'s tool check
- **THEN** `run` lists and deletes no pod, the record remains, stderr says no create began, and `run` exits `130`

#### Scenario: a failed teardown is exit 1
- **Key:** `run:teardown:failure-is-1`
- **WHEN** the command exits `0` and the delete answers 404
- **THEN** `run` exits `1` and the record remains
