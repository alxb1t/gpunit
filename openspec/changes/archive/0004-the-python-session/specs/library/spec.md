## Purpose

A GPU session for a consumer written in Python: one `with` block that opens it, yields what the consumer needs to
reach the pod, and tears it down on every way out — the failures raised, the signals and the tunnel gpunit's.

## ADDED Requirements

### Requirement: A session opens and closes in one block

`gpunit.session(spec, environ=…, cwd=…)` SHALL open a session as `up` does, refusing a busy local port first, and
SHALL yield an object naming the pod's host, the local port each spec'd remote port is forwarded to, an `ssh`
command line, the booted image and the pod's id. The block's end, however it ends, SHALL tear the session down as
`down` does, once a create began.

#### Scenario: the block sees the session
- **Key:** `library:session:yields-the-session`
- **WHEN** a block opens a session with `ports = [8188]`
- **THEN** `s.host`, `s.port(8188)`, `s.ssh`, `s.image` and `s.pod_id` name the recorded pod, and `s.port(8188)` accepts a connection

#### Scenario: the block's end tears down
- **Key:** `library:session:exit-tears-down`
- **WHEN** the block ends normally
- **THEN** the pod is deleted and `.gpunit/pod` is gone

#### Scenario: an error in the block tears down
- **Key:** `library:session:error-tears-down`
- **WHEN** the block raises `ValueError`
- **THEN** the pod is deleted and the `ValueError` reaches the caller

### Requirement: Failures are exceptions

The session SHALL raise `gpunit.Refused` when it refused, with nothing rented or what it rented torn down;
`gpunit.Lost` when a create's answer was lost, after a teardown was attempted; and `gpunit.TeardownFailed` when
the teardown failed, chained to whatever ended the block, or to the refusal whose own teardown failed while the
session opened.

#### Scenario: a refusal raises Refused
- **Key:** `library:errors:refused`
- **WHEN** a pod is already recorded
- **THEN** opening raises `Refused` and makes no create

#### Scenario: a lost create raises Lost
- **Key:** `library:errors:lost`
- **WHEN** the create answers 503
- **THEN** opening raises `Lost` after the sweep was attempted

#### Scenario: a failed teardown raises TeardownFailed
- **Key:** `library:errors:teardown-failed`
- **WHEN** the block ends and the delete answers 404
- **THEN** `TeardownFailed` is raised and `.gpunit/pod` remains

#### Scenario: a refusal whose teardown failed raises TeardownFailed
- **Key:** `library:errors:refusal-teardown-failed`
- **WHEN** the pod gets no host within the timeout and the teardown's delete answers 500
- **THEN** `TeardownFailed` is raised from the `Refused`, and `.gpunit/pod` remains

### Requirement: Signals end the block, never the teardown

While a session is open, `SIGINT`, `SIGTERM` and `SIGHUP` SHALL raise `gpunit.Interrupted`, a `KeyboardInterrupt`
naming the signal; during the teardown all three SHALL be ignored; the caller's handlers SHALL be restored when
the session closes; and opening a session off the main thread SHALL be refused.

#### Scenario: SIGTERM ends the block and tears down
- **Key:** `library:signals:term-raises`
- **WHEN** `SIGTERM` arrives inside the block
- **THEN** `Interrupted` with `signal` `15` is raised, and the pod is deleted

#### Scenario: a signal during the teardown is ignored
- **Key:** `library:signals:teardown-shielded`
- **WHEN** `SIGINT` arrives while the teardown's delete runs
- **THEN** the teardown runs to its end

#### Scenario: the caller's handlers come back
- **Key:** `library:signals:handlers-restored`
- **WHEN** the session closes
- **THEN** the handlers for `SIGINT`, `SIGTERM` and `SIGHUP` are the ones set before it opened

#### Scenario: another thread is refused
- **Key:** `library:signals:main-thread-only`
- **WHEN** a session is opened from a thread other than the main one
- **THEN** `Refused` is raised and no request is made

### Requirement: The tunnel stays open while the block runs

The session SHALL forward each spec'd port over one `ssh -N -L` child, SHALL reopen it when it exits, waiting 1
second at first and doubling to 30, reset after a tunnel lived 30 seconds, SHALL log each reopening, and SHALL stop
watching it before the teardown.

#### Scenario: a dead tunnel is reopened
- **Key:** `library:tunnel:reopened`
- **WHEN** the tunnel child exits while the block runs
- **THEN** a new tunnel child is started and the log says so

### Requirement: The caller owns the log and the environment

The session SHALL send each of gpunit's lines to the `say` callable it is given, and to stderr when none is; and
SHALL read the provider's key from the `environ` mapping it is given, and from the process's environment only when
none is.

#### Scenario: the lines go to the sink
- **Key:** `library:say:sink`
- **WHEN** a session opens and closes with a `say` that collects lines
- **THEN** the collected lines hold `session up` and `deleted`, and nothing of gpunit's reaches stderr

#### Scenario: the key comes from the mapping
- **Key:** `library:environ:key-from-mapping`
- **WHEN** `RUNPOD_API_KEY` is unset in the process and given in `environ`
- **THEN** the session opens, and the requests carry the mapping's key
