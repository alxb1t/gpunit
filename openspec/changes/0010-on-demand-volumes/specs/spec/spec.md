## MODIFIED Requirements

### Requirement: The spec is one TOML file

The system SHALL read the session's spec from `gpunit.toml`: `project`, `image`, `gpus` (a preference list),
`vram_gb`, `ceiling`, `disk_gb`, and optionally `volume`, `volume_gb`, `volume_ceiling`, `volume_datacenter`, `ports`,
`ram_gb`, `cuda`, `max_hourly`, `timeout` and an `[env]` table; and SHALL refuse, naming the field, when a required
field is missing, a value has the wrong type, a key is unknown, a port, remote or local, lies outside 1–65535, or
`[env]` names a variable beginning `GPUNIT_`. `volume_gb` SHALL be from 10 to 4000 and SHALL come with
`volume_ceiling`, a duration as `ceiling` is; `volume_ceiling` and `volume_datacenter` SHALL come with `volume_gb`; and
`volume` and `volume_gb` SHALL NOT both be set.

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

#### Scenario: the window volume's keys load
- **Key:** `spec:file:volume-keys`
- **WHEN** `volume_gb = 60`, `volume_ceiling = "4h"` and `volume_datacenter = "EU-RO-1"`
- **THEN** the spec holds 60 GB, 14400 seconds and `EU-RO-1`

#### Scenario: a volume_gb without its ceiling is refused
- **Key:** `spec:file:volume-gb-needs-ceiling`
- **WHEN** `volume_gb = 60` and no `volume_ceiling`
- **THEN** `up` refuses naming `volume_ceiling`, exits `1`, and makes no request

#### Scenario: a kept volume and a window volume are refused together
- **Key:** `spec:file:volume-and-volume-gb-refused`
- **WHEN** `volume = "v1"` and `volume_gb = 60`
- **THEN** `up` refuses naming both keys, exits `1`, and makes no request

#### Scenario: a volume size out of range is refused
- **Key:** `spec:file:volume-gb-out-of-range`
- **WHEN** `volume_gb = 5`, or `volume_gb = 5000`
- **THEN** `up` refuses naming `volume_gb` and the range 10–4000
