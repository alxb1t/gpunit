## MODIFIED Requirements

### Requirement: The ledger names each pod gpunit learns of

The system SHALL append one JSON line to `~/.local/state/gpunit/ledger.jsonl` when it first learns a pod's id — when a
create answers, and when a sweep lists a pod no record names — holding the pod's id, the project, the card (null for a
swept pod), the image and the UTC time, and nothing else. It SHALL append one line when `volume up` creates or extends a
window volume, holding the volume's id, the project, `kind` `volume`, its UTC end and the UTC time, and nothing else;
the last such line for a volume's id gives its end. It SHALL append one line when a volume's delete answers `204` —
`volume down`'s, the sweep's of a volume past its end, or the sweep's after a lost create — holding the volume's id,
`kind` `deleted` and the UTC time, and nothing else. A ledger that cannot be written SHALL warn on stderr and SHALL
NOT stop or alter the session, the volume or the teardown.

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

#### Scenario: a window volume is recorded with its end
- **Key:** `spend:ledger:volume-is-recorded`
- **WHEN** `volume up` creates `v1` for `isekai` with `volume_ceiling = "4h"`, then extends it
- **THEN** the ledger holds a line for each, with the keys `id`, `project`, `kind`, `ends` and `at`, and the volume's end is the second line's

#### Scenario: a volume's delete is recorded
- **Key:** `spend:ledger:delete-is-recorded`
- **WHEN** `volume down` deletes the recorded `v1`, the next command deletes the overdue `v2`, or `volume down`'s sweep deletes `v9` on `y`
- **THEN** the ledger holds a new line for that volume whose keys are `id`, `kind` and `at`, `kind` being `deleted`, and no project, host, key or path; a recorded volume's end is still its `volume` line's

### Requirement: Spend reports the provider's billing by project

The system SHALL, on `spend`, read the pods' and the network volumes' billing from the provider for the window; SHALL
give each pod and each window volume its project from the ledger, the first line for a pod's id winning; and SHALL
print one line per project with its pod count and amount, its window volumes' charges in that amount, one line for the
pods the ledger does not name, one line per other volume, and a total, each amount the provider's own and never an
estimate. A volume the ledger does not name SHALL never be attributed to a project. A window volume past its end that
the current UTC day still bills, and that no `deleted` line names, SHALL be named on stderr with `gpunit volume down`.
A billing or a ledger that cannot be read SHALL be an error, never a table.

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
- **WHEN** the provider bills a volume `v1` over the window, and the ledger does not name it
- **THEN** the report holds a line for `v1` with its amount, under no project

#### Scenario: a window volume bills under its project
- **Key:** `spend:report:window-volume-under-project`
- **WHEN** the ledger names window volume `v2` for `isekai`, and the provider bills it `$0.02`
- **THEN** `isekai`'s amount holds the `$0.02`, and no storage line names `v2`

#### Scenario: an overdue volume still billing is named
- **Key:** `spend:report:overdue-volume-named`
- **WHEN** the ledger gives window volume `v2` an end yesterday, and the provider bills `v2` today
- **THEN** stderr names `v2`, its project and `gpunit volume down`

#### Scenario: a deleted volume is not named
- **Key:** `spend:report:deleted-volume-not-named`
- **WHEN** the ledger gives window volume `v2` for `isekai` an end yesterday and a `deleted` line, and the provider bills `v2` today
- **THEN** stderr does not name `v2`, and `isekai`'s amount holds `v2`'s charge

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

#### Scenario: an unreadable ledger is an error, not a table
- **Key:** `spend:report:unreadable-ledger-fails`
- **WHEN** the ledger cannot be read — bytes that are not UTF-8, a directory in its place, or no home directory
- **THEN** `spend` prints no table, says the ledger could not be read, and exits `1`
