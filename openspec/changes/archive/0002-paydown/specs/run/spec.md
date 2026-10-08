## MODIFIED Requirements

### Requirement: Run tears down on every exit

The system SHALL tear the session down when the command exits, on `SIGINT`, `SIGTERM` and `SIGHUP`, and after a
lost create; SHALL ignore a second interrupt while tearing down; SHALL kill the tunnel first; and SHALL exit with
the command's code when the teardown succeeded — `128 + n` for a command killed by signal `n` — `1` when it did
not, even after a signal, `3` after a lost create.

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

#### Scenario: a failed teardown is exit 1
- **Key:** `run:teardown:failure-is-1`
- **WHEN** the command exits `0` and the delete answers 404
- **THEN** `run` exits `1` and the record remains

### Requirement: A dead tunnel is reopened

The system SHALL, while the command runs, reopen the tunnel when its `ssh` child exits, and SHALL log each
reopening; SHALL wait before each reopening, 1 second at first and doubling to 30; and SHALL wait 1 second again
once a tunnel has lived 30 seconds before it exits.

#### Scenario: the tunnel comes back
- **Key:** `run:tunnel:reopened`
- **WHEN** the tunnel child exits while the command runs
- **THEN** a new tunnel child is started and stderr says so

#### Scenario: a tunnel that keeps dying backs off
- **Key:** `run:tunnel:backoff`
- **WHEN** each tunnel exits at once after it opens
- **THEN** the waits before the reopenings are 1, 2, 4, 8, 16, 30 and 30 seconds; and after a tunnel that lived 30 seconds, the wait is 1 second again
