## MODIFIED Requirements

### Requirement: The pod stops itself

Boot SHALL arm a watchdog process that stops the pod after `GPUNIT_CEILING` seconds and outlives a crash of boot's
main flow, and SHALL stop the pod on every end of that main flow; each stop SHALL go through the provider's API with
the key the provider injected; the stop SHALL retry on any answer but a success, the wait doubling from 30 seconds to
300; a 401 or 403 SHALL be logged as the key being unable to stop this pod, naming a delete by hand, and still
retried; and the command's exit, however it ends, SHALL stop the pod 60 seconds after boot logs
`the command exited <code>`, so the pod's log still holds that line for a reader. The ceiling, a refusal and an error
of boot's own SHALL stop the pod without that wait.

#### Scenario: the ceiling stops the pod
- **Key:** `boot:stop:ceiling`
- **WHEN** `GPUNIT_CEILING` seconds pass with the command still running
- **THEN** the stop is requested for `RUNPOD_POD_ID`, with no 60-second wait before it

#### Scenario: the command's end stops the pod
- **Key:** `boot:stop:command-end`
- **WHEN** the command exits
- **THEN** boot logs `the command exited <code>`, waits 60 seconds, and then the stop is requested

#### Scenario: a refusal stops without the wait
- **Key:** `boot:stop:refusal-no-grace`
- **WHEN** boot refuses after the ceiling is armed, before the command starts
- **THEN** the stop is requested with no 60-second wait before it

#### Scenario: an error of boot's own stops the pod
- **Key:** `boot:stop:own-error`
- **WHEN** boot's main flow raises an error it did not expect, after the ceiling is armed
- **THEN** the stop is requested with no 60-second wait before it, and boot exits non-zero

#### Scenario: a failed stop retries with backoff
- **Key:** `boot:stop:retries`
- **WHEN** the stop answers 500 twice then succeeds
- **THEN** the waits after the stop's attempts were 30 then 60 seconds and boot ends after the success

#### Scenario: a refused key is named
- **Key:** `boot:stop:refused-key-named`
- **WHEN** the stop answers 401, then 403, then succeeds
- **THEN** stderr says the key cannot stop this pod after each refusal, and the stop was retried until the success

## ADDED Requirements

### Requirement: Boot runs on a Python image and refuses what it lacks

`boot.py -- <command>` SHALL run on an image holding `python3` 3.10 or newer with its standard library, `openssh-server` and `ca-certificates`,
and SHALL need neither `curl` nor `env`. It SHALL exit `1` naming the gap when `sshd` is not on the image, or when any
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

### Requirement: Boot is one file a consumer adds alone

Boot SHALL be one file, `boot/boot.py`, that imports nothing but Python's standard library and nothing of gpunit, so
a consumer's image adds it alone; and it SHALL parse and run on Python 3.10.

#### Scenario: the standard library alone
- **Key:** `boot:file:stdlib-only`
- **WHEN** boot's imports are read
- **THEN** each names a module of Python's standard library, and none names `gpunit`

## REMOVED Requirements

### Requirement: Boot refuses what it cannot run on

**Reason:** boot is `boot.py` now, and needs neither `curl` nor `env`; the requirement's *no curl* and *no env*
scenarios named refusals that no longer happen.

**Migration:** *Boot runs on a Python image and refuses what it lacks* holds the same refusals; `boot:refuse:no-curl`
and `boot:refuse:no-env` become `boot:needs:no-curl` and `boot:needs:no-env`.
