# Design — 0002 paydown

How each card of `0001-core`'s backlog closes: the fix, where it lands, and the test that holds it.
**Verdict: feasible.** Every fix is a few lines in a file the card names, re-checked at HEAD.

## Context

See [proposal](proposal.md) — *Why*. What holds at the cut, `main` at `eef8983`:

- **The ssh line** is built once, by `ssh_command` (`gpunit/session.py:83-96`): `ssh -i <key> -o
  UserKnownHostsFile=… -o StrictHostKeyChecking=yes root@<host> -p <port>`. `run`'s tunnel (`gpunit/run.py:125-134`)
  and `GPUNIT_SSH` (`gpunit/run.py:105`) reuse it. No `-F`, no `IdentitiesOnly`.
- **The tool check** in `up` names `ssh-keygen` alone (`gpunit/session.py:51-52`); `_scan` runs `ssh-keyscan` after
  the create (`gpunit/session.py:299-310`). `ssh()` calls `os.execvp` bare (`gpunit/session.py:106`); `cli.py:95`
  says `return FAILED  # reached only when the exec failed`, which an `OSError` never reaches.
- **The port parser** `_port` (`gpunit/spec.py:132-141`) checks types only.
- **The opener** is `urllib.request.build_opener()` (`gpunit/runpod.py:59`), whose `HTTPRedirectHandler` follows a
  3xx and copies the `Authorization` header `add_header` set (`gpunit/runpod.py:208`). `_call` (`:215-223`) already
  turns any `HTTPError` into an `_Answer` with its status.
- **A delete's success:** `RunPod.delete` logs on anything but `200`/`204` (`gpunit/runpod.py:193`); `down` clears
  the record and counts a sweep only on `204` (`gpunit/session.py:139`, `:163`).
- **The log read** opens the stream with `timeout=LOG_READ_S` (10) and reads until a 10 s deadline
  (`gpunit/runpod.py:142-157`). `fingerprint()` keeps the **last** match: a restarted container prints a new key
  (`gpunit/provider.py:26`), and `test_the_logs_last_fingerprint_wins` pins it.
- **`_supervise`** returns `command.wait()` raw (`gpunit/run.py:117`), `-9` for a `SIGKILL`; it reopens a dead
  tunnel on the next 1 s poll, with no wait (`gpunit/run.py:120-122`).
- **Boot's sshd config** (`boot/boot.sh:69-76`) has no `UsePAM`, so it is `no`.
- **The curl refusal** is a case of `test_a_missing_tool_refuses`, under the `boot:refuse:no-sshd` mark
  (`tests/test_boot.py:163-166`).
- **README** links `openspec/changes/0001-core/design.md` (`README.md:15`), dead since the archive, and pins
  `v0.1.0` (`README.md:44`, `:55`).
- **`live/Dockerfile`** copies `boot/boot.sh` from the tree, so a changed `boot.sh` needs a rebuilt image and a new
  digest in `live/gpunit.toml`.

## Goals / Non-Goals

**Goals:** close each card with the fix it names or the one the grilling chose; a test bound to a scenario key
for each; `make live` on the changed ssh line and boot.

**Non-Goals:** a new verb, key or exit code; a change to the `Provider` seam; editing the archived `0001-core`.

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| [D1](#d1) | `ssh_command` opens with `-F none -o IdentitiesOnly=yes` (S4) | a `Host *` block brings ControlMaster, ProxyCommand and LocalForward as well as the agent; pods are on public IPs | `-o ForwardAgent=no` alone |
| [D2](#d2) | `up` checks `ssh`, `ssh-keygen`, `ssh-keyscan` in one refusal; `ssh()` refuses on `OSError` (R5, R6) | a missing tool after the create leaks a pod; a traceback is not a refusal | checking in `_scan` |
| [D3](#d3) | `_port` refuses a remote or local port outside 1–65535 (R9) | a typo rents a pod for a forward that cannot bind | clamping |
| [D4](#d4) | the opener follows no redirect (S3) | the API has no legitimate redirect, and `_call` already reads a 3xx safely | `add_unredirected_header` |
| [D5](#d5) | one success set `DELETED = (200, 204)` in `gpunit/provider.py` (R7) | `down` and `RunPod.delete` must agree | `204` alone |
| [D6](#d6) | the log read ends on a quiet stream: a 3 s per-read timeout under the 10 s cap (R8) | the history arrives as a burst; last-wins holds; the seam stays | stopping at the first host-key line |
| [D7](#d7) | a negative code from `wait()` becomes `128 - code` (R3) | a shell's convention: `137` for `SIGKILL` | passing `-9` through |
| [D8](#d8) | `_Backoff`: 1 s doubling to 30 s before each reopening, reset after a tunnel lived 30 s (R4) | a tunnel that cannot bind floods stderr; a blip an hour later waits 1 s | a fixed wait |
| [D9](#d9) | `UsePAM yes` in boot's sshd config (R13) | a `!`-locked root logs in by key; an sshd built without PAM only warns | a README requirement on root |
| [D10](#d10) | the curl case leaves the parametrized test for its own, under `boot:refuse:no-curl` (R12) | a scenario key must name what its tests prove | relabelling the parametrize |
| [D11](#d11) | README: the archived link, the pins at `v0.1.1`, the ssh line, the `128+n` row | the README is what a consumer copies | — |
| [D12](#d12) | R10 closes moot | the archived design is history; no change edits it | editing the archive |
| [D13](#d13) | `make live` by hand on a rebuilt `live` image | the gate fakes ssh and sshd; `-F none` and `UsePAM` change the live path | trusting the stubs |

### D1

`ssh_command` returns `["ssh", "-F", "none", "-o", "IdentitiesOnly=yes", "-i", <key>, …]`; the rest is unchanged.
The tunnel and `GPUNIT_SSH` inherit it. `-F none` reads neither `~/.ssh/config` nor `/etc/ssh/ssh_config`
(`man ssh`, OpenSSH 10.3p1). `IdentitiesOnly=yes` still matters without a config: an agent's keys are offered by
default.

### D2

`up` runs `shutil.which` on `ssh`, `ssh-keygen` and `ssh-keyscan` before anything else. When any is missing it
refuses `"not on PATH: <names>; install OpenSSH"`, with the missing names in that order. `ssh()` wraps the exec:
`OSError` → `log.refuse(f"ssh could not be run: {fault}")`. `cli.py:95`'s comment becomes
`# unreachable: the exec replaces this process, or ssh() refuses`.

### D3

`_port` refuses, naming `ports` and the value, when `remote` or `local` is outside 1–65535. This check runs after
the type check.

### D4

`class _NoRedirect(urllib.request.HTTPRedirectHandler)` with `redirect_request` returning `None`; the default
opener is `build_opener(_NoRedirect)`. urllib then raises the 3xx as an `HTTPError`, which `_call` reads as an
`_Answer`. A 3xx on create is `Lost`, on delete a kept record, on `get` a failed poll, on `list` a `Lost`. Tests:
`RunPod`'s default opener holds a `_NoRedirect`, its `redirect_request` answers `None`, and a scripted 302 on
create raises `Lost`.

### D5

`DELETED = (200, 204)` sits beside `pod_name` in `gpunit/provider.py`. `RunPod.delete` logs when
`status not in DELETED`, and `down` tests `code in DELETED` for the recorded pod and the sweep.

### D6

`LOG_IDLE_S = 3` in `gpunit/runpod.py`. The stream opens with `timeout=LOG_IDLE_S`, so each read waits at most
3 s. The 10 s deadline stays the cap. A `TimeoutError` is an `OSError`, so the existing `except` returns what
arrived. Test: a `FakeOpener` stream that sends an earlier boot's host-key line and this boot's, then raises
`TimeoutError`, returns what arrived, this boot's fingerprint winning, and was opened with `timeout == LOG_IDLE_S`.

### D7

`_supervise` keeps `wait()`'s code and returns `128 - code` when it is negative. Test: `gpunit run -- bash -c
'kill -9 $$'` exits `137`.

### D8

`_Backoff` lives in `gpunit/run.py` and holds the next wait and the time the tunnel opened. `REOPEN_FIRST_S = 1.0`
and `REOPEN_CAP_S = 30.0` are module constants.

```
tunnel exits at t ──▶ lived ≥ 30 s? ──yes──▶ wait = 1
                            │ no
                            ▼
                      reopen at t + wait; wait = min(wait × 2, 30)
```

`_supervise` asks `_Backoff.due(now)` on each poll and reopens only when it answers yes. It logs once per exit:
`the tunnel exited (<code>); reopening it in <n>s`. A unit test drives `_Backoff` with explicit times.
`test_a_dead_tunnel_is_reopened` sets `REOPEN_FIRST_S` to `0.1`.

### D9

`UsePAM yes` goes into the heredoc at `boot/boot.sh:69-76`, after `PasswordAuthentication no`. With
`KbdInteractiveAuthentication no` and `PasswordAuthentication no`, PAM adds only its account check. The new test
reads boot's config and finds the line. `AllowUsers root` follows it (0002·S1): with PAM on, sshd no longer refuses a
`!`-locked account itself, so boot admits root alone, and a key the image baked in for another account opens nothing.

### D10

`test_a_missing_tool_refuses` splits into `test_no_sshd_refuses` (`boot:refuse:no-sshd`) and `test_no_curl_refuses`
(`boot:refuse:no-curl`). Both call one helper that takes the tool and the words it is named by.

### D11

`README.md:15` → `The design: [openspec/changes/archive/0001-core/design.md](openspec/changes/archive/0001-core/design.md).`
The `ADD` URL and `uv add` pin `v0.1.1`. One spend-rule bullet: **gpunit's ssh is its own** — no ssh_config is
read, only the session's key is offered; a user who wants their own config runs `ssh -i .gpunit/key` themselves.
The `128+n` row adds a command killed by signal `n`.

### D12

R10 asked to fix D1's tree in `0001-core`'s design before the archive. The archive happened first, and an archived
design is a record, not a live page. The card closes moot: it is listed under `backlog:` and no task touches it.

### D13

A **HUMAN · METERED** phase: rebuild `live/Dockerfile` for `linux/amd64`, push it, write the new digest into
`live/gpunit.toml`, run `make live` with `RUNPOD_API_KEY` set, and append the run's tail to `live/last_run.txt`.
It proves `GPUNIT_SSH` connects under `-F none` to a boot whose sshd runs on `UsePAM yes`, the host key verifies, and
`nvidia-smi` runs. `live/gpunit.toml` sets no `ports`, so no tunnel opens: the tunnel's `-F none` line is checked
against the gate's stubs only. The image predates `AllowUsers root` (0002·S1), which the stub-backed boot test holds.

## Dependencies

None.

## Risks / Trade-offs

- **A user who wants their ssh_config on `gpunit ssh` loses it** → they run `ssh` with `.gpunit/key` themselves;
  README says so.
- **`-F none` is missing on an old OpenSSH** → `make live` proves it on this machine; Ubuntu 22.04's OpenSSH 8.9
  documents it. A failure refuses visibly; it rents nothing new.
- **A slow connect to the log endpoint takes more than 3 s** → that read returns empty, and the host-key poll
  retries every 5 s within its 60 s.
- **A command that logs at least every 3 s keeps the read open to the 10 s cap** → the stream is live after its
  backfill, so it never goes quiet, even once this boot's host-key line has arrived. The cost is at most 0.1.0's;
  ending the read at that line would break last-wins over a backfill still arriving, so the cap stays the bound.
- **`UsePAM yes` on an image whose PAM stack denies root** → the scan still verifies the host key, and `ssh` fails
  visibly; the ceiling bounds the spend.

## Verdict

Feasible. Every fix is local to the file its card names. The `make live` phase proves the ssh and boot changes
on a real pod before release.
