## MODIFIED Requirements

### Requirement: The model table names what each model serves on

The system SHALL bundle a model table whose rows each name a model's Hugging Face repository at a pinned revision, its
served name, its vLLM arguments, the card memory it needs, the cards to try in order, and its disk; and SHALL bundle
the digest of the image every row serves on. No row's vLLM arguments SHALL turn request logging on or reset a flag the launcher sets. Each argument's flag is read
with `_` as `-` and cut at `=`; a row SHALL be refused, naming the flag, when a flag is not `--` followed by lowercase
letters, digits and `-`; when it is, or abbreviates, a launcher flag — `--revision`, `--code-revision`,
`--tokenizer-revision`, `--served-model-name`, `--host`, `--port`, `--api-key`; or when it is, or abbreviates,
`--enable-log-requests`, `--enable-log-outputs`, `--log-level` or `--logging-config`; or, naming the argument, when an
argument holds a space or other whitespace, which the launch script splits on. The image's launch script turns
request logging off for every row. A row SHALL be
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

#### Scenario: a row's launcher flag, whole or cut short, is refused
- **Key:** `serve:table:launcher-flags-refused`
- **WHEN** a row's arguments hold `--revision main`, `--port=8001`, `--revisio main`, `--por=8001`, `--api-k k` or
  `--code_rev main`, or `--revisio` behind a tab inside another argument
- **THEN** the row is refused naming the flag, or the argument that hides it, and `--max-num-seqs 8` passes; the
  launch script's own check names the same flag

#### Scenario: a row's rewritten logging flag is refused
- **Key:** `serve:table:logging-families-refused`
- **WHEN** a row's arguments hold `--enable_log_requests`, `--enable-log-o`, `--log-level=debug`, `--hf-overrides.x` or `--config`
- **THEN** the row is refused naming the flag, and `--no-enable-log-requests` passes; the launch script's own check
  names the same flag

### Requirement: The serve image is built on request and pinned

The serve image SHALL be built from vLLM's image named by digest, with an SSH server, `ca-certificates`, no baked host
key, telemetry off, gpunit's boot script as its entry point and gpunit's launch script as its command; SHALL be built
only on a manual request naming a tag other than `latest`; and its digest SHALL be the one the model table records.
The launch script SHALL set `DO_NOT_TRACK`, `HF_HUB_DISABLE_TELEMETRY` and `VLLM_NO_USAGE_STATS` to `1` and pass
`--no-enable-log-requests` after the row's arguments, whatever the pod's environment and the row hold; it SHALL
refuse to start vLLM, exiting `1` and naming the flag, when the row's arguments hold a flag the model table refuses.

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
  in its environment, and `--max-num-seqs 8` in the row's arguments
- **THEN** vLLM starts with each of the three set to `1`, and `--no-enable-log-requests` as its last argument

#### Scenario: the launcher refuses a row the table refuses
- **Key:** `serve:image:launcher-refuses-a-row`
- **WHEN** the launch script runs with `--revisio main` in the row's arguments
- **THEN** vLLM is not started, and the script exits `1` naming `--revisio`
