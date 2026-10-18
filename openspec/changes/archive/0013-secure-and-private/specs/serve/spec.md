## MODIFIED Requirements

### Requirement: The model table names what each model serves on

The system SHALL bundle a model table whose rows each name a model's Hugging Face repository at a pinned revision, its
served name, its vLLM arguments, the card memory it needs, the cards to try in order, and its disk; and SHALL bundle
the digest of the image every row serves on. Every row's vLLM arguments SHALL turn request logging off explicitly, so
no prompt reaches the pod's log. A row SHALL be refused, naming the row and the field, when a field is
missing, the revision is not a commit hash, or the image is not a digest.

#### Scenario: the table loads
- **Key:** `serve:table:loads`
- **WHEN** the bundled table is read
- **THEN** it holds the rows `qwen3-4b` for `Qwen/Qwen3-4B` and `qwen3.8-27b` for `Qwen/Qwen3.8-27B-FP8`, each at a 40-hex
  revision, and an image named by digest

#### Scenario: a row with a moving revision is refused
- **Key:** `serve:table:revision-pinned`
- **WHEN** a row names `revision = "main"`
- **THEN** the table is refused, naming the row and `revision`

#### Scenario: a row becomes a session's spec
- **Key:** `serve:table:row-makes-the-spec`
- **WHEN** `qwen3-4b` is served with `--ceiling 2h`
- **THEN** the session's spec names the project `serve-qwen3-4b`, the table's image, the row's cards, memory and
  disk, its remote port `8000` forwarded to the local port it was given, the ceiling `7200` seconds, and the model, its
  revision and its arguments in the pod's environment

#### Scenario: the larger row asks for a 48 GB card and its family's parser
- **Key:** `serve:table:larger-row`
- **WHEN** the row `qwen3.8-27b` is read
- **THEN** it needs 48 GB of card, names `qwen3_coder` as its tool-call parser and `qwen3` as its reasoning parser,
  serves the language model alone, caps its concurrent sequences under the 192 its Mamba cache holds, and lists
  `NVIDIA A40`, `NVIDIA RTX A6000`, `NVIDIA L40`,
  `NVIDIA RTX 6000 Ada Generation` and `NVIDIA L40S`, in that order

#### Scenario: no row logs requests
- **Key:** `serve:table:request-logging-off`
- **WHEN** the bundled table is read
- **THEN** every row's arguments hold `--no-enable-log-requests`, and none holds `--enable-log-requests` or
  `--enable-log-outputs`

### Requirement: A served session waits for the model, within a bound

The system SHALL keep a served session's files under `~/.local/state/gpunit/serve/<model>/`, wherever the command
runs; SHALL ask the model server for its models through the session's forwarded port, with the session's key, until it
answers, for at most 20 minutes, printing a progress line from the pod's log every 30 seconds; and SHALL refuse and
tear down at that bound. Each poll SHALL read the pod's status from the provider; two polls in a row reading `EXITED`,
`ERROR` or `TERMINATED` SHALL end the wait with the refusal `the pod stopped while the model loaded`, and the session
SHALL close. Every 30 seconds the system SHALL read the pod's log since the create and keep it in `pod.log` under the
model's directory, at mode `0600`, replaced only by a read at least as long; each session SHALL start without the last
session's file. Before the dead-pod refusal the system SHALL print the kept log's last 30 lines and name the file.
Every line of the pod's log the system prints SHALL first lose its control characters, U+0000 to U+001F and U+007F to
U+009F; `pod.log` SHALL keep each line as read.

#### Scenario: the server is awaited
- **Key:** `serve:wait:awaited`
- **WHEN** the model server answers after three polls
- **THEN** the chat or the endpoint opens only after it answers

#### Scenario: the bound tears down
- **Key:** `serve:wait:bound-tears-down`
- **WHEN** the model server never answers within the bound
- **THEN** the command refuses naming the bound, and the session closes

#### Scenario: the state is the model's, not the directory's
- **Key:** `serve:wait:state-per-model`
- **WHEN** `gpunit serve qwen3-4b` runs from any directory
- **THEN** its session files are under `~/.local/state/gpunit/serve/qwen3-4b/.gpunit/`

#### Scenario: a busy local port is not a clash
- **Key:** `serve:wait:busy-local-port-is-skipped`
- **WHEN** local port `8000` already answers
- **THEN** the forward uses another free local port before the price is asked, and the endpoint names it

#### Scenario: a dead pod ends the wait
- **Key:** `serve:wait:dead-pod-ends-the-wait`
- **WHEN** the model server never answers, and the pod reads `RUNNING` and then `EXITED` on every later poll
- **THEN** the command refuses with `the pod stopped while the model loaded` well before the bound, prints the kept log's last lines and the file's path, the pod is deleted, and the command exits `1`

#### Scenario: a running pod keeps the wait
- **Key:** `serve:wait:running-pod-waits`
- **WHEN** the pod reads `RUNNING` on every poll, or `EXITED` once between two `RUNNING` reads, and the model server answers on the fifth poll
- **THEN** the chat or the endpoint opens, and nothing refuses

#### Scenario: the log is kept
- **Key:** `serve:wait:log-kept`
- **WHEN** the wait reads the pod's log since the create
- **THEN** `~/.local/state/gpunit/serve/<model>/pod.log` holds those lines at mode `0600`, a shorter later read leaves it as it was, and the next session starts without it

#### Scenario: printed log lines are cleaned
- **Key:** `serve:wait:log-lines-cleaned`
- **WHEN** the pod's log holds the line `\x1b]0;owned\x07loading\x1b[2J 50%`, and the wait prints a progress line and
  then the dead-pod refusal's kept lines
- **THEN** each printed line holds `]0;ownedloading[2J 50%` and no control character, and `pod.log` holds the line as
  read
