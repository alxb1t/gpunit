## ADDED Requirements

### Requirement: A served session mounts its row's window volume

`gpunit serve <model>` SHALL, when `gpunit volume up --serve <model>` has recorded a volume and `--volume` is not given,
mount that volume as a window volume of the row's `disk_gb`, under the session rules for a window volume; and SHALL
never create a volume. `volume up --serve <model>` SHALL size the volume by the row's `disk_gb` and choose its data
centre from the row's cards. The serve image SHALL keep the model's weights under `GPUNIT_VOLUME_PATH` when it is
set, and start vLLM either way.

#### Scenario: serve mounts the row's volume
- **Key:** `serve:volume:window-mounted`
- **WHEN** `volume up --serve qwen3-4b --ceiling 1h --yes` recorded `v3`, and `serve qwen3-4b --ceiling 30m` runs
- **THEN** the create mounts `v3` in its data centre, and the pod is told `GPUNIT_VOLUME_PATH=/runpod-volume`

#### Scenario: serve never makes a volume
- **Key:** `serve:volume:never-created`
- **WHEN** no volume is recorded for the row, and `serve qwen3-4b --ceiling 30m` runs
- **THEN** no volume is created, and the pod mounts none

#### Scenario: the image keeps the weights on the volume
- **Key:** `serve:volume:weights-on-the-volume`
- **WHEN** the serve image's command runs with `GPUNIT_VOLUME_PATH=/runpod-volume`, and again with it unset
- **THEN** vLLM starts with the row's arguments both times, its `HF_HOME` `/runpod-volume/huggingface` the first time and unset the second
