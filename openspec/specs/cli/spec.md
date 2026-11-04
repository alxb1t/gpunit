## Purpose

The one command a consumer and an operator run: its verbs, its exit codes, and what it prints where, so a script
can read its outcome without parsing its words.

## Requirements

### Requirement: The verbs and the usage exit

The system SHALL accept the verbs `up`, `status`, `down`, `ssh` and `run`, each reading `gpunit.toml` from the
working directory unless `--spec <path>` names another, `volume up` and `volume down`, which read the spec the same
way, `serve <model>`, which reads the bundled model table and the operator's user file, and `spend`, which reads the
provider's billing and the ledger; `down --serve <model>` SHALL tear down the session `serve` left for that model;
`volume up --serve <model> --ceiling <duration>` and `volume down --serve <model>` SHALL make and delete the window
volume of that model's row; `serve`, `down --serve`, `volume up --serve` and `volume down --serve` SHALL take
`--models <path>`, naming the user file; `up`, `run`, `serve` and `volume up` SHALL take `--stock-wait <duration>`,
in place of the spec's `stock_wait`; and the system SHALL exit `2` with a usage line on an unknown verb, a missing
argument, an unreadable spec path, a `--stock-wait` that is no duration, `--models` without a
model, or an unknown model, whose line names each row with its
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

#### Scenario: a --stock-wait that is no duration exits 2
- **Key:** `cli:verbs:stock-wait-not-a-duration-exits-2`
- **WHEN** `gpunit up`, `gpunit run`, `gpunit serve qwen3-4b --ceiling 1h` or `gpunit volume up` runs with
  `--stock-wait soon`
- **THEN** it exits `2`, names `--stock-wait`, and makes no request

#### Scenario: each verb that names a model reads the given file
- **Key:** `cli:verbs:models-on-each-serve-verb`
- **WHEN** `rows.toml` holds the row `granite-4.0-micro`, and `serve`, `down --serve`, `volume up --serve` and
  `volume down --serve` each name it with `--models rows.toml`
- **THEN** each finds the row in `rows.toml`

### Requirement: The exit codes say what happened

The system SHALL exit `0` when the verb did its work, `1` when it refused or failed for any reason below, `2` on usage,
`3` when a create's outcome is unknown, `4` when no card had capacity — none in stock for `volume up`, every create
refused for a session — `5` when no card of `gpus`, or of `serve`'s row, meets `vram_gb` and `max_hourly`, and
`128 + n` when signal `n` ended a `run`, a `serve` or a wait for stock, `130` when Ctrl-C ended `volume down`'s sweep or
`volume up`'s price question; and SHALL print every line it writes on its own behalf to stderr, each opening with the
UTC time, so stdout belongs to the command `run` executes.

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

#### Scenario: no capacity exits 4
- **Key:** `cli:exits:no-capacity-exits-4`
- **WHEN** every create of `gpunit up` answers 400
- **THEN** it exits `4`, and the refusal is a `refused:` line

#### Scenario: no card that fits exits 5
- **Key:** `cli:exits:no-fit-exits-5`
- **WHEN** every card of `gpus` costs more than `max_hourly`
- **THEN** `gpunit up` exits `5` after a `skipped:` line per card, and makes no create

#### Scenario: serve with no card that fits exits 5
- **Key:** `cli:exits:serve-no-fit-exits-5`
- **WHEN** `gpunit serve qwen3-4b --ceiling 1h --max-hourly 0.01` runs, and every card of the row costs more
- **THEN** it exits `5` on a `refused:` line, asks no price, and makes no create

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

### Requirement: The refusal's lines are a contract

The system SHALL write these lines in these forms, after the UTC time, so a caller may parse them: a refusal as
`refused: <reason>`; a card under the floor as `skipped: <card> has <n> GB, under <vram_gb>`; a card over the price as
`skipped: <card> costs $<hourly>/h, over <max_hourly>`; and each attempt of a wait for stock as `no capacity: attempt
<n>; next in 60s, waiting until <UTC>`.

#### Scenario: the skipped lines name the card and the figure
- **Key:** `cli:lines:skipped-forms`
- **WHEN** `gpus` names a card of 24 GB under `vram_gb = 48`, and a card at $2.59/h over `max_hourly = 0.9`
- **THEN** stderr holds `skipped: <first> has 24 GB, under 48` and `skipped: <second> costs $2.59/h, over 0.9`

#### Scenario: each attempt is one line
- **Key:** `cli:lines:attempt-form`
- **WHEN** a wait for stock makes its second attempt
- **THEN** stderr holds `no capacity: attempt 2; next in 60s, waiting until <UTC>`, the UTC its end
