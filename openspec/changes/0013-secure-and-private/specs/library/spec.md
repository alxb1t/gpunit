## MODIFIED Requirements

### Requirement: The tunnel stays open while the block runs

The session SHALL forward each spec'd port over one `ssh -N -L` child, as one forward bound to `127.0.0.1` and,
where `::1` binds, one bound to `::1`; SHALL reopen it when it exits and no other process holds a spec'd local port,
waiting 1 second at first and doubling to 30, reset after a tunnel lived 30 seconds; SHALL log each reopening; and
SHALL stop watching it before the teardown. A spec'd local port that accepts a connection on `127.0.0.1` or `::1`
when the tunnel is about to open, or after its child exits, SHALL end the block with `gpunit.Refused` naming the
port, and the session SHALL be torn down; a block that catches that `Refused` and goes on SHALL still be ended by
`SIGINT`, `SIGTERM` or `SIGHUP`.

#### Scenario: a dead tunnel is reopened
- **Key:** `library:tunnel:reopened`
- **WHEN** the tunnel child exits while the block runs, and its local port is free
- **THEN** a new tunnel child is started and the log says so

#### Scenario: a taken port ends the block
- **Key:** `library:tunnel:taken-port-refuses`
- **WHEN** the tunnel child exits while the block runs, and another process listens on its local port
- **THEN** no new tunnel child is started, `Refused` naming the port is raised in the block, and the pod is deleted

#### Scenario: a port taken while the pod came up refuses
- **Key:** `library:tunnel:taken-before-open-refuses`
- **WHEN** a spec'd local port was free when the session began opening, and answers once the pod is up
- **THEN** no tunnel child is started, `Refused` naming the port is raised, and the pod is deleted

#### Scenario: each loopback family is its own forward
- **Key:** `library:tunnel:each-family-forwarded`
- **WHEN** the tunnel opens for a spec'd port
- **THEN** its `ssh` argv forwards it as `-L127.0.0.1:<local>:localhost:<remote>`, plus
  `-L[::1]:<local>:localhost:<remote>` where `::1` binds, and in no forward without a bind address

#### Scenario: a swallowed refusal leaves the signals live
- **Key:** `library:tunnel:swallowed-refusal-keeps-signals`
- **WHEN** the block catches the `Refused` of a taken port and goes on, and `SIGINT` arrives
- **THEN** `Interrupted` is raised in the block, and the pod is deleted
