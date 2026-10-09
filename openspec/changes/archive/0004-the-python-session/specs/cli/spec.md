## ADDED Requirements

### Requirement: A closed stderr ends no teardown

The system SHALL keep running when a line it writes to stderr finds the stream closed, so a pipe that dies during
the teardown never cuts it short, and the exit code is the one the teardown earns.

#### Scenario: a dead pipe during the teardown
- **Key:** `cli:exits:closed-stderr`
- **WHEN** `gpunit run -- true` runs with its stderr a pipe whose reader has exited
- **THEN** the pod is deleted and `run` exits `0`
