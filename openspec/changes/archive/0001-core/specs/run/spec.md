## Purpose

One command run against a session that exists only as long as the command does: the ports forwarded, the session
handed over in the environment, and the pod torn down on every way out.

## ADDED Requirements

### Requirement: Run hands the session over

The system SHALL, on `run -- <command>`, open the session, forward each spec'd port over one `ssh -N -L` child,
then run the command as a child with `GPUNIT_HOST`, `GPUNIT_PORT_<remote>=<local>` for each port, and
`GPUNIT_SSH` (a command line that opens a shell on the pod) in its environment.

#### Scenario: the environment names the session
- **Key:** `run:handover:env`
- **WHEN** `gpunit run -- env` runs with `ports = [8188]`
- **THEN** the command's environment holds `GPUNIT_HOST`, `GPUNIT_PORT_8188=8188` and `GPUNIT_SSH`

### Requirement: A port already answering refuses before anything is rented

The system SHALL, before any request, refuse when a spec'd local port already accepts a connection on loopback,
naming the port.

#### Scenario: a busy port refuses
- **Key:** `run:ports:busy-refuses`
- **WHEN** local `8188` is listening when `gpunit run` starts
- **THEN** it refuses naming `8188`, exits `1`, and makes no request

### Requirement: Run tears down on every exit

The system SHALL tear the session down when the command exits, on `SIGINT`, `SIGTERM` and `SIGHUP`, and after a
lost create; SHALL ignore a second interrupt while tearing down; SHALL kill the tunnel first; and SHALL exit with
the command's code when the teardown succeeded, `1` when it did not, even after a signal, `3` after a lost create.

#### Scenario: the command's exit tears down
- **Key:** `run:teardown:on-exit`
- **WHEN** the command exits `0`
- **THEN** the pod is deleted and `run` exits `0`

#### Scenario: the command's failure is passed through
- **Key:** `run:teardown:code-passed`
- **WHEN** the command exits `7` and the teardown succeeds
- **THEN** `run` exits `7`

#### Scenario: an interrupt tears down once
- **Key:** `run:teardown:interrupt`
- **WHEN** `SIGINT` arrives during the command, and again during the teardown
- **THEN** the teardown runs to its end once and `run` exits `130`

#### Scenario: a failed teardown is exit 1
- **Key:** `run:teardown:failure-is-1`
- **WHEN** the command exits `0` and the delete answers 404
- **THEN** `run` exits `1` and the record remains

### Requirement: A dead tunnel is reopened

The system SHALL, while the command runs, reopen the tunnel when its `ssh` child exits, and SHALL log each reopening.

#### Scenario: the tunnel comes back
- **Key:** `run:tunnel:reopened`
- **WHEN** the tunnel child exits while the command runs
- **THEN** a new tunnel child is started and stderr says so
