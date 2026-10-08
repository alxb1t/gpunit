## MODIFIED Requirements

### Requirement: Boot refuses what it cannot run on

`boot.sh -- <command>` SHALL exit `1` naming the gap when `sshd`, `curl` or `env` is not on the image, or when any
of `RUNPOD_API_KEY`, `RUNPOD_POD_ID`, `PUBLIC_KEY`, `GPUNIT_CEILING` is unset or empty, or when no command follows
`--`; and SHALL stop the pod before exiting when the gap is found after the ceiling is armed.

#### Scenario: no sshd
- **Key:** `boot:refuse:no-sshd`
- **WHEN** `sshd` is not on `PATH`
- **THEN** boot exits `1` naming `openssh-server` and starts no command

#### Scenario: no curl
- **Key:** `boot:refuse:no-curl`
- **WHEN** `curl` is not on `PATH`
- **THEN** boot exits `1` naming `curl` and starts no command

#### Scenario: no env
- **Key:** `boot:refuse:no-env`
- **WHEN** `env` is not on `PATH`
- **THEN** boot exits `1` naming `coreutils` and starts no command

#### Scenario: no ceiling
- **Key:** `boot:refuse:no-ceiling`
- **WHEN** `GPUNIT_CEILING` is unset
- **THEN** boot exits `1` naming `GPUNIT_CEILING` and starts no command

### Requirement: The pod stops itself

Boot SHALL arm a timer of `GPUNIT_CEILING` seconds and an exit trap, each stopping the pod through the provider's
API with the key the provider injected; the stop SHALL retry on any answer but a success, the wait doubling from
30 seconds to 300; a 401 or 403 SHALL be logged as the key being unable to stop this pod, naming a delete by hand,
and still retried; and the command's exit, however it ends, SHALL stop the pod.

#### Scenario: the ceiling stops the pod
- **Key:** `boot:stop:ceiling`
- **WHEN** `GPUNIT_CEILING` seconds pass with the command still running
- **THEN** the stop is requested for `RUNPOD_POD_ID`

#### Scenario: the command's end stops the pod
- **Key:** `boot:stop:command-end`
- **WHEN** the command exits
- **THEN** the stop is requested

#### Scenario: a failed stop retries with backoff
- **Key:** `boot:stop:retries`
- **WHEN** the stop answers 500 twice then succeeds
- **THEN** the waits were 30 then 60 seconds and boot ends after the success

#### Scenario: a refused key is named
- **Key:** `boot:stop:refused-key-named`
- **WHEN** the stop answers 401, then 403, then succeeds
- **THEN** stderr says the key cannot stop this pod after each refusal, and the stop was retried until the success

### Requirement: The command runs as a child

Boot SHALL run the command as a child process after sshd is up, without `RUNPOD_API_KEY` in its environment,
forward `SIGTERM` to it, and exit with its code after the stop.

#### Scenario: the child's code
- **Key:** `boot:child:code`
- **WHEN** the command exits `3`
- **THEN** boot exits `3` after requesting the stop

#### Scenario: the child holds no key
- **Key:** `boot:child:no-key`
- **WHEN** boot runs a command that prints its environment
- **THEN** the printed environment holds no `RUNPOD_API_KEY`, and the stop still carries the key
