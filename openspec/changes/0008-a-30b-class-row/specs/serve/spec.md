## MODIFIED Requirements

### Requirement: The model table names what each model serves on

The system SHALL bundle a model table whose rows each name a model's Hugging Face repository at a pinned revision, its
served name, its vLLM arguments, the card memory it needs, the cards to try in order, and its disk; and SHALL bundle
the digest of the image every row serves on. A row SHALL be refused, naming the row and the field, when a field is
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
  serves the language model alone, and lists `NVIDIA A40`, `NVIDIA RTX A6000`, `NVIDIA L40`,
  `NVIDIA RTX 6000 Ada Generation` and `NVIDIA L40S`, in that order

## ADDED Requirements

### Requirement: A row's tool-calling is proved by a check

The repository SHALL hold a check that sends one chat request carrying a function schema to a served model, and SHALL
pass only when the answer's finish reason is `tool_calls` and its first call names the function with arguments that
parse; it SHALL read the key from the environment and never from its arguments, and exit `1` naming what it found
otherwise.

#### Scenario: a tool call passes
- **Key:** `serve:tools:call-passes`
- **WHEN** the server answers with `finish_reason` `tool_calls` and a call to `get_weather` with `{"city": "Paris"}`
- **THEN** the check prints the call and exits `0`

#### Scenario: plain text fails
- **Key:** `serve:tools:plain-text-fails`
- **WHEN** the server answers with text and `finish_reason` `stop`
- **THEN** the check exits `1` and says the answer held no tool call

#### Scenario: unparseable arguments fail
- **Key:** `serve:tools:bad-arguments-fail`
- **WHEN** the server answers with a call whose arguments are not JSON
- **THEN** the check exits `1` and says so

#### Scenario: the key is not an argument
- **Key:** `serve:tools:key-from-the-environment`
- **WHEN** the check runs
- **THEN** it sends `OPENAI_API_KEY` as the bearer token and accepts none on its command line
