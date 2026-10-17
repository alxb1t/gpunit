## MODIFIED Requirements

### Requirement: The host key is verified from the log's tail before anything connects

The system SHALL give each pod it creates a fresh random `GPUNIT_NONCE` of 32 hex characters; SHALL read the line
`gpunit host key <nonce>: SHA256:…` from the pod's log over the provider's API, accepting only a line whose nonce is
the session's; SHALL scan the pod's Ed25519 host key over SSH, SHALL connect only when the two match, writing the
scanned key to `.gpunit/known_hosts`; and SHALL tear the pod down and exit `1` when no line appears within 60 seconds,
no scan answers within 180 seconds, or the two differ. Each read of the log SHALL end when the stream has sent nothing
for 3 seconds, or after 10 seconds in all, taking the last host-key line of what arrived that boot's own
`step: the command` line followed — the command starts after that line, so a line it echoes before it is not the key.
Each poll SHALL read the log's last 5000 lines once; a host-key line further back is not read, RunPod's log since a time
being read from the same tail, and the poll goes on until its 60 seconds pass. When a read of fewer than 5000 lines
opens with boot's first line, `<UTC> step: the ceiling, <N>s`, and so holds the log from its start, and it holds a key
line without a nonce that a step line follows, and no line with the session's nonce, the system SHALL tear the pod
down and exit `1`, saying the image's `boot.sh` is older than `v0.6.0`. A read that opens with any other line — cut by
its time bound or a fault, or a tail past boot's lines — SHALL judge nothing an older `boot.sh`.

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

#### Scenario: a key line pushed out of the tail is not read
- **Key:** `session:hostkey:tail-bound`
- **WHEN** the log's last 5000 lines hold no host-key line, or only a command's echo of a key line with no nonce and a step line, boot's own lines having left them
- **THEN** each poll reads the last 5000 lines once, nothing is judged an older `boot.sh`, and the pod is deleted and `up` exits `1` once the 60 seconds pass

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
- **WHEN** the log, under 5000 lines and opening with boot's `step: the ceiling` line, holds `gpunit host key: SHA256:…` and boot's step line, and no line with the session's nonce
- **THEN** the pod is deleted, stderr names `boot.sh` from `v0.6.0`, and `up` exits `1` without waiting the 60 seconds

#### Scenario: a read that misses the log's start judges nothing
- **Key:** `session:hostkey:cut-read-not-judged`
- **WHEN** a read of under 5000 lines opens with a command's output, not boot's `step: the ceiling` line, and holds `gpunit host key: SHA256:…` and a step line, and no line with the session's nonce
- **THEN** nothing is judged an older `boot.sh`, and the pod is deleted and `up` exits `1` once the 60 seconds pass
