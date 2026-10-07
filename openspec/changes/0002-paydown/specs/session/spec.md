## ADDED Requirements

### Requirement: Up refuses without the OpenSSH client

The system SHALL, on `up`, refuse before any request when `ssh`, `ssh-keygen` or `ssh-keyscan` is not on `PATH`,
naming each one missing; a session it could not reach or verify is never rented.

#### Scenario: a missing ssh-keyscan refuses before the create
- **Key:** `session:tools:missing-refuses`
- **WHEN** `ssh-keygen` and `ssh` are on `PATH` and `ssh-keyscan` is not
- **THEN** `up` refuses naming `ssh-keyscan`, exits `1`, and makes no request

## MODIFIED Requirements

### Requirement: The host key is verified before anything connects

The system SHALL read the line `gpunit host key: SHA256:…` from the pod's log over the provider's API, SHALL scan
the pod's Ed25519 host key over SSH, SHALL connect only when the two match, writing the scanned key to
`.gpunit/known_hosts`; and SHALL tear the pod down and exit `1` when no line appears within 60 seconds, no scan
answers within 180 seconds, or the two differ. Each read of the log SHALL end when the stream has sent nothing
for 3 seconds, or after 10 seconds in all, taking the last host-key line of what arrived.

#### Scenario: a match is recorded
- **Key:** `session:hostkey:match-recorded`
- **WHEN** the log's fingerprint equals the scanned key's
- **THEN** `.gpunit/known_hosts` holds the scanned key and stderr prints `host key verified`

#### Scenario: a mismatch tears down
- **Key:** `session:hostkey:mismatch-tears-down`
- **WHEN** the scanned key's fingerprint differs from the printed one
- **THEN** the pod is deleted, no record remains, and `up` exits `1`

#### Scenario: no fingerprint tears down
- **Key:** `session:hostkey:no-line-tears-down`
- **WHEN** the log holds no `gpunit host key:` line within 60 seconds
- **THEN** the pod is deleted and `up` exits `1`

#### Scenario: a quiet stream ends the read
- **Key:** `session:hostkey:quiet-stream-ends-read`
- **WHEN** the log stream sends its lines and then nothing
- **THEN** the read returns those lines once the stream has been quiet for 3 seconds, the last fingerprint among them winning

### Requirement: Down never reads a 404 as gone, and sweeps every listed pod

The system SHALL, on `down`, delete the recorded pod; SHALL keep the record when the answer is anything but a
success — `200` or `204` — naming a 404 as "gone or a wrong key"; SHALL then delete every live pod the listing
names for this project, reading its answer by the same rule; SHALL remove `.gpunit/pending` only when the sweep
left nothing; and SHALL exit `1` when any delete failed or the listing could not be read.

#### Scenario: a 404 keeps the record
- **Key:** `session:down:404-keeps-record`
- **WHEN** the delete answers 404
- **THEN** `.gpunit/pod` remains, stderr says the key may be wrong, and `down` exits `1`

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

### Requirement: Ssh opens a shell on the session

The system SHALL, on `ssh`, exec the system `ssh` with the session's key, the recorded host and port, and strict
checking against `.gpunit/known_hosts`; SHALL refuse with no record; and SHALL refuse, naming `ssh`, when `ssh`
cannot be run. Every `ssh` line the system starts — the shell, `run`'s tunnel, and `GPUNIT_SSH` — SHALL read no
ssh_config file and SHALL offer the session's key alone.

#### Scenario: ssh uses the record
- **Key:** `session:ssh:uses-record`
- **WHEN** `gpunit ssh` runs with a record
- **THEN** the `ssh` command names `.gpunit/key`, `.gpunit/known_hosts`, `StrictHostKeyChecking=yes`, the host and the port

#### Scenario: no ssh_config, no other key
- **Key:** `session:ssh:own-config-only`
- **WHEN** `gpunit ssh` runs, or `gpunit run` opens its tunnel
- **THEN** each `ssh` command holds `-F none` and `IdentitiesOnly=yes`

#### Scenario: no ssh refuses
- **Key:** `session:ssh:no-ssh-refuses`
- **WHEN** `gpunit ssh` runs with a record and `ssh` cannot be run
- **THEN** it refuses naming `ssh`, on one stderr line, and exits `1`
