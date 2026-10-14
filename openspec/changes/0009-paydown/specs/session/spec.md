## MODIFIED Requirements

### Requirement: The host key is verified before anything connects

The system SHALL give each pod it creates a fresh random `GPUNIT_NONCE` of 32 hex characters; SHALL read the line
`gpunit host key <nonce>: SHA256:…` from the pod's log over the provider's API, accepting only a line whose nonce is
the session's; SHALL scan the pod's Ed25519 host key over SSH, SHALL connect only when the two match, writing the
scanned key to `.gpunit/known_hosts`; and SHALL tear the pod down and exit `1` when no line appears within 60 seconds,
no scan answers within 180 seconds, or the two differ. Each read of the log SHALL end when the stream has sent nothing
for 3 seconds, or after 10 seconds in all, taking the last host-key line of what arrived that boot's own
`step: the command` line followed — the command starts after that line, so a line it echoes before it is not the key.
When the log's last lines hold no host-key line, the same poll SHALL read the log again from the time the create was
asked. When the log holds a key line without a nonce that a step line follows, and no line with the session's nonce,
the system SHALL tear the pod down and exit `1`, saying the image's `boot.sh` is older than `v0.6.0`.

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
- **WHEN** the log holds no `gpunit host key` line within 60 seconds
- **THEN** the pod is deleted and `up` exits `1`

#### Scenario: a quiet stream ends the read
- **Key:** `session:hostkey:quiet-stream-ends-read`
- **WHEN** the log stream sends its lines and then nothing
- **THEN** the read returns those lines once the stream has been quiet for 3 seconds, the last fingerprint among them winning

#### Scenario: a key line pushed out of the tail is read from the boot's start
- **Key:** `session:hostkey:since-fallback`
- **WHEN** the log's last lines hold no host-key line, and the log since the create holds one
- **THEN** that fingerprint is the printed one, read with `since` equal to the record's `created`, and the session proceeds

#### Scenario: a line the command echoes is not the key
- **Key:** `session:hostkey:echoed-line-is-ignored`
- **WHEN** the log holds the real key line and boot's `step: the command` line, then a command's output holding `gpunit host key: SHA256:forged` and `x step: the command`
- **THEN** the printed fingerprint is the real one

#### Scenario: a key line with another nonce is not the key
- **Key:** `session:hostkey:other-nonce-ignored`
- **WHEN** the log holds the real key line and boot's step line, then a command's output holding a key line with another nonce and a step line
- **THEN** the printed fingerprint is the real one

#### Scenario: a key line with no step after it is not yet
- **Key:** `session:hostkey:key-without-step-waits`
- **WHEN** the log holds a key line with the session's nonce and no `step: the command` line after it
- **THEN** no fingerprint is read, and the poll goes on until the 60 seconds pass

#### Scenario: each pod gets its own nonce
- **Key:** `session:hostkey:nonce-per-pod`
- **WHEN** two sessions are opened
- **THEN** each create gives its pod a `GPUNIT_NONCE` of 32 hex characters, and the two differ

#### Scenario: an older boot.sh is refused
- **Key:** `session:hostkey:old-boot-refused`
- **WHEN** the log holds `gpunit host key: SHA256:…` and boot's step line, and no line with the session's nonce
- **THEN** the pod is deleted, stderr names `boot.sh` from `v0.6.0`, and `up` exits `1` without waiting the 60 seconds
