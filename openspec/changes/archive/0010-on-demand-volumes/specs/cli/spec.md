## MODIFIED Requirements

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
