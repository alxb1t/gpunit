## Purpose

The lifecycle of one GPU session — placed from a preference list, reached only after its host key is proven, and
torn down on every way out — with the spend rules that keep a pod from billing with nothing watching it.

## Requirements

### Requirement: One live session per project

The system SHALL name the pod `gpunit-<project>` and SHALL refuse `up` when `.gpunit/pod` exists, when
`.gpunit/pending` exists, or when the provider lists a live pod of that name whose image matches the spec's;
and SHALL fail the listing, not pass it, when a pod of that name carries no image.

#### Scenario: a recorded pod refuses up
- **Key:** `session:one:recorded-refuses`
- **WHEN** `.gpunit/pod` exists
- **THEN** `up` refuses naming `gpunit down` and makes no create

#### Scenario: a listed pod refuses up
- **Key:** `session:one:listed-refuses`
- **WHEN** no record exists and the provider lists a live `gpunit-isekai` pod on the spec's image
- **THEN** `up` refuses naming the pod's id and makes no create

#### Scenario: a look-alike image is not ours
- **Key:** `session:one:look-alike-image-ignored`
- **WHEN** the provider lists a live `gpunit-isekai` pod on an image that only begins with the spec's
- **THEN** the listing does not count it

### Requirement: A GPU is placed from the preference list

The system SHALL read each named GPU's memory from the provider's catalogue, SHALL refuse a name the catalogue
does not know, SHALL skip a card under `vram_gb` or over `max_hourly`, SHALL try the remaining cards in order
with one create each, SHALL move to the next on a refusal the provider attributes to capacity or a rule (a 400),
and SHALL exit `1` when none was placed.

#### Scenario: an unknown card refuses
- **Key:** `session:place:unknown-card-refuses`
- **WHEN** `gpus` names a card the catalogue answers 404 for
- **THEN** `up` refuses naming the card and makes no create

#### Scenario: a card under the floor is skipped
- **Key:** `session:place:under-floor-skipped`
- **WHEN** the first card has less memory than `vram_gb` and the second has enough
- **THEN** the first create is for the second card, and stderr says the first was skipped

#### Scenario: a 400 moves on
- **Key:** `session:place:400-moves-on`
- **WHEN** the create for the first card answers 400 and the second answers 201
- **THEN** the session is on the second card and exits `0`

#### Scenario: none placed
- **Key:** `session:place:none-placed`
- **WHEN** every create answers 400
- **THEN** `up` exits `1`, no record exists, and `.gpunit/pending` is gone

### Requirement: A lost create exits 3 and is swept later

The system SHALL write `.gpunit/pending` before the first create and remove it only after a record is written or
every create was refused; SHALL exit `3` when a create's answer is a 5xx, a transport failure, or a 201 without an
id, leaving `pending` in place; and `down` SHALL treat `pending` as a pod that may exist.

#### Scenario: a 5xx is a lost create
- **Key:** `session:lost:5xx-exits-3`
- **WHEN** the create answers 503
- **THEN** `up` exits `3`, `.gpunit/pending` remains, and stderr names `gpunit down`

#### Scenario: a transport failure is a lost create
- **Key:** `session:lost:transport-exits-3`
- **WHEN** the create's connection fails before an answer
- **THEN** `up` exits `3` and `.gpunit/pending` remains

### Requirement: The wait is bounded and a timeout tears down

The system SHALL poll the pod until it has a public host and a mapped port `22`, for at most `timeout` seconds
(default 420); SHALL read a failed poll as not yet, never as an abort; and on the deadline SHALL tear the pod down and
exit `1`. A pod the provider reports `EXITED`, `ERROR` or `TERMINATED` on two polls in a row SHALL end the wait at
once, tearing the pod down and exiting `1`, naming the status; any other status, and any failed read, SHALL keep waiting.
The rule's live proof, `make live-dead`, SHALL exit `1` naming `gpunit down`, with no `up` and no `down`, in a checkout
whose `.gpunit/` records a pod or a pending create.

#### Scenario: the deadline tears down
- **Key:** `session:wait:deadline-tears-down`
- **WHEN** no poll answers a host and a port within `timeout`
- **THEN** the pod is deleted, no record remains, and `up` exits `1`

#### Scenario: a failed poll is not yet
- **Key:** `session:wait:failed-poll-is-not-yet`
- **WHEN** one poll answers 500 and the next answers a host and a port
- **THEN** the wait continues and the session proceeds

#### Scenario: a dead pod ends the wait
- **Key:** `session:wait:dead-pod-tears-down`
- **WHEN** two polls in a row answer the status `EXITED`, with no host or port
- **THEN** the pod is deleted, no record remains, `up` exits `1` naming `EXITED`, and no further poll is made

#### Scenario: one terminal poll is not yet
- **Key:** `session:wait:one-dead-poll-is-not-yet`
- **WHEN** one poll answers `EXITED` and the next answers a host and a port
- **THEN** the wait continues and the session proceeds

#### Scenario: the live proof spares a recorded session
- **Key:** `session:wait:dead-proof-spares-a-record`
- **WHEN** `live/dead.py` runs in a checkout whose `.gpunit/` holds `pod`, or `pending`
- **THEN** it exits `1` naming `gpunit down`, and runs neither `gpunit up` nor `gpunit down`

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

### Requirement: A fresh keypair per session

The system SHALL generate an Ed25519 keypair into `.gpunit/key` and `.gpunit/key.pub` at mode `0600` before the
create, SHALL pass the public key to the pod, and SHALL delete both at teardown. Every write into `.gpunit/` SHALL
first set the directory to mode `0700`, whether it made the directory or found it.

#### Scenario: the keypair is made and passed
- **Key:** `session:key:fresh-per-session`
- **WHEN** `up` creates a pod
- **THEN** `.gpunit/key` exists at `0600` and the create's `PUBLIC_KEY` equals `.gpunit/key.pub`

#### Scenario: the keypair leaves with the pod
- **Key:** `session:key:deleted-at-teardown`
- **WHEN** `down` deletes the recorded pod
- **THEN** `.gpunit/key` and `.gpunit/key.pub` are gone

#### Scenario: an existing directory is made private
- **Key:** `session:key:dir-private`
- **WHEN** `.gpunit/` exists at mode `0755` and `up` writes the keypair
- **THEN** `.gpunit/` is at mode `0700`

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

### Requirement: Only the secure cloud, only port 22

The system SHALL create every pod with `cloud` secure and `22/tcp` as the only exposed port.

#### Scenario: the create's cloud and ports
- **Key:** `session:create:secure-and-22`
- **WHEN** `up` creates a pod with `ports = [8188]`
- **THEN** the create names the secure cloud and exposes `22/tcp` only

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

### Requirement: Up refuses without the OpenSSH client

The system SHALL, on `up`, refuse before any request when `ssh`, `ssh-keygen` or `ssh-keyscan` is not on `PATH`,
naming each one missing; a session it could not reach or verify is never rented.

#### Scenario: a missing ssh-keyscan refuses before the create
- **Key:** `session:tools:missing-refuses`
- **WHEN** `ssh-keygen` and `ssh` are on `PATH` and `ssh-keyscan` is not
- **THEN** `up` refuses naming `ssh-keyscan`, exits `1`, and makes no request

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

### Requirement: Pods are placed within the allow-list

When the spec sets `datacenters`, the system SHALL name those data centres, in their order, as the create's data
centres when no volume is mounted; SHALL refuse before any create, naming the volume, its data centre and
`datacenters`, when the mounted volume's data centre is not among them; and SHALL read the pod's data centre at each
poll of the wait, treating the pod as up only once it reads one of them, and tearing the pod down and exiting `1`,
naming the data centre, when it reads another. Without `datacenters`, placement SHALL be as before.

#### Scenario: the create names the allow-list
- **Key:** `session:datacenters:create-names-them`
- **WHEN** `datacenters = ["EU-RO-1", "EU-SE-1"]` and no volume is set
- **THEN** the create names `EU-RO-1` and `EU-SE-1`, in that order, as its data centres

#### Scenario: a mounted volume outside the allow-list refuses
- **Key:** `session:datacenters:volume-outside-refuses`
- **WHEN** `datacenters = ["EU-RO-1"]`, and `volume = "v1"` or the recorded window volume is in `CA-MTL-4`
- **THEN** `up` refuses naming the volume, `CA-MTL-4` and `datacenters`, and makes no create

#### Scenario: a pod placed outside the allow-list is torn down
- **Key:** `session:datacenters:pod-outside-tears-down`
- **WHEN** `datacenters = ["EU-RO-1"]` and a poll reads the pod in `US-TX-3`
- **THEN** the pod is deleted, no record remains, and `up` exits `1` naming `US-TX-3` and `datacenters`

#### Scenario: a pod with no data centre yet is not up
- **Key:** `session:datacenters:unread-is-not-yet`
- **WHEN** `datacenters = ["EU-RO-1"]`, one poll reads a host and a port with no data centre, and the next reads them
  in `EU-RO-1`
- **THEN** the wait continues past the first, and the session proceeds after the second

#### Scenario: no allow-list, no data centres named
- **Key:** `session:datacenters:unset-names-none`
- **WHEN** `datacenters` is not set and no volume is set
- **THEN** the create names no data centre, and the wait does not read one
