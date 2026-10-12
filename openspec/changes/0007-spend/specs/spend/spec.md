## Purpose

What gpunit's sessions cost, answered from the provider's own billing: a ledger of the pods gpunit made gives each its
project, and what the ledger does not know, and the volumes the account keeps, are shown on lines of their own.

## ADDED Requirements

### Requirement: The ledger names each pod gpunit learns of

The system SHALL append one JSON line to `~/.local/state/gpunit/ledger.jsonl` when it first learns a pod's id — when a
create answers, and when a sweep lists a pod no record names — holding the pod's id, the project, the card (null for a
swept pod), the image and the UTC time, and nothing else. A ledger that cannot be written SHALL warn on stderr and
SHALL NOT stop or alter the session or the teardown.

#### Scenario: a create is recorded
- **Key:** `spend:ledger:create-is-recorded`
- **WHEN** `up` creates a pod for the project `isekai` on `NVIDIA A40`
- **THEN** the ledger holds one new line naming that pod's id, `isekai`, `NVIDIA A40`, the image and a UTC time

#### Scenario: a swept pod is recorded
- **Key:** `spend:ledger:sweep-is-recorded`
- **WHEN** `down` lists a live pod of the project that no record names, and deletes it
- **THEN** the ledger holds a line for that pod with the project and a null card

#### Scenario: the line holds no secret
- **Key:** `spend:ledger:holds-nothing-else`
- **WHEN** a create is recorded
- **THEN** the line's keys are `id`, `project`, `card`, `image` and `at`, and no host, key or path

#### Scenario: an unwritable ledger blocks nothing
- **Key:** `spend:ledger:failure-never-blocks`
- **WHEN** the ledger's directory cannot be written during `up`
- **THEN** stderr warns that the ledger could not be written, and `up` opens the session as it would have

### Requirement: Spend reports the provider's billing by project

The system SHALL, on `spend`, read the pods' and the network volumes' billing from the provider for the window; SHALL
give each pod its project from the ledger, the first line for an id winning; and SHALL print one line per project with
its pod count and amount, one line for the pods the ledger does not name, one line per volume, and a total, each
amount the provider's own and never an estimate. Storage SHALL never be attributed to a project.

#### Scenario: pods are summed by project
- **Key:** `spend:report:by-project`
- **WHEN** the ledger names two pods `isekai` and one `serve-qwen3-4b`, and the provider bills each over two days
- **THEN** the report holds a line `isekai` with two pods and the sum of their amounts over both days, and a line `serve-qwen3-4b` with one

#### Scenario: a pod the ledger does not name is unattributed
- **Key:** `spend:report:unattributed`
- **WHEN** the provider bills a pod that no ledger line names
- **THEN** the report holds a line `unattributed` counting it, and its amount is in the total

#### Scenario: storage is a line of its own
- **Key:** `spend:report:storage-is-its-own-line`
- **WHEN** the provider bills a volume `v1` over the window
- **THEN** the report holds a line for `v1` with its amount, under no project

#### Scenario: the total is the provider's
- **Key:** `spend:report:total-is-the-providers`
- **WHEN** the provider bills pods and volumes over the window
- **THEN** the total is the sum of every pod record's and every volume record's total amount, as the provider gave them

#### Scenario: the day still billing is named
- **Key:** `spend:report:in-progress-day-noted`
- **WHEN** a report is printed
- **THEN** stderr says the current UTC day is still being billed and its figures can change

#### Scenario: the report as JSON
- **Key:** `spend:report:json`
- **WHEN** `gpunit spend --json` runs
- **THEN** stdout is one JSON object with the keys `from`, `to`, `projects`, `unattributed`, `storage` and `total`

#### Scenario: an unreadable billing is an error, not zeros
- **Key:** `spend:report:unreadable-billing-fails`
- **WHEN** the provider's billing answers 500
- **THEN** `spend` prints no table, says the billing could not be read, and exits `1`

### Requirement: The window is whole UTC days

The system SHALL report `--days N` whole UTC days ending with the current one, `N` being 7 when not given, and SHALL
refuse an `N` under 1 before any request.

#### Scenario: the default window
- **Key:** `spend:window:default-is-seven-days`
- **WHEN** `gpunit spend` runs on 2026-10-12
- **THEN** the billing is read from 2026-10-06T00:00:00Z to 2026-10-13T00:00:00Z, in day buckets

#### Scenario: a chosen window
- **Key:** `spend:window:days`
- **WHEN** `gpunit spend --days 2` runs on 2026-10-12
- **THEN** the billing is read from 2026-10-11T00:00:00Z to 2026-10-13T00:00:00Z
