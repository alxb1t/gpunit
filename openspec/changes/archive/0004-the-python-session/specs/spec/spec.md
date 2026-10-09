## MODIFIED Requirements

### Requirement: The spec is one TOML file

The system SHALL read the session's spec from `gpunit.toml`: `project`, `image`, `gpus` (a preference list),
`vram_gb`, `ceiling`, `disk_gb`, and optionally `volume`, `ports`, `ram_gb`, `cuda`, `max_hourly`, `timeout` and
an `[env]` table; and SHALL refuse, naming the field, when a required field is missing, a value has the wrong
type, a key is unknown, a port, remote or local, lies outside 1–65535, or `[env]` names a variable beginning
`GPUNIT_`.

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

#### Scenario: a GPUNIT_ variable in env is refused
- **Key:** `spec:file:env-gpunit-refused`
- **WHEN** `[env]` holds `GPUNIT_VOLUME_PATH = "/data"`
- **THEN** `up` refuses naming `GPUNIT_VOLUME_PATH`, exits `1`, and makes no request
