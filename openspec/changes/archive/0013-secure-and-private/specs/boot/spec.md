## MODIFIED Requirements

### Requirement: Boot runs on a Python image and refuses what it lacks

`boot.py -- <command>` SHALL run on an image holding `python3` 3.10 or newer with its standard library, `openssh-server` and `ca-certificates`,
and SHALL need neither `curl` nor `env`. It SHALL exit `1` naming the gap when `sshd` is not on the image, when
OpenSSL finds no CA store for the stop's TLS, or when any
of `RUNPOD_API_KEY`, `RUNPOD_POD_ID`, `PUBLIC_KEY`, `GPUNIT_CEILING`, `GPUNIT_NONCE` is unset or empty, or when no
command follows `--`; and SHALL stop the pod before exiting when the gap is found after the ceiling is armed.

#### Scenario: no sshd
- **Key:** `boot:refuse:no-sshd`
- **WHEN** `sshd` is not on `PATH`
- **THEN** boot exits `1` naming `openssh-server` and starts no command

#### Scenario: the stop needs no curl
- **Key:** `boot:needs:no-curl`
- **WHEN** `curl` is not on `PATH`
- **THEN** boot runs the command, and the stop is requested with the key in a request header

#### Scenario: the command needs no env
- **Key:** `boot:needs:no-env`
- **WHEN** `env` is not on `PATH`
- **THEN** boot runs the command, with neither `RUNPOD_API_KEY` nor `GPUNIT_NONCE` in its environment

#### Scenario: no ceiling
- **Key:** `boot:refuse:no-ceiling`
- **WHEN** `GPUNIT_CEILING` is unset
- **THEN** boot exits `1` naming `GPUNIT_CEILING` and starts no command

#### Scenario: no nonce
- **Key:** `boot:refuse:no-nonce`
- **WHEN** `GPUNIT_NONCE` is unset
- **THEN** boot exits `1` naming `GPUNIT_NONCE`, prints no host-key line, and starts no command

#### Scenario: no CA store
- **Key:** `boot:refuse:no-ca-store`
- **WHEN** OpenSSL finds no CA file and no CA directory holding a file
- **THEN** boot exits `1` naming `ca-certificates`, arms no ceiling, and starts no command
