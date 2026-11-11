## ADDED Requirements

### Requirement: Down clears a record only when its pod is gone, and sweeps every listed pod

The system SHALL, on `down`, delete the recorded pod; SHALL keep the record when the answer is anything but a
success — `200` or `204` — unless the pod is **gone**, naming a 404 as "gone or a wrong key"; SHALL then delete every
live pod the listing names for this project, reading its answer by the same rule; SHALL remove `.gpunit/pending` only
when the sweep left nothing; and SHALL exit `1` when any delete failed or the listing could not be read. A recorded pod
is gone when its read answers `404` and the account's listing of its pods, read with the same key, answers without it.
A read or listing that fails, or a listing that holds the pod, SHALL keep the record. A gone pod's record SHALL be
cleared, saying `pod <id> is gone; its record is cleared`, and SHALL be no failure. Gone is no delete: the ledger SHALL
record no line for it.

#### Scenario: a 404 keeps the record
- **Key:** `session:down:404-keeps-record`
- **WHEN** the delete answers 404 and the pod's read fails, or its read answers 404 and the account's listing fails or still holds it
- **THEN** `.gpunit/pod` remains, stderr says the key may be wrong, and `down` exits `1`

#### Scenario: a gone pod's record is cleared
- **Key:** `session:down:gone-clears`
- **WHEN** the delete answers 404, the pod's read answers 404 and the account's listing lacks the pod
- **THEN** `.gpunit/pod`, `.gpunit/known_hosts`, `.gpunit/key` and `.gpunit/key.pub` are gone, stderr says the pod is gone, the ledger gains no line, and `down` exits `0`

#### Scenario: a success clears the record
- **Key:** `session:down:success-clears`
- **WHEN** the delete answers a success
- **THEN** `.gpunit/pod`, `.gpunit/known_hosts`, `.gpunit/key` and `.gpunit/key.pub` are gone

#### Scenario: a 200 is a success
- **Key:** `session:down:200-is-success`
- **WHEN** the delete of the recorded pod and of a swept pod each answer 200
- **THEN** the record is cleared, the sweep counts the pod deleted, and `down` exits `0`

#### Scenario: the sweep removes a pod no record names
- **Key:** `session:down:sweep-unrecorded`
- **WHEN** no record exists, `.gpunit/pending` exists, and the listing names one live pod
- **THEN** that pod is deleted, `.gpunit/pending` is gone, and `down` exits `0`

#### Scenario: an unreadable listing fails
- **Key:** `session:down:unreadable-listing-fails`
- **WHEN** the listing answers 500
- **THEN** `down` exits `1` and says no sweep was made

## REMOVED Requirements

### Requirement: Down never reads a 404 as gone, and sweeps every listed pod

**Reason:** a pod's 404 is read as gone when the account's listing lacks the pod too, as a volume's is (D55, D57).
**Migration:** `Down clears a record only when its pod is gone, and sweeps every listed pod` carries every scenario of it, the 404 one narrowed.
