## Purpose

The pod's half of the session: one shell file a consumer's image runs as its entrypoint, so the pod stops itself
at its ceiling whatever happens to the machine that made it, and proves its host key before anything connects.

## ADDED Requirements

### Requirement: Boot refuses what it cannot run on

`boot.sh -- <command>` SHALL exit `1` naming the gap when `sshd` or `curl` is not on the image, or when any of
`RUNPOD_API_KEY`, `RUNPOD_POD_ID`, `PUBLIC_KEY`, `GPUNIT_CEILING` is unset or empty, or when no command follows
`--`; and SHALL stop the pod before exiting when the gap is found after the ceiling is armed.

#### Scenario: no sshd
- **Key:** `boot:refuse:no-sshd`
- **WHEN** `sshd` is not on `PATH`
- **THEN** boot exits `1` naming `openssh-server` and starts no command

#### Scenario: no ceiling
- **Key:** `boot:refuse:no-ceiling`
- **WHEN** `GPUNIT_CEILING` is unset
- **THEN** boot exits `1` naming `GPUNIT_CEILING` and starts no command

### Requirement: The pod stops itself

Boot SHALL arm a timer of `GPUNIT_CEILING` seconds and an exit trap, each stopping the pod through the provider's
API with the key the provider injected; the stop SHALL retry on any answer but a success, the wait doubling from
30 seconds to 300; and the command's exit, however it ends, SHALL stop the pod.

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

### Requirement: Sshd on a fresh host key, and the fingerprint printed

Boot SHALL install `PUBLIC_KEY` as the only authorized key, generate a fresh Ed25519 host key on every boot, never
serving one the image supplied, start `sshd` on a config of its own, not the image's, serving that key alone, and
print one line `gpunit host key: SHA256:<fingerprint>` to stdout.

#### Scenario: the fingerprint line
- **Key:** `boot:sshd:fingerprint-printed`
- **WHEN** boot starts
- **THEN** stdout holds exactly one line matching `^gpunit host key: SHA256:[A-Za-z0-9+/]+$`, equal to the served key's fingerprint

#### Scenario: the authorized key
- **Key:** `boot:sshd:authorized-key`
- **WHEN** boot starts with `PUBLIC_KEY` set
- **THEN** `/root/.ssh/authorized_keys` holds that key alone, at mode `0600`

### Requirement: The command runs as a child

Boot SHALL run the command as a child process after sshd is up, forward `SIGTERM` to it, and exit with its code
after the stop.

#### Scenario: the child's code
- **Key:** `boot:child:code`
- **WHEN** the command exits `3`
- **THEN** boot exits `3` after requesting the stop
