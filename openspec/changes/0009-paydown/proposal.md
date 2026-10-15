---
version: v0.6
backlog: [0006·S1, 0007·R6, 0007·R7, 0008·R5]
---

# 0009 — paydown

**A pod that stops while `serve` waits or holds is torn down in seconds, and its log is kept on the laptop; the
backlog closes.** The host key carries a per-session nonce an echo cannot know, and the drift in README and the spend
spec is corrected. **A minor:** `boot.sh` prints a new host-key line, so an older `boot.sh` is refused.

| read | for |
|---|---|
| this file | why, and what changes |
| [design](design.md) | each fix, the cards it closes, and why that fix |
| [tasks](tasks.md) | the phases, in build order |
| `specs/` | `boot` · `session` · `serve` · `spend` |

## Why

**A stopped pod kept billing while `serve` waited** (2026-10-13, during `0008`'s live run). vLLM exited, `boot.sh`
stopped the pod as designed, and `serve`'s model wait went on asking `/v1/models` through a dead tunnel. Only a
SIGTERM ended it; alone it would have waited to its 1200 s bound. The wait never asks the provider for the pod's
status: `v0.3.1`'s dead-pod rule covers `up`'s SSH wait only.

**The crash's cause was lost with the container.** RunPod drops a container's log when the pod stops, and the wait
kept only the last line it printed. The cause — `max_num_seqs (256) exceeds available Mamba cache blocks (192)` — was
found on a second run, by hand, and fixed in `v0.5.0`.

**A command that echoes two attacker-chosen lines can still supply the host key** (`0006·S1`): `fingerprint` accepts
any key line a `step: the command` line follows.

## What Changes

- **A dead pod ends `serve`'s wait and its hold** on lifecycle's rule — two terminal polls in a row
  ([D1](design.md#d1)).
- **The pod's log is kept** at `~/.local/state/gpunit/serve/<model>/pod.log`; the dead-pod refusal prints its last 30
  lines and names the file ([D2](design.md#d2)).
- **BREAKING for a consumer's image — the host key carries a nonce:** gpunit gives each pod a fresh
  `GPUNIT_NONCE`; `boot.sh` prints it in its key line and keeps it from the command; gpunit accepts only the line
  with it, and refuses an older `boot.sh` by name ([D3](design.md#d3), `0006·S1`).
- **`boot.sh` waits 60 s after the command exits, before the stop**, so gpunit reads the exit line; never at the
  ceiling or on a refusal ([D4](design.md#d4)).
- **The drift:** README's exit row for `spend --days`; a scenario for the unreadable ledger, its test's tag and
  `spend`'s docstring ([D5](design.md#d5), `0007·R6`, `0007·R7`).
- **`0008·R5` and `0007·R6`'s design half close won't-fix** — they name archived text ([D6](design.md#d6)).
- **`make live-serve-dead`**, the live proof of a crash in the wait ([D7](design.md#d7)).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `boot`:
  - *Boot refuses what it cannot run on* — `GPUNIT_NONCE` is required.
  - *The pod stops itself* — the command's exit stops the pod after a 60 s wait; the ceiling and a refusal do not wait.
  - *Sshd on a fresh host key, and the fingerprint printed* — the line is `gpunit host key <nonce>: SHA256:…`.
  - *The command runs as a child* — without `GPUNIT_NONCE` either.
- `session`:
  - *The host key is verified before anything connects* — only the line with the session's nonce is the key; an older
    `boot.sh` is refused.
- `serve`:
  - *A served session waits for the model, within a bound* — a dead pod ends the wait; the log is kept.
  - *The endpoint is served on loopback with a key of its own* — a dead pod ends the hold.
- `spend`:
  - *Spend reports the provider's billing by project* — an unreadable ledger has its own scenario.

## Impact

- **Files:** `boot/boot.sh`, `gpunit/provider.py`, `gpunit/runpod.py`, `gpunit/lifecycle.py`,
  `gpunit/serve/session.py`, `gpunit/serve/models.toml`, `gpunit/spend.py`, `live/serve_dead.py` (new),
  `live/gpunit.toml`, `live/gpunit.dead.toml`, `live/last_run.txt`, `live/serve_last_run.txt`, `Makefile`,
  `README.md`, `CLAUDE.md`, and the tests.
- **The `Provider` seam:** `create` takes the nonce.
- **Consumers:** an image must `ADD` `boot.sh` from `v0.6.0`; with an older one, `up` refuses after the create and
  tears the pod down. isekai and Synthetic Portraits update their `ADD` when they move to `v0.6.0`.
- **Images:** `gpunit-vllm`, `gpunit-live` and `gpunit-live-dead` are rebuilt and their digests pinned.
- **Dependencies:** none ([Dependencies](design.md#dependencies)).
- **Spend:** a crashed command bills 60 s more before its stop, ~$0.01 on an A40. The live runs, `make live` and
  `make live-dead`, cost a few cents by hand.

## Not in this change

- **Ending a wait on the log line `the command exited`** — a command can echo it. Trigger: boot's own lines carry the
  nonce too.
- **A status check in `gpunit run`'s command phase** — its SSH session ends with the pod.
- **The bound refusal printing the kept log** — trigger: a wait that ends at its bound with no cause in sight.
- **A new live run of `qwen3.8-27b`** — only `boot.sh` changed in its image.
- **The serve runs, `make live-serve` and `make live-serve-dead`** — a fresh host pulled `gpunit-vllm` for over 15
  minutes with no SSH and nothing to see. Trigger: a network volume that holds the image's weights, in the next
  version. [D1](design.md#d1) and [D4](design.md#d4) are proven offline only until then.
- **The consumers' repos** — they move to `v0.6.0` in their own versions.
