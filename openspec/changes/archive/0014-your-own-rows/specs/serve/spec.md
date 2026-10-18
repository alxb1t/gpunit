## ADDED Requirements

### Requirement: The operator's own rows come from one user file

The system SHALL read one user file of model rows: the file `--models <path>` names; else the file `GPUNIT_MODELS`
names; else `$XDG_CONFIG_HOME/gpunit/models.toml`, with `~/.config` when `XDG_CONFIG_HOME` is unset, empty or not an
absolute path. Only the first that is set SHALL be read; the others SHALL NOT be merged with it. A file named by
`--models` or `GPUNIT_MODELS` that cannot be read SHALL be refused; an absent default file SHALL mean no user rows.
The system SHALL serve the user file's rows and the bundled rows; a user row of a bundled row's name SHALL replace it,
and the system SHALL say so in one stderr line naming the file and the replaced rows. A user row SHALL pass the checks a
bundled row passes, naming the file, the row and the field on a fault; the user file SHALL hold `models` rows alone,
every row served on the bundled image, and any other top-level key SHALL be refused.

#### Scenario: the given file comes first
- **Key:** `serve:rows:models-flag-first`
- **WHEN** a file is given with `--models`, `GPUNIT_MODELS` names a second, and the default path holds a third
- **THEN** only the given file's rows join the bundled rows

#### Scenario: the environment comes before the default
- **Key:** `serve:rows:env-before-xdg`
- **WHEN** no file is given, `GPUNIT_MODELS` names a file, and the default path holds another
- **THEN** only the file `GPUNIT_MODELS` names is read

#### Scenario: the default follows XDG
- **Key:** `serve:rows:xdg-default`
- **WHEN** neither `--models` nor `GPUNIT_MODELS` is set, and `XDG_CONFIG_HOME` is `/cfg`, then unset
- **THEN** the rows come from `/cfg/gpunit/models.toml`, then from `~/.config/gpunit/models.toml`

#### Scenario: no user file, the bundled rows alone
- **Key:** `serve:rows:no-file-bundled-only`
- **WHEN** neither `--models` nor `GPUNIT_MODELS` is set, and the default path holds no file
- **THEN** the rows are the bundled rows, and no line is printed

#### Scenario: a named file that cannot be read is refused
- **Key:** `serve:rows:named-file-missing-refused`
- **WHEN** `GPUNIT_MODELS` names a file that does not exist
- **THEN** the command refuses naming the path, exits `1`, and makes no request

#### Scenario: the user rows join the bundled rows
- **Key:** `serve:rows:merged`
- **WHEN** the user file holds the row `granite-4.0-micro`
- **THEN** the rows are `granite-4.0-micro`, `qwen3-4b` and `qwen3.8-27b`, each on the bundled image, and
  `granite-4.0-micro`'s source is the file's path

#### Scenario: a user row replaces the bundled row of its name
- **Key:** `serve:rows:same-name-replaces`
- **WHEN** the user file holds a row named `qwen3-4b`
- **THEN** `serve qwen3-4b` serves the user row, and stderr holds one line naming the file and `qwen3-4b`

#### Scenario: a user row is checked as a bundled row is
- **Key:** `serve:rows:checked-as-bundled`
- **WHEN** a user row names `revision = "main"`, or lacks `disk_gb`, or holds an argument with a space
- **THEN** the command refuses naming the file, the row and the field, and exits `1`

#### Scenario: a user file naming an image is refused
- **Key:** `serve:rows:image-refused`
- **WHEN** the user file holds a top-level `image`
- **THEN** the command refuses naming the file and `image`, and exits `1`

#### Scenario: a row turning request logging on is refused
- **Key:** `serve:rows:logging-on-refused`
- **WHEN** a row's arguments hold `--enable-log-requests`
- **THEN** the command refuses naming the row and `args`, and exits `1`

## MODIFIED Requirements

### Requirement: The model table names what each model serves on

The system SHALL bundle a model table whose rows each name a model's Hugging Face repository at a pinned revision, its
served name, its vLLM arguments, the card memory it needs, the cards to try in order, and its disk; and SHALL bundle
the digest of the image every row serves on. No row's vLLM arguments SHALL turn request logging on: a row holding
`--enable-log-requests` SHALL be refused, and the image's launch script turns it off for every row. A row SHALL be
refused, naming the row and the field, when a field is missing, the revision is not a commit hash, or the image is not
a digest.

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
- **THEN** no row's arguments hold `--enable-log-requests` or `--enable-log-outputs`

### Requirement: The serve image is built on request and pinned

The serve image SHALL be built from vLLM's image named by digest, with an SSH server, `ca-certificates`, no baked host
key, telemetry off, gpunit's boot script as its entry point and gpunit's launch script as its command; SHALL be built
only on a manual request naming a tag other than `latest`; and its digest SHALL be the one the model table records.
The launch script SHALL set `DO_NOT_TRACK`, `HF_HUB_DISABLE_TELEMETRY` and `VLLM_NO_USAGE_STATS` to `1` and pass
`--no-enable-log-requests` after the row's arguments, whatever the pod's environment and the row hold.

#### Scenario: the image is built from pinned inputs
- **Key:** `serve:image:pinned-inputs`
- **WHEN** the serve image's build file is read
- **THEN** its base carries a digest, the SSH server's install deletes its host keys and holds no `curl`, its entry
  point is `python3` running the boot script, and its command is `python3` running the launch script

#### Scenario: only a request builds
- **Key:** `serve:image:only-a-request-builds`
- **WHEN** the serve image's workflow is read
- **THEN** a manual request is its only trigger, `latest` is refused, and the digest is written to its summary

#### Scenario: the launcher keeps logging and telemetry off
- **Key:** `serve:image:launcher-forces-quiet`
- **WHEN** the launch script runs with `DO_NOT_TRACK=0`, `HF_HUB_DISABLE_TELEMETRY=0` and `VLLM_NO_USAGE_STATS=0`
  in its environment, and `--enable-log-requests` in the row's arguments
- **THEN** vLLM starts with each of the three set to `1`, and `--no-enable-log-requests` as its last argument

### Requirement: The chat streams the model's answer in the terminal

The system SHALL read the operator's lines, send each with the conversation so far to the model's chat completions
endpoint, print the answer as it streams, keep the conversation in memory, and end the session on `/exit`, the end of
input, or a request that cannot connect, which says the server stopped answering. Thinking SHALL be off unless
`--think` is given. Each streamed part SHALL print without its control characters, U+0000 to U+001F and U+007F to
U+009F, but newline and tab; the conversation SHALL keep each part as streamed.

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

#### Scenario: streamed text is cleaned
- **Key:** `serve:chat:streamed-text-cleaned`
- **WHEN** the server streams the part `\x1b]52;c;b3du\x07two\n\tlines`
- **THEN** stdout holds `]52;c;b3dutwo\n\tlines`, and the next request carries the part as streamed
