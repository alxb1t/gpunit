## MODIFIED Requirements

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
