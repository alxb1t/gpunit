## ADDED Requirements

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

## MODIFIED Requirements

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
