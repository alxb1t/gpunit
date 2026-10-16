## MODIFIED Requirements

### Requirement: The volume pins the data centre

The system SHALL, when `volume` is set, read the volume's data centre from the provider before any create, SHALL
refuse when the volume cannot be read, SHALL create the pod in that data centre with the volume mounted, and SHALL
tell the pod the volume's id as `GPUNIT_VOLUME_ID` and its mount path as `GPUNIT_VOLUME_PATH` in its environment. When
`volume_gb` is set, the system SHALL do the same with the volume `.gpunit/volume` records; SHALL refuse, naming
`gpunit volume up`, when none is recorded; and SHALL refuse, naming the volume's end, when the session's ceiling plus
its wait for SSH would end after it.

#### Scenario: the create carries the volume's data centre
- **Key:** `session:volume:pins-datacenter`
- **WHEN** `volume = "v1"` and the provider says `v1` is in `EU-RO-1`
- **THEN** the create names `EU-RO-1` and mounts `v1`

#### Scenario: an unreadable volume refuses
- **Key:** `session:volume:unreadable-refuses`
- **WHEN** the volume read answers 404
- **THEN** `up` refuses naming the volume id and makes no create

#### Scenario: the pod is told its volume
- **Key:** `session:volume:the-pod-is-told`
- **WHEN** `volume = "v1"` and a pod is created on RunPod
- **THEN** the create's environment holds `GPUNIT_VOLUME_ID=v1` and `GPUNIT_VOLUME_PATH=/runpod-volume`

#### Scenario: the window's volume is mounted
- **Key:** `session:volume:window-mounted`
- **WHEN** `volume_gb = 60` and `.gpunit/volume` records `v2` in `CA-MTL-4`, its end four hours away
- **THEN** the create names `CA-MTL-4` and mounts `v2`

#### Scenario: no window volume refuses
- **Key:** `session:volume:window-missing-refuses`
- **WHEN** `volume_gb = 60` and `.gpunit/volume` does not exist
- **THEN** `up` refuses naming `gpunit volume up`, and makes no create

#### Scenario: a session past the volume's end refuses
- **Key:** `session:volume:outlives-window-refuses`
- **WHEN** the recorded volume ends in 30 minutes, and `ceiling = "45m"`
- **THEN** `up` refuses naming the volume's end and `gpunit volume up`, and makes no create

## REMOVED Requirements

### Requirement: The host key is verified before anything connects

**Reason**: its scenario `session:hostkey:since-fallback` reads a key line from the log since the create when the tail
has lost it; RunPod's log since a time is read from the same 5000-line tail (0010 design D14), so no such read exists.
**Migration**: the requirement below keeps every other rule and scenario and states the tail's bound,
`session:hostkey:tail-bound` replacing `session:hostkey:since-fallback`.

## ADDED Requirements

### Requirement: The host key is verified from the log's tail before anything connects

The system SHALL give each pod it creates a fresh random `GPUNIT_NONCE` of 32 hex characters; SHALL read the line
`gpunit host key <nonce>: SHA256:…` from the pod's log over the provider's API, accepting only a line whose nonce is
the session's; SHALL scan the pod's Ed25519 host key over SSH, SHALL connect only when the two match, writing the
scanned key to `.gpunit/known_hosts`; and SHALL tear the pod down and exit `1` when no line appears within 60 seconds,
no scan answers within 180 seconds, or the two differ. Each read of the log SHALL end when the stream has sent nothing
for 3 seconds, or after 10 seconds in all, taking the last host-key line of what arrived that boot's own
`step: the command` line followed — the command starts after that line, so a line it echoes before it is not the key.
Each poll SHALL read the log's last 5000 lines once; a host-key line further back is not read, RunPod's log since a time
being read from the same tail, and the poll goes on until its 60 seconds pass. When a read of fewer than 5000 lines,
and so the whole log, holds a key line without a nonce that a step line follows, and no line with the session's nonce,
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
- **WHEN** the log, under 5000 lines, holds `gpunit host key: SHA256:…` and boot's step line, and no line with the session's nonce
- **THEN** the pod is deleted, stderr names `boot.sh` from `v0.6.0`, and `up` exits `1` without waiting the 60 seconds
