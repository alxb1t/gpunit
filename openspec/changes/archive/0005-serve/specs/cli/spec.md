## MODIFIED Requirements

### Requirement: The verbs and the usage exit

The system SHALL accept the verbs `up`, `status`, `down`, `ssh` and `run`, each reading `gpunit.toml` from the
working directory unless `--spec <path>` names another, and `serve <model>`, which reads the bundled model table;
`down --serve <model>` SHALL tear down the session `serve` left for that model; and SHALL exit `2` with a
usage line on an unknown verb, a missing argument or an unreadable spec path, before any network call.

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
