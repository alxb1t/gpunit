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
