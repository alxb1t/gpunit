## MODIFIED Requirements

### Requirement: The volume pins the data centre

The system SHALL, when `volume` is set, read the volume's data centre from the provider before any create, SHALL
refuse when the volume cannot be read, SHALL create the pod in that data centre with the volume mounted, and SHALL
tell the pod the volume's id as `GPUNIT_VOLUME_ID` and its mount path as `GPUNIT_VOLUME_PATH` in its environment.

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
