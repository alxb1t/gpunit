## Purpose

A model on a rented GPU, for a person and for a local client: one command opens a gpunit session on a bundled image
and a bundled model table, and gives a chat in the terminal or an OpenAI-compatible endpoint on loopback until the
session ends.

## ADDED Requirements

### Requirement: The model table names what each model serves on

The system SHALL bundle a model table whose rows each name a model's Hugging Face repository at a pinned revision,
its served name, its vLLM arguments, the card memory it needs, the cards to try in order, and its disk; and SHALL
bundle the digest of the image every row serves on. A row SHALL be refused, naming the row and the field, when a
field is missing, the revision is not a commit hash, or the image is not a digest.

#### Scenario: the table loads
- **Key:** `serve:table:loads`
- **WHEN** the bundled table is read
- **THEN** it holds the row `qwen3-4b` for `Qwen/Qwen3-4B` at a 40-hex revision, and an image named by digest

#### Scenario: a row with a moving revision is refused
- **Key:** `serve:table:revision-pinned`
- **WHEN** a row names `revision = "main"`
- **THEN** the table is refused, naming the row and `revision`

#### Scenario: a row becomes a session's spec
- **Key:** `serve:table:row-makes-the-spec`
- **WHEN** `qwen3-4b` is served with `--ceiling 2h`
- **THEN** the session's spec names the project `serve-qwen3-4b`, the table's image, the row's cards, memory and disk,
  port `8000`, the ceiling `7200` seconds, and the model, its revision and its arguments in the pod's environment

### Requirement: Nothing is rented before the operator agrees to the price

The system SHALL print each placeable card's hourly price and the most the session can cost — the highest price times
the ceiling — and SHALL ask `rent … for at most $X? [y/N]` before any create, renting nothing unless the answer is
`y`; `--yes` SHALL skip the question.

#### Scenario: no is the default
- **Key:** `serve:price:no-by-default`
- **WHEN** the operator answers with an empty line
- **THEN** nothing is created and the command exits `1`

#### Scenario: --yes skips the question
- **Key:** `serve:price:yes-skips`
- **WHEN** `--yes` is given
- **THEN** the prices and the maximum are printed and the session opens without a question

### Requirement: A served session waits for the model, within a bound

The system SHALL keep a served session's files under `~/.local/state/gpunit/serve/<model>/`, wherever the command
runs; SHALL ask the model server for its models through the session's forwarded port, with the session's key, until it
answers, for at most 20 minutes, printing a progress line from the pod's log every 30 seconds; and SHALL refuse and
tear down at that bound.

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

### Requirement: The chat streams the model's answer in the terminal

The system SHALL read the operator's lines, send each with the conversation so far to the model's chat completions
endpoint, print the answer as it streams, keep the conversation in memory, and end the session on `/exit` or the end
of input. Thinking SHALL be off unless `--think` is given.

#### Scenario: an answer streams
- **Key:** `serve:chat:streams`
- **WHEN** the operator sends a line and the server streams an answer in parts
- **THEN** the parts are printed as they arrive, and the next request carries both the line and the answer

#### Scenario: thinking is off by default
- **Key:** `serve:chat:thinking-off`
- **WHEN** a request is sent without `--think`
- **THEN** it carries `chat_template_kwargs` with `enable_thinking` set to false

#### Scenario: the end of input ends the session
- **Key:** `serve:chat:eof-ends`
- **WHEN** the operator sends `/exit`, or the input ends
- **THEN** the session closes

### Requirement: The endpoint is served on loopback with a key of its own

With `--api`, the system SHALL print `OPENAI_BASE_URL=http://127.0.0.1:<port>/v1` and `OPENAI_API_KEY=<key>`, the key
random per session and required by the model server, and SHALL hold the session until it is interrupted or reaches
its ceiling.

#### Scenario: the endpoint's lines
- **Key:** `serve:api:prints-the-endpoint`
- **WHEN** `--api` is given and the model server answers
- **THEN** stdout holds the base URL on loopback and a key of at least 32 characters, the same key the pod was given

#### Scenario: a request without the key is refused by the server
- **Key:** `serve:api:key-required`
- **WHEN** the pod is created for `--api`
- **THEN** its environment gives the model server that key as the one it requires

### Requirement: The serve image is built on request and pinned

The serve image SHALL be built from vLLM's image named by digest, with an SSH server, `curl`, no baked host key,
telemetry off and gpunit's boot script as its entry point; SHALL be built only on a manual request naming a tag other
than `latest`; and its digest SHALL be the one the model table records.

#### Scenario: the image is built from pinned inputs
- **Key:** `serve:image:pinned-inputs`
- **WHEN** the serve image's build file is read
- **THEN** its base carries a digest, the SSH server's install deletes its host keys, and its entry point is the boot
  script

#### Scenario: only a request builds
- **Key:** `serve:image:only-a-request-builds`
- **WHEN** the serve image's workflow is read
- **THEN** a manual request is its only trigger, `latest` is refused, and the digest is written to its summary
