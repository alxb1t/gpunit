## Purpose

What a consumer declares about its GPU session, in one file it commits; what is refused before a pod exists; and
where secrets come from — so a session cannot be opened without an end, a pin, or an owner for its key.

## Requirements

### Requirement: The spec is one TOML file

The system SHALL read the session's spec from `gpunit.toml`: `project`, `image`, `gpus` (a preference list),
`vram_gb`, `ceiling`, `disk_gb`, and optionally `volume`, `volume_gb`, `volume_ceiling`, `volume_datacenter`,
`datacenters`, `ports`, `ram_gb`, `cuda`, `max_hourly`, `timeout` and an `[env]` table; and SHALL refuse, naming the
field, when a required field is missing, a value has the wrong type, a key is unknown, a port, remote or local, lies
outside 1–65535, or `[env]` names a variable beginning `GPUNIT_` or `RUNPOD_`. An `[env]` value SHALL reach the pod as
written, a RunPod secret reference `{{ RUNPOD_SECRET_<name> }}` among them. `volume_gb` SHALL be from 10 to 4000 and
SHALL come with `volume_ceiling`, a duration as `ceiling` is; `volume_ceiling` and `volume_datacenter` SHALL come with
`volume_gb`; and `volume` and `volume_gb` SHALL NOT both be set. `datacenters` SHALL be a non-empty list of data-centre
ids, kept in its order; a `volume_datacenter` it does not name SHALL be refused, naming
`volume_datacenter` and `datacenters`.

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

#### Scenario: a RUNPOD_ variable in env is refused
- **Key:** `spec:file:env-runpod-refused`
- **WHEN** `[env]` holds `RUNPOD_API_KEY = "rpa_x"`
- **THEN** `up` refuses naming `RUNPOD_API_KEY`, exits `1`, and makes no request

#### Scenario: a secret reference passes as written
- **Key:** `spec:file:env-secret-reference-kept`
- **WHEN** `[env]` holds `HF_TOKEN = "{{ RUNPOD_SECRET_hf_token }}"` and a pod is created
- **THEN** the create's environment holds `HF_TOKEN` with the value `{{ RUNPOD_SECRET_hf_token }}`

#### Scenario: the allow-list loads
- **Key:** `spec:file:datacenters-load`
- **WHEN** `datacenters = ["EU-RO-1", "EU-SE-1"]`
- **THEN** the spec holds `EU-RO-1` and `EU-SE-1`, in that order

#### Scenario: an empty allow-list is refused
- **Key:** `spec:file:datacenters-empty-refused`
- **WHEN** `datacenters = []`, or `datacenters = ["EU-RO-1", 7]`
- **THEN** `up` refuses naming `datacenters`, exits `1`, and makes no request

#### Scenario: a window volume outside the allow-list is refused
- **Key:** `spec:file:volume-datacenter-outside-refused`
- **WHEN** `datacenters = ["EU-RO-1"]`, `volume_gb = 60`, `volume_ceiling = "4h"` and `volume_datacenter = "CA-MTL-4"`
- **THEN** `up` and `volume up` refuse naming `volume_datacenter` and `datacenters`, exit `1`, and make no request

### Requirement: An image without a digest is refused

The system SHALL refuse an `image` that does not end in `@sha256:` and sixty-four hex characters, before any
network call.

#### Scenario: a tag is refused
- **Key:** `spec:image:tag-refused`
- **WHEN** `image = "ghcr.io/alxb1t/isekai:latest"`
- **THEN** `up` refuses naming the digest form and exits `1`, and no request is made

### Requirement: The ceiling is required

The system SHALL require `ceiling`, a duration in seconds, minutes or hours (`600s`, `45m`, `4h`), with no default;
and SHALL pass it to the pod as `GPUNIT_CEILING` in seconds.

#### Scenario: no ceiling, no pod
- **Key:** `spec:ceiling:required`
- **WHEN** `gpunit.toml` has no `ceiling`
- **THEN** `up` refuses naming `ceiling` and makes no request

#### Scenario: the ceiling reaches the pod in seconds
- **Key:** `spec:ceiling:reaches-the-pod`
- **WHEN** `ceiling = "45m"` and a pod is created
- **THEN** the create carries `GPUNIT_CEILING=2700` in the pod's environment

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
