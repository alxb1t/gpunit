## MODIFIED Requirements

### Requirement: The serve image is built on request and pinned

The serve image SHALL be built from vLLM's image named by digest, with an SSH server, `ca-certificates`, no baked host
key, telemetry off, gpunit's boot script as its entry point and gpunit's launch script as its command; SHALL be built
only on a manual request naming a tag other than `latest`; and its digest SHALL be the one the model table records.

#### Scenario: the image is built from pinned inputs
- **Key:** `serve:image:pinned-inputs`
- **WHEN** the serve image's build file is read
- **THEN** its base carries a digest, the SSH server's install deletes its host keys and holds no `curl`, its entry
  point is `python3` running the boot script, and its command is `python3` running the launch script

#### Scenario: only a request builds
- **Key:** `serve:image:only-a-request-builds`
- **WHEN** the serve image's workflow is read
- **THEN** a manual request is its only trigger, `latest` is refused, and the digest is written to its summary
