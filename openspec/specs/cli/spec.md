## Purpose

The one command a consumer and an operator run: its verbs, its exit codes, and what it prints where, so a script
can read its outcome without parsing its words.

## Requirements

### Requirement: The verbs and the usage exit

The system SHALL accept the verbs `up`, `status`, `down`, `ssh` and `run`, each reading `gpunit.toml` from the
working directory unless `--spec <path>` names another; and SHALL exit `2` with a usage line on an unknown verb,
a missing argument or an unreadable spec path, before any network call.

#### Scenario: an unknown verb exits 2
- **Key:** `cli:verbs:unknown-verb-exits-2`
- **WHEN** `gpunit frobnicate` runs
- **THEN** it exits `2`, prints a usage line to stderr, and makes no request

#### Scenario: run without a command exits 2
- **Key:** `cli:verbs:run-without-command-exits-2`
- **WHEN** `gpunit run` runs with nothing after `--`
- **THEN** it exits `2` and names the form `gpunit run -- <command>`

### Requirement: The exit codes say what happened

The system SHALL exit `0` when the verb did its work, `1` when it refused or failed, `2` on usage, and `3` when a
create's outcome is unknown; and SHALL print every line it writes on its own behalf to stderr, each opening with
the UTC time, so stdout belongs to the command `run` executes.

#### Scenario: a refusal exits 1 on stderr
- **Key:** `cli:exits:refusal-exits-1`
- **WHEN** `gpunit up` refuses because a pod is already recorded
- **THEN** it exits `1`, and the refusal is one stderr line opening with a UTC timestamp and the word `refused:`

#### Scenario: stdout carries only the command's output
- **Key:** `cli:exits:stdout-is-the-commands`
- **WHEN** `gpunit run -- echo hello` completes
- **THEN** stdout holds `hello` and nothing of gpunit's own

### Requirement: Status reports the record, in words or JSON

The system SHALL, on `status`, print the recorded session — the pod id, the image, the host and the port — and
SHALL print the same as one JSON object on `--json`; with no record it SHALL say so and exit `0`.

#### Scenario: status as JSON
- **Key:** `cli:status:json`
- **WHEN** `gpunit status --json` runs with a record present
- **THEN** stdout is one JSON object with the keys `id`, `image`, `host`, `port`, `status`

#### Scenario: no record
- **Key:** `cli:status:no-record`
- **WHEN** `gpunit status` runs with no `.gpunit/pod`
- **THEN** it prints that no session is recorded and exits `0`
