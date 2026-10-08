## MODIFIED Requirements

### Requirement: The host key is verified before anything connects

The system SHALL read the line `gpunit host key: SHA256:…` from the pod's log over the provider's API, SHALL scan
the pod's Ed25519 host key over SSH, SHALL connect only when the two match, writing the scanned key to
`.gpunit/known_hosts`; and SHALL tear the pod down and exit `1` when no line appears within 60 seconds, no scan
answers within 180 seconds, or the two differ. Each read of the log SHALL end when the stream has sent nothing
for 3 seconds, or after 10 seconds in all, taking the last host-key line of what arrived. When the log's last
lines hold no host-key line, the same poll SHALL read the log again from the time the create was asked.

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

#### Scenario: a key line pushed out of the tail is read from the boot's start
- **Key:** `session:hostkey:since-fallback`
- **WHEN** the log's last lines hold no host-key line, and the log since the create holds one
- **THEN** that fingerprint is the printed one, read with `since` equal to the record's `created`, and the session proceeds
