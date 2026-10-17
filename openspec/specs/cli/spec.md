## Purpose

The one command a consumer and an operator run: its verbs, its exit codes, and what it prints where, so a script
can read its outcome without parsing its words.

## Requirements

### Requirement: The verbs and the usage exit

The system SHALL accept the verbs `up`, `status`, `down`, `ssh` and `run`, each reading `gpunit.toml` from the
working directory unless `--spec <path>` names another, `volume up` and `volume down`, which read the spec the same
way, `serve <model>`, which reads the bundled model table, and `spend`, which reads the provider's billing and the
ledger; `down --serve <model>` SHALL tear down the session `serve` left for that model; `volume up --serve <model>
--ceiling <duration>` and `volume down --serve <model>` SHALL make and delete the window volume of that model's row; and
the system SHALL exit `2` with a usage line on an unknown verb, a missing argument or an unreadable spec path, before
any network call.

#### Scenario: an unknown verb exits 2
- **Key:** `cli:verbs:unknown-verb-exits-2`
- **WHEN** `gpunit frobnicate` runs
- **THEN** it exits `2`, prints a usage line to stderr, and makes no request

#### Scenario: run without a command exits 2
- **Key:** `cli:verbs:run-without-command-exits-2`
- **WHEN** `gpunit run` runs with nothing after `--`
- **THEN** it exits `2` and names the form `gpunit run -- <command>`

#### Scenario: serve without a ceiling exits 2
- **Key:** `cli:verbs:serve-without-ceiling-exits-2`
- **WHEN** `gpunit serve qwen3-4b` runs with no `--ceiling`
- **THEN** it exits `2`, names `--ceiling`, and makes no request

#### Scenario: an unknown model exits 2
- **Key:** `cli:verbs:serve-unknown-model-exits-2`
- **WHEN** `gpunit serve no-such-model --ceiling 1h` runs
- **THEN** it exits `2`, names the models the table holds, and makes no request

#### Scenario: spend with a bad window exits 2
- **Key:** `cli:verbs:spend-bad-days-exits-2`
- **WHEN** `gpunit spend --days 0` runs
- **THEN** it exits `2`, names `--days`, and makes no request

#### Scenario: volume without an action exits 2
- **Key:** `cli:verbs:volume-without-action-exits-2`
- **WHEN** `gpunit volume` runs with neither `up` nor `down`
- **THEN** it exits `2`, names `volume up` and `volume down`, and makes no request

#### Scenario: a model's volume without a ceiling exits 2
- **Key:** `cli:verbs:volume-serve-without-ceiling-exits-2`
- **WHEN** `gpunit volume up --serve qwen3-4b` runs with no `--ceiling`
- **THEN** it exits `2`, names `--ceiling`, and makes no request

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

### Requirement: A closed stderr ends no teardown

The system SHALL keep running when a line it writes to stderr finds the stream closed, so a pipe that dies during
the teardown never cuts it short, and the exit code is the one the teardown earns.

#### Scenario: a dead pipe during the teardown
- **Key:** `cli:exits:closed-stderr`
- **WHEN** `gpunit run -- true` runs with its stderr a pipe whose reader has exited
- **THEN** the pod is deleted and `run` exits `0`
