## MODIFIED Requirements

### Requirement: The tunnel stays open while the block runs

The session SHALL forward each spec'd port over one `ssh -N -L` child, SHALL reopen it when it exits and no other
process holds a spec'd local port, waiting 1 second at first and doubling to 30, reset after a tunnel lived 30
seconds, SHALL log each reopening, and SHALL stop watching it before the teardown. A spec'd local port that accepts a
connection on `127.0.0.1` or `::1` when the tunnel is about to open, or after its child exits, SHALL end the block
with `gpunit.Refused` naming the port, and the session SHALL be torn down.

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
