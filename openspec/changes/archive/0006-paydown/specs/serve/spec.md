## MODIFIED Requirements

### Requirement: The model table names what each model serves on

The system SHALL bundle a model table whose rows each name a model's Hugging Face repository at a pinned revision, its
served name, its vLLM arguments, the card memory it needs, the cards to try in order, and its disk; and SHALL bundle
the digest of the image every row serves on. A row SHALL be refused, naming the row and the field, when a field is
missing, the revision is not a commit hash, or the image is not a digest.

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
- **THEN** the session's spec names the project `serve-qwen3-4b`, the table's image, the row's cards, memory and
  disk, its remote port `8000` forwarded to the local port it was given, the ceiling `7200` seconds, and the model, its
  revision and its arguments in the pod's environment

### Requirement: Nothing is rented before the operator agrees to the price

The system SHALL print each placeable card's hourly price and the most the session can cost — the highest price times
the ceiling plus the wait for SSH, since the pod bills while it pulls and boot arms the ceiling after — and SHALL ask
`rent … for at most $X? [y/N]` before any create, renting nothing unless the answer is `y`; `--yes` SHALL skip the
question.

#### Scenario: no is the default
- **Key:** `serve:price:no-by-default`
- **WHEN** the operator answers with an empty line
- **THEN** nothing is created and the command exits `1`

#### Scenario: --yes skips the question
- **Key:** `serve:price:yes-skips`
- **WHEN** `--yes` is given
- **THEN** the prices and the maximum are printed and the session opens without a question

#### Scenario: the maximum covers the wait for SSH
- **Key:** `serve:price:covers-the-wait`
- **WHEN** `qwen3-4b` is served with `--ceiling 30m` on a card at `$0.69/h`
- **THEN** the question names at most `$0.58`, the price for the 1800 s ceiling plus the 1200 s wait for SSH

#### Scenario: an interrupt at the question rents nothing
- **Key:** `serve:price:interrupt-is-no`
- **WHEN** the operator presses Ctrl-C at the question
- **THEN** nothing is created, stderr says `not rented` without a traceback, and the command exits `130`

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

#### Scenario: a busy local port is not a clash
- **Key:** `serve:wait:busy-local-port-is-skipped`
- **WHEN** local port `8000` already answers
- **THEN** the forward uses another free local port before the price is asked, and the endpoint names it

### Requirement: The chat streams the model's answer in the terminal

The system SHALL read the operator's lines, send each with the conversation so far to the model's chat completions
endpoint, print the answer as it streams, keep the conversation in memory, and end the session on `/exit`, the end of
input, or a request that cannot connect, which says the server stopped answering. Thinking SHALL be off unless
`--think` is given.

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

#### Scenario: a stopped server ends the chat
- **Key:** `serve:chat:stopped-server-ends`
- **WHEN** a request cannot connect, as when the pod's ceiling has stopped it
- **THEN** the chat ends, the session closes, and stderr says the server stopped answering

#### Scenario: a server error drops the turn
- **Key:** `serve:chat:server-error-drops-the-turn`
- **WHEN** a request is answered with an HTTP 500
- **THEN** the turn is dropped, stderr says the model did not answer, and the chat goes on
