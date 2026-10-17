## MODIFIED Requirements

### Requirement: The exit codes say what happened

The system SHALL exit `0` when the verb did its work, `1` when it refused or failed, `2` on usage, `3` when a create's
outcome is unknown, and `128 + n` when signal `n` ended a `run` or `serve`, `130` when Ctrl-C ended `volume down`'s
sweep; and SHALL print every line it writes on its own behalf to stderr, each opening with the UTC time, so stdout
belongs to the command `run` executes.

#### Scenario: a refusal exits 1 on stderr
- **Key:** `cli:exits:refusal-exits-1`
- **WHEN** `gpunit up` refuses because a pod is already recorded
- **THEN** it exits `1`, and the refusal is one stderr line opening with a UTC timestamp and the word `refused:`

#### Scenario: stdout carries only the command's output
- **Key:** `cli:exits:stdout-is-the-commands`
- **WHEN** `gpunit run -- echo hello` completes
- **THEN** stdout holds `hello` and nothing of gpunit's own

#### Scenario: a signal ends serve at 128 + n
- **Key:** `cli:exits:serve-signal-is-128-plus-n`
- **WHEN** `SIGTERM` arrives while `gpunit serve --api` holds its endpoint
- **THEN** the session is torn down and `serve` exits `143`
