## Purpose

One command run against a session that exists only as long as the command does: the ports forwarded, the session
handed over in the environment, and the pod torn down on every way out.

## Requirements

### Requirement: Run hands the session over

The system SHALL, on `run -- <command>`, open the session, forward each spec'd port over one `ssh -N -L` child,
then run the command as a child with `GPUNIT_HOST`, `GPUNIT_PORT_<remote>=<local>` for each port, and
`GPUNIT_SSH` (a command line that opens a shell on the pod) in its environment; and SHALL leave the provider's
account key, `RUNPOD_API_KEY`, out of that environment.

#### Scenario: the environment names the session
- **Key:** `run:handover:env`
- **WHEN** `gpunit run -- env` runs with `ports = [8188]`
- **THEN** the command's environment holds `GPUNIT_HOST`, `GPUNIT_PORT_8188=8188` and `GPUNIT_SSH`

#### Scenario: the command gets no account key
- **Key:** `run:handover:no-account-key`
- **WHEN** `gpunit run -- env` runs with `RUNPOD_API_KEY` set
- **THEN** the command's environment holds no `RUNPOD_API_KEY`, and the provider's requests still carry the key

### Requirement: A port already answering refuses before anything is rented

The system SHALL, before any request, refuse when a spec'd local port already accepts a connection on loopback,
`127.0.0.1` or `::1`, naming the port.

#### Scenario: a busy port refuses
- **Key:** `run:ports:busy-refuses`
- **WHEN** local `8188` is listening when `gpunit run` starts
- **THEN** it refuses naming `8188`, exits `1`, and makes no request

#### Scenario: a port busy on IPv6 loopback refuses
- **Key:** `run:ports:busy-on-v6-refuses`
- **WHEN** local `8188` is listening on `::1` alone when `gpunit run` starts
- **THEN** it refuses naming `8188`, exits `1`, and makes no request

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

#### Scenario: a record gone before up still tears down this run's pod
- **Key:** `run:teardown:record-gone-before-up`
- **WHEN** a pod is recorded by an earlier `gpunit up` when `run` starts, the record is removed before `up` checks
  it, and `up` creates a pod
- **THEN** the command's exit deletes the pod this run created, and `run` exits with the command's code

#### Scenario: a failed teardown is exit 1
- **Key:** `run:teardown:failure-is-1`
- **WHEN** the command exits `0` and the delete answers 404
- **THEN** `run` exits `1` and the record remains

### Requirement: A dead tunnel is reopened

The system SHALL, while the command runs, reopen the tunnel when its `ssh` child exits and no other process holds a
spec'd local port, and SHALL log each reopening; SHALL wait before each reopening, 1 second at first and doubling
to 30; and SHALL wait 1 second again once a tunnel has lived 30 seconds before it exits. A spec'd local port that
accepts a connection on `127.0.0.1` or `::1` when the tunnel is about to open, or after its child exits, SHALL end
the command, refuse naming the port, tear the session down, and make `run` exit `1`.

#### Scenario: the tunnel comes back
- **Key:** `run:tunnel:reopened`
- **WHEN** the tunnel child exits while the command runs, and its local port is free
- **THEN** a new tunnel child is started and stderr says so

#### Scenario: a tunnel that keeps dying backs off
- **Key:** `run:tunnel:backoff`
- **WHEN** each tunnel exits at once after it opens
- **THEN** the waits before the reopenings are 1, 2, 4, 8, 16, 30 and 30 seconds; and after a tunnel that lived 30 seconds, the wait is 1 second again

#### Scenario: a taken port ends the run
- **Key:** `run:tunnel:taken-port-refuses`
- **WHEN** the tunnel child exits while the command runs, and another process listens on its local port
- **THEN** no new tunnel child is started, the command is ended, stderr names the port, the pod is deleted, and
  `run` exits `1`
