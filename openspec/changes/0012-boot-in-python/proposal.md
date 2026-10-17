---
version: v0.8
backlog: [0011·R4]
---

# 0012 — boot in Python

**`boot/boot.py` replaces `boot/boot.sh`:** one stdlib file for Python 3.10 that prints the same log lines, so gpunit
cannot tell the two apart and no consumer is forced to move. The serve image's `sh -c` becomes `serve/launch.py`, the
`Makefile`'s inline live recipes become `live/*.py`, and the gate holds `boot/boot.py` at 100 % line and branch
coverage.

| read | for |
|---|---|
| this file | why, and what changes |
| [design](design.md) | the boot's steps, the tests, the gate, the launch, the live scripts, the images |
| [tasks](tasks.md) | the phases, in build order |
| `specs/` | `boot` · `serve` |

## Why

**The pod's half is the one part of gpunit no unit test reaches.** `boot/boot.sh` is bash, proven only end to
end against stub `curl`, `sleep`, `sshd` and `ssh-keygen`; a step cannot be tested alone, and coverage cannot
be measured.

**Shell has already broken a release.** The serve image's `CMD` is `sh -c` with an `if` for `HF_HOME`; its first form
broke every mounted volume before `v0.7.0` (`0010` design D13). The `Makefile`'s live recipes hold their logic in
inline shell no test reads.

**`0011·R4` closes won't-fix** — it names a `Verify:` in the archived `0011` tasks ([D11](design.md#d11)).

## What Changes

- **`boot/boot.py`:** Python 3.10, stdlib only, no gpunit import, one file; the steps as functions
  ([D1](design.md#d1), [D2](design.md#d2)).
- **The stop guarantee kept:** the ceiling in a forked watchdog process, the main flow in `try … finally`, `SIGTERM`
  forwarded, the 60 s grace and the stop's backoff unchanged ([D3](design.md#d3)).
- **An image needs `python3` ≥ 3.10 with its standard library, `openssh-server` and `ca-certificates`:** `curl` and `env` drop out; the stop
  goes over `urllib`, the key in a header ([D4](design.md#d4)).
- **The tests:** unit tests import `boot.py`; end-to-end tests run it against stub `sshd` and `ssh-keygen`; every
  `boot:*` scenario stays bound ([D5](design.md#d5), [D6](design.md#d6)).
- **The gate:** `pytest-cov`, and `boot/boot.py` at 100 % line and branch coverage; ruff and ty hold it to 3.10
  ([D7](design.md#d7)).
- **`boot/boot.sh` is deleted** once `boot.py` is proven; consumers keep `v0.7.0`'s by its tag URL, and gpunit keeps
  reading its lines ([D8](design.md#d8)).
- **`serve/launch.py`** sets `HF_HOME` on a volume and `exec`s vLLM, in place of `sh -c` ([D9](design.md#d9)).
- **The live recipes become `live/*.py`**, one line a target, their logic tested offline ([D10](design.md#d10)).
- **The images rebuilt** and re-pinned; `make live`, `make live-dead`, `make live-volume` and `make live-serve` on
  them ([D12](design.md#d12), [D13](design.md#d13)).
- **The handover:** README's step 2 adds `boot.py` from `v0.8.0`; `CLAUDE.md` names the new files ([D14](design.md#d14)).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `boot`:
  - *Boot refuses what it cannot run on* → *Boot runs on a Python image and refuses what it lacks* (removed and
    added) — `boot.py` on `python3` ≥ 3.10, `openssh-server` and `ca-certificates`;
    `curl` and `env` no longer needed: `boot:refuse:no-curl` and `boot:refuse:no-env` give way to
    `boot:needs:no-curl` and `boot:needs:no-env`, which say boot runs without them.
  - *The pod stops itself* — a watchdog process and a stop on every end of the main flow, in place of a timer and an
    exit trap.
  - *Boot is one file a consumer adds alone* (added) — stdlib only, no gpunit import.
- `serve`:
  - *The serve image is built on request and pinned* — `ca-certificates` in place of `curl`; `boot.py` as its entry
    point and `launch.py` as its command.

## Impact

- **Files:** `boot/boot.py` (new), `boot/boot.sh` (deleted), `serve/launch.py` (new), `serve/Dockerfile`,
  `live/volume.py`, `live/serve.py`, `live/dead.py`, `live/window.py` (new), `live/serve_dead.py`, `live/Dockerfile`,
  `live/Dockerfile.dead`, `Makefile`, `pyproject.toml`, `uv.lock`, `.gitignore`, `gpunit/serve/models.toml`,
  `live/gpunit.toml`, `live/gpunit.volume.toml`, `live/gpunit.dead.toml`, `live/last_run.txt`,
  `live/serve_last_run.txt`, `README.md`, `CLAUDE.md`, and the tests.
- **gpunit's laptop side:** unchanged. It reads the same lines, and still names `v0.6.0` to an older `boot.sh`.
- **Consumers:** nothing moves. A consumer on `boot.sh` at `v0.7.0` keeps working; one that moves `ADD`s `boot.py`
  and installs `python3`.
- **Dependencies:** `pytest-cov`, a dev dependency ([Dependencies](design.md#dependencies)).
- **Spend:** `make live`, `make live-dead`, `make live-volume` and `make live-serve` cost about $0.40 by hand ([D13](design.md#d13)).

## Not in this change

- **A log line gpunit reads, changed** — the contract stays byte for byte.
- **Dropping the acceptance of `boot.sh`'s lines** — trigger: no consumer pinned to a `boot.sh` tag.
- **Moving a consumer to `boot.py`** — isekai's and Synthetic Portraits' own versions.
- **Running the tests under a real Python 3.10** — trigger: a 3.10 interpreter on the gate's machine; ruff and ty
  hold the version until then ([D7](design.md#d7)).
- **`make live` as a script** — its recipe holds no logic, only plain commands ([D10](design.md#d10)).
