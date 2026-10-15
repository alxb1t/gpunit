## MODIFIED Requirements

### Requirement: Spend reports the provider's billing by project

The system SHALL, on `spend`, read the pods' and the network volumes' billing from the provider for the window; SHALL
give each pod its project from the ledger, the first line for an id winning; and SHALL print one line per project with
its pod count and amount, one line for the pods the ledger does not name, one line per volume, and a total, each
amount the provider's own and never an estimate. Storage SHALL never be attributed to a project. A billing or a ledger
that cannot be read SHALL be an error, never a table.

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

#### Scenario: an unreadable ledger is an error, not a table
- **Key:** `spend:report:unreadable-ledger-fails`
- **WHEN** the ledger cannot be read — bytes that are not UTF-8, a directory in its place, or no home directory
- **THEN** `spend` prints no table, says the ledger could not be read, and exits `1`
