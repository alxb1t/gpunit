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
(default 420); SHALL read a failed poll as not yet, never as an abort; and on the deadline SHALL tear the pod down
and exit `1`.

#### Scenario: the deadline tears down
- **Key:** `session:wait:deadline-tears-down`
- **WHEN** no poll answers a host and a port within `timeout`
- **THEN** the pod is deleted, no record remains, and `up` exits `1`

#### Scenario: a failed poll is not yet
- **Key:** `session:wait:failed-poll-is-not-yet`
- **WHEN** one poll answers 500 and the next answers a host and a port
- **THEN** the wait continues and the session proceeds

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

### Requirement: The volume pins the data centre

The system SHALL, when `volume` is set, read the volume's data centre from the provider before any create, SHALL
refuse when the volume cannot be read, and SHALL create the pod in that data centre with the volume mounted.

#### Scenario: the create carries the volume's data centre
- **Key:** `session:volume:pins-datacenter`
- **WHEN** `volume = "v1"` and the provider says `v1` is in `EU-RO-1`
- **THEN** the create names `EU-RO-1` and mounts `v1`

#### Scenario: an unreadable volume refuses
- **Key:** `session:volume:unreadable-refuses`
- **WHEN** the volume read answers 404
- **THEN** `up` refuses naming the volume id and makes no create

### Requirement: A fresh keypair per session

The system SHALL generate an Ed25519 keypair into `.gpunit/key` and `.gpunit/key.pub` at mode `0600` before the
create, SHALL pass the public key to the pod, and SHALL delete both at teardown.

#### Scenario: the keypair is made and passed
- **Key:** `session:key:fresh-per-session`
- **WHEN** `up` creates a pod
- **THEN** `.gpunit/key` exists at `0600` and the create's `PUBLIC_KEY` equals `.gpunit/key.pub`

#### Scenario: the keypair leaves with the pod
- **Key:** `session:key:deleted-at-teardown`
- **WHEN** `down` deletes the recorded pod
- **THEN** `.gpunit/key` and `.gpunit/key.pub` are gone

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
