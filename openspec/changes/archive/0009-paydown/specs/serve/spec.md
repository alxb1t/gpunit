## MODIFIED Requirements

### Requirement: A served session waits for the model, within a bound

The system SHALL keep a served session's files under `~/.local/state/gpunit/serve/<model>/`, wherever the command
runs; SHALL ask the model server for its models through the session's forwarded port, with the session's key, until it
answers, for at most 20 minutes, printing a progress line from the pod's log every 30 seconds; and SHALL refuse and
tear down at that bound. Each poll SHALL read the pod's status from the provider; two polls in a row reading `EXITED`,
`ERROR` or `TERMINATED` SHALL end the wait with the refusal `the pod stopped while the model loaded`, and the session
SHALL close. Every 30 seconds the system SHALL read the pod's log since the create and keep it in `pod.log` under the
model's directory, at mode `0600`, replaced only by a read at least as long; each session SHALL start without the last
session's file. Before the dead-pod refusal the system SHALL print the kept log's last 30 lines and name the file.

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

### Requirement: The endpoint is served on loopback with a key of its own

With `--api`, the system SHALL print `OPENAI_BASE_URL=http://127.0.0.1:<port>/v1` and `OPENAI_API_KEY=<key>`, the key
random per session and required by the model server, and SHALL hold the session until it is interrupted or reaches
its ceiling. Each poll of the hold SHALL read the pod's status and keep the pod's log as the wait does; two polls in a
row reading `EXITED`, `ERROR` or `TERMINATED` SHALL end the hold with the refusal `the pod stopped while serving`,
printed after the kept log's last 30 lines and the file's name, and the session SHALL close.

#### Scenario: the endpoint's lines
- **Key:** `serve:api:prints-the-endpoint`
- **WHEN** `--api` is given and the model server answers
- **THEN** stdout holds the base URL on loopback and a key of at least 32 characters, the same key the pod was given

#### Scenario: a request without the key is refused by the server
- **Key:** `serve:api:key-required`
- **WHEN** the pod is created for `--api`
- **THEN** its environment gives the model server that key as the one it requires

#### Scenario: a dead pod ends the hold
- **Key:** `serve:api:dead-pod-ends-the-hold`
- **WHEN** the model server has answered, and the pod then reads `EXITED` on two holds' polls in a row
- **THEN** the command refuses with `the pod stopped while serving`, prints the kept log's last lines and the file's path, the pod is deleted, and the command exits `1`
