## MODIFIED Requirements

### Requirement: Status reports the record, in words or JSON

The system SHALL, on `status`, print the recorded session — the pod id, the image, the host and the port — and
SHALL print the same as one JSON object on `--json`; with no record it SHALL say so and exit `0`. When the pod's read
fails, it SHALL report the status `UNKNOWN`. When the recorded pod is gone — its read answers `404` and the account's
listing lacks it — it SHALL clear the record, say `pod <id> is gone; its record is cleared` on stderr, print what it
prints with no record, and exit `0`.

#### Scenario: status as JSON
- **Key:** `cli:status:json`
- **WHEN** `gpunit status --json` runs with a record present
- **THEN** stdout is one JSON object with the keys `id`, `image`, `host`, `port`, `status`

#### Scenario: no record
- **Key:** `cli:status:no-record`
- **WHEN** `gpunit status` runs with no `.gpunit/pod`
- **THEN** it prints that no session is recorded and exits `0`

#### Scenario: a gone pod's record is cleared
- **Key:** `cli:status:gone-clears`
- **WHEN** `gpunit status --json` runs with a record whose pod reads 404 and is missing from the account's listing
- **THEN** `.gpunit/pod` is gone, stdout is `null`, stderr says the pod is gone, and it exits `0`

#### Scenario: a pod still listed keeps its record
- **Key:** `cli:status:listed-keeps-record`
- **WHEN** `gpunit status` runs with a record whose pod reads 404 and the account's listing still holds it, or the listing fails
- **THEN** `.gpunit/pod` remains, stdout names the status `UNKNOWN`, and it exits `0`
