## MODIFIED Requirements

### Requirement: Boot refuses what it cannot run on

`boot.sh -- <command>` SHALL exit `1` naming the gap when `sshd` or `curl` is not on the image, or when any of
`RUNPOD_API_KEY`, `RUNPOD_POD_ID`, `PUBLIC_KEY`, `GPUNIT_CEILING` is unset or empty, or when no command follows
`--`; and SHALL stop the pod before exiting when the gap is found after the ceiling is armed.

#### Scenario: no sshd
- **Key:** `boot:refuse:no-sshd`
- **WHEN** `sshd` is not on `PATH`
- **THEN** boot exits `1` naming `openssh-server` and starts no command

#### Scenario: no curl
- **Key:** `boot:refuse:no-curl`
- **WHEN** `curl` is not on `PATH`
- **THEN** boot exits `1` naming `curl` and starts no command

#### Scenario: no ceiling
- **Key:** `boot:refuse:no-ceiling`
- **WHEN** `GPUNIT_CEILING` is unset
- **THEN** boot exits `1` naming `GPUNIT_CEILING` and starts no command

### Requirement: Sshd on a fresh host key, and the fingerprint printed

Boot SHALL install `PUBLIC_KEY` as the only authorized key, generate a fresh Ed25519 host key on every boot, never
serving one the image supplied, start `sshd` on a config of its own, not the image's, serving that key alone, to root alone,
with PAM's account check on, and print one line `gpunit host key: SHA256:<fingerprint>` to stdout.

#### Scenario: the fingerprint line
- **Key:** `boot:sshd:fingerprint-printed`
- **WHEN** boot starts
- **THEN** stdout holds exactly one line matching `^gpunit host key: SHA256:[A-Za-z0-9+/]+$`, equal to the served key's fingerprint

#### Scenario: the authorized key
- **Key:** `boot:sshd:authorized-key`
- **WHEN** boot starts with `PUBLIC_KEY` set
- **THEN** `/root/.ssh/authorized_keys` holds that key alone, at mode `0600`

#### Scenario: PAM is on
- **Key:** `boot:sshd:pam-on`
- **WHEN** boot starts sshd
- **THEN** sshd's config holds `UsePAM yes`, so a root whose password is locked with `!` still logs in by key

#### Scenario: root alone is admitted
- **Key:** `boot:sshd:root-only`
- **WHEN** boot starts sshd
- **THEN** sshd's config holds `AllowUsers root`, so a key the image baked in for another account logs no one in
