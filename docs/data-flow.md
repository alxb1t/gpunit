# Data flow

How data moves through a session, a boot, the state files, `serve`, the window volume and `spend`, and how an
outcome becomes an exit code. Behaviour is the specs' (`openspec/specs/`); this page is the order things happen in.

## A session

`run`, `serve` and `gpunit.session` open through `gpunit/library.py::open_session`, which calls
`gpunit/lifecycle.py::up` and owns the tunnel and the teardown. The `up` verb calls `gpunit/lifecycle.py::up` alone,
and leaves the pod for `down` ([D27](decisions.md#d27--session-is-a-context-manager-over-open_session-run-is-its-first-caller)).

```
 checks ──▶ place ──▶ create ──▶ wait ──▶ host key ──▶ tunnel ──▶ command ──▶ teardown
   │          │         │         │          │            │                      ▲
 spec,      catalogue  pending,  mapped,   log line     ssh -N -L               │
 record,    floor,     then      in        = keyscan    per loopback            │
 tools,     one card   record    datacenters            family                  │
 ports      at a time                                                           │
   └────────────── any refusal after the create ────────────────────────────────┘
```

- **Checks** run before any request: the spec, the record and `pending`, the ssh tools, the local ports
  ([D24](decisions.md#d24--gpunits-ssh-is-its-own-the-tools-checked-before-any-request)). The window's sweep runs
  first ([D43](decisions.md#d43--every-session-mounts-the-window-the-sweep-runs-first)).
- **Place and create:** one create per card; a 400 moves on, anything else is `Lost`
  ([D19](decisions.md#d19--placement-the-catalogue-floor-one-create-per-card-a-400-moves-on-the-rest-is-lost)).
- **Wait:** a bounded poll until the pod's port 22 is mapped; two dead polls end it, and a pod outside
  `datacenters` is torn down ([D21](decisions.md#d21--the-wait-a-bounded-poll-a-failed-read-is-not-yet-two-dead-polls-end-any-wait),
  [D26](decisions.md#d26--a-pod-outside-datacenters-is-torn-down)).
- **Host key:** `gpunit/hostkey.py::verify` reads the log, scans the port, compares, and writes `known_hosts`
  ([D22](decisions.md#d22--the-host-key-is-proven-over-the-log)).
- **Tunnel and command:** `gpunit/library.py::_Tunnel` forwards the spec's ports; `run`'s command gets
  `GPUNIT_HOST`, `GPUNIT_SSH` and a `GPUNIT_PORT_<remote>` per port.
- **Teardown:** on every way out of the block, signals ignored, only when a create began here or was lost
  ([D20](decisions.md#d20--teardown-only-when-a-create-began-here-or-was-lost)).

## The boot contract

What the laptop tells the pod, and what boot prints back over RunPod's log.

```
 laptop                              pod: boot/boot.py
 ──────                              ─────────────────
 contract.pod_env ── env ──────────▶ check the env and the command
   [env], PUBLIC_KEY,                <UTC> step: the ceiling, <n>s   watchdog armed
   GPUNIT_CEILING, GPUNIT_NONCE,     <UTC> step: sshd                fresh host key
   GPUNIT_VOLUME_ID/_PATH                gpunit host key <nonce>: SHA256:…   (stdout)
                                     <UTC> step: the command         key and nonce withheld
 contract.fingerprint ◀── log ────── <UTC> the command exited <code>
 contract.old_boot                   a grace wait, then the stop, in a finally
```

- **In:** `gpunit/contract.py::pod_env` builds the env from the spec's `[env]`, then gpunit's names, which win
  ([D12](decisions.md#d12--env-passes-as-written-names-no-gpunit_-or-runpod_-gpunits-names-win)).
- **Out:** boot's own lines go to stderr, UTC-stamped; the key line goes to stdout. `gpunit/contract.py::fingerprint`
  takes the last key line with the session's nonce that a `step: the command` line follows.
- **The stop:** the watchdog stops the pod at the ceiling; the main flow stops it in a `finally` however the command
  ends ([D46](decisions.md#d46--the-ceiling-in-a-forked-watchdog-the-stop-in-a-finally-retried)).

## The state files

In `.gpunit/` beside the spec, each written whole, the directory `0700`
([D15](decisions.md#d15--gpunit-in-the-working-directory-each-record-written-whole-the-directory-0700)).

```
 pod:     pending ──create answered──▶ pod ──down, 204──▶ (gone)
            │                           also: key, key.pub, known_hosts
            └──lost──▶ kept; the next down sweeps by name and image

 window:  volume.pending ──created──▶ volume ──volume down / past its end──▶ (gone)
```

- `pending` marks a create that may have made a pod no record names; `State.began` says this process wrote it.
- `pod` is the record: the pod's id, image, address and create time. A 404 on delete keeps it
  ([D23](decisions.md#d23--teardown-a-404-keeps-the-record-the-projects-pods-are-swept)).
- `key` and `key.pub` are the session's keypair, deleted with the pod
  ([D16](decisions.md#d16--a-keypair-per-session-deleted-at-teardown)).
- `volume` and `volume.pending` are the window's record and mark, beside the pod's.
- `serve` keeps the same files under the home directory, one directory per model
  ([D18](decisions.md#d18--serves-state-under-the-home-directory-one-session-per-model)).

## Serve

`gpunit/serve/session.py` runs a row on a session.

```
 sweep ──▶ row's spec ──▶ local port ──▶ price, y/N ──▶ open ──▶ wait /v1/models ──▶ chat
                                                                       │            or --api hold
                                                                       └── pod.log kept since the create
```

- The row comes from `gpunit/serve/table.py::rows`: the bundled table or the user file
  ([D34](decisions.md#d34--a-model-is-a-row-the-bundled-table-and-one-user-file)).
- The local port is picked before the price; nothing is rented without a `y`
  ([D35](decisions.md#d35--the-price-first-yn---yes-skips-it)).
- The wait polls `/v1/models` over the tunnel with the session's key; a dead pod ends it
  ([D36](decisions.md#d36--serves-wait-polls-v1models-the-local-port-is-picked-before-the-price)).
- Printed log lines and streamed text are cleaned; `pod.log` stays as read
  ([D39](decisions.md#d39--podlog-holds-the-log-since-the-create-printed-lines-are-cleaned)).

## The window volume

A network volume that outlives its sessions, to its own ceiling.

```
 volume up ──▶ price, y/N ──▶ create or extend ──▶ .gpunit/volume
                                                      │
 up · run · serve ──▶ mount at VOLUME_PATH ◀──────────┤
                                                      │
 every sweep: past its end? ──▶ lifecycle.delete_volume ──▶ ledger: deleted
```

- Each pod mounts the window at the provider's path, `gpunit/runpod.py::VOLUME_PATH`, and reads it as
  `GPUNIT_VOLUME_PATH`.
- `volume up` picks the data centre, then every pod of the window goes there
  ([D42](decisions.md#d42--the-windows-data-centre)).
- `gpunit/lifecycle.py::sweep_window` deletes a window past its end before a verb's work, and in `down` after its pods
  ([D43](decisions.md#d43--every-session-mounts-the-window-the-sweep-runs-first)).
- After a lost create, `volume down` asks a person at a terminal before deleting each volume of its name
  ([D41](decisions.md#d41--volume-up-and-down-the-sweep-asks-a-person-at-a-terminal)).

## Spend

```
 ledger.jsonl ──┐
 (id → project) ├──▶ join on id ──▶ by project, whole UTC days, rounded once
 pod billing  ──┤
 volume billing ┘
```

- `gpunit/ledger.py` writes a line when a pod or volume is created, swept or deleted; a failed write blocks nothing
  ([D17](decisions.md#d17--the-ledger-best-effort-to-write-refuses-to-read-spend-joins-on-it)).
- `gpunit/spend.py` reads the provider's amounts over whole UTC days; an unreadable billing is an error, never zeros
  ([D44](decisions.md#d44--spend-whole-utc-days-the-providers-amounts-one-rounding)).

## Exit codes

```
 body's code ─────────────────────────────▶ that code
 Refused ─────────────────────────────────▶ 1
 Lost ────────────────────────────────────▶ 3
 TeardownFailed ──▶ caused by Lost? ──yes─▶ 3
                                    └─no──▶ 1
 Interrupted(n), KeyboardInterrupt ───────▶ 128+n
 a usage fault ───────────────────────────▶ 2
```

`gpunit/run.py::outcome` maps the session's exceptions; `gpunit/cli.py::_run` adds the usage fault and runs the
verb ([D32](decisions.md#d32--exit-codes-0-1-2-3-128n)).
