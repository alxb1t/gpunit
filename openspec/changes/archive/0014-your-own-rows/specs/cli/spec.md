## MODIFIED Requirements

### Requirement: The verbs and the usage exit

The system SHALL accept the verbs `up`, `status`, `down`, `ssh` and `run`, each reading `gpunit.toml` from the
working directory unless `--spec <path>` names another, `volume up` and `volume down`, which read the spec the same
way, `serve <model>`, which reads the bundled model table and the operator's user file, and `spend`, which reads the
provider's billing and the ledger; `down --serve <model>` SHALL tear down the session `serve` left for that model;
`volume up --serve <model> --ceiling <duration>` and `volume down --serve <model>` SHALL make and delete the window
volume of that model's row; `serve`, `down --serve`, `volume up --serve` and `volume down --serve` SHALL take
`--models <path>`, naming the user file; and the system SHALL exit `2` with a usage line on an unknown verb, a missing
argument, an unreadable spec path, `--models` without a model, or an unknown model, whose line names each row with its
source, `bundled` or the user file's path, before any network call.

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
- **THEN** it exits `2`, names each model the rows hold with its source, as `qwen3-4b (bundled)`, and makes no
  request

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

#### Scenario: --models without a model exits 2
- **Key:** `cli:verbs:models-without-serve-exits-2`
- **WHEN** `gpunit down --models rows.toml` or `gpunit volume up --models rows.toml` runs with no `--serve`
- **THEN** it exits `2`, names `--serve`, and makes no request

#### Scenario: each verb that names a model reads the given file
- **Key:** `cli:verbs:models-on-each-serve-verb`
- **WHEN** `rows.toml` holds the row `granite-4.0-micro`, and `serve`, `down --serve`, `volume up --serve` and
  `volume down --serve` each name it with `--models rows.toml`
- **THEN** each finds the row in `rows.toml`
