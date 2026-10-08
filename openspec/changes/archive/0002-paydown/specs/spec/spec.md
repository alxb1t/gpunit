## MODIFIED Requirements

### Requirement: The spec is one TOML file

The system SHALL read the session's spec from `gpunit.toml`: `project`, `image`, `gpus` (a preference list),
`vram_gb`, `ceiling`, `disk_gb`, and optionally `volume`, `ports`, `ram_gb`, `cuda`, `max_hourly`, `timeout` and
an `[env]` table; and SHALL refuse, naming the field, when a required field is missing, a value has the wrong
type, a key is unknown, or a port, remote or local, lies outside 1–65535.

#### Scenario: a missing required field is named
- **Key:** `spec:file:missing-field-named`
- **WHEN** `gpunit.toml` has no `gpus`
- **THEN** `up` refuses with a line naming `gpus` and exits `1`

#### Scenario: an unknown key is refused
- **Key:** `spec:file:unknown-key-refused`
- **WHEN** `gpunit.toml` holds `gpu = "RTX 4090"`
- **THEN** `up` refuses naming `gpu` and the nearest known key `gpus`

#### Scenario: a port forwards to the same local port by default
- **Key:** `spec:file:ports-default-local`
- **WHEN** `ports = [8188]` and no `local` is given
- **THEN** the session forwards remote `8188` to local `8188`

#### Scenario: a port's local side is overridden
- **Key:** `spec:file:ports-local-override`
- **WHEN** `ports = [{ remote = 8188, local = 18188 }]`
- **THEN** the session forwards remote `8188` to local `18188`

#### Scenario: a port out of range is refused
- **Key:** `spec:file:port-out-of-range`
- **WHEN** `ports = [70000]`, or `ports = [{ remote = 8188, local = 0 }]`
- **THEN** `up` refuses naming `ports`, exits `1`, and makes no request

### Requirement: Secrets come from the environment only

The system SHALL read the provider's key from `RUNPOD_API_KEY` in its own environment, SHALL never read a `.env`
file, SHALL refuse before any request when the variable is empty, SHALL never place the key on a subprocess's
command line, and SHALL never follow a redirect with it: a redirect is an answer like any other failure.

#### Scenario: no key, no request
- **Key:** `spec:secrets:no-key-refused`
- **WHEN** `RUNPOD_API_KEY` is unset and `gpunit up` runs
- **THEN** it refuses naming `RUNPOD_API_KEY`, exits `1`, and makes no request

#### Scenario: a .env beside the spec is ignored
- **Key:** `spec:secrets:dotenv-ignored`
- **WHEN** a `.env` holding `RUNPOD_API_KEY=…` sits beside `gpunit.toml` and the variable is unset
- **THEN** `up` refuses as if no key existed

#### Scenario: a redirect is not followed
- **Key:** `spec:secrets:redirect-not-followed`
- **WHEN** the provider's API answers a request with a 302 to another host
- **THEN** no request reaches that host, and the answer is read as a failure: a lost create, a kept record
