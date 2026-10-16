---
version: v0.7
backlog: [0009·L1, 0009·R6, 0009·S3]
---

# 0010 — on-demand volumes

**A network volume that lives for a working window:** `gpunit volume up` creates the project's volume from
`gpunit.toml`, every session in the window mounts it in its data centre, and `gpunit volume down` — or the volume's own
ceiling — deletes it. The weights download once a window, and no storage bills between windows. **`v0.6`'s acceptance
closes here**, its serve runs inside a window, with its open cards.

| read | for |
|---|---|
| this file | why, and what changes |
| [design](design.md) | the seam, the verbs, the window's rules, the live runs |
| [tasks](tasks.md) | the phases, in build order |
| `specs/` | `volume` (new) · `spec` · `cli` · `session` · `serve` · `spend` |

## Why

**A volume kept forever bills between working sessions.** isekai and Synthetic Portraits each keep one
(`db7sc8cild`, `klklbwxdhu`); isekai's costs ~$3.50 a month to serve renders made a few hours a week. Without a volume,
every pod downloads the weights again.

**A window volume pays for storage only while it is used.** The operator opens a window, say four hours of renders;
the first pod fills the volume, the later pods read it, and the window's end deletes it.

**`v0.6.0` shipped without its serve runs** — `make live-serve` and `make live-serve-dead` were moved to the next
version — and with open cards: `make live-dead` never reaches the dead-pod rule (`0009·L1`), and the pinned
images carry `boot.sh` from before `681e23c` (`0009·R6`, `0009·S3`).

## What Changes

- **`gpunit volume up` / `gpunit volume down`**, reading `gpunit.toml`'s new `volume_gb`, `volume_ceiling` and
  optional `volume_datacenter` ([D2](design.md#d2), [D4](design.md#d4), [D5](design.md#d5)).
- **The data centre comes from stock:** the first card of `gpus` in stock in a data centre with standard volumes
  ([D3](design.md#d3)).
- **The window's record** is `.gpunit/volume`; every session of the window mounts that volume, and refuses a ceiling
  past the volume's ([D6](design.md#d6)).
- **The volume's ceiling:** any gpunit command after it deletes the volume first; `volume up` on a live volume extends
  it, after the price ([D5](design.md#d5), [D7](design.md#d7)).
- **`serve`:** `gpunit volume up --serve <row> --ceiling 4h` makes the row's window volume, and `serve` mounts it
  ([D8](design.md#d8)).
- **`spend`:** a volume gpunit made bills under its project; one past its ceiling is named ([D9](design.md#d9)).
- **The live runs:** `make live-volume`; `make live-serve` and `make live-serve-dead` inside a window; `make live-dead`
  reaches boot's stop ([D10](design.md#d10), `0009·L1`).
- **The images rebuilt** from `boot.sh` at HEAD and re-pinned ([D11](design.md#d11), `0009·R6`, `0009·S3`).
- **The serve image keeps the weights on a mounted volume:** its `CMD` broke on any volume ([D13](design.md#d13)).
- **The log since the create is read:** RunPod's `since` stream sends no past line ([D14](design.md#d14)).

## Capabilities

### New Capabilities

- `volume`: the window volume — its creation from the spec, its extension, its deletion, its ceiling.

### Modified Capabilities

- `spec`:
  - *The spec is one TOML file* — `volume_gb`, `volume_ceiling`, `volume_datacenter`, and their refusals.
- `cli`:
  - *The verbs and the usage exit* — `volume up` and `volume down`, from the spec or `--serve`.
- `session`:
  - *The volume pins the data centre* — a window's volume is mounted from `.gpunit/volume`.
- `serve`:
  - *A served session mounts its row's window volume* (added) — `serve` mounts the volume `volume up --serve` made.
- `spend`:
  - *The ledger names each pod gpunit learns of* — it names each window volume too, with its end.
  - *Spend reports the provider's billing by project* — a window volume bills under its project.

## Impact

- **Files:** `gpunit/provider.py`, `gpunit/runpod.py`, `gpunit/spec.py`, `gpunit/state.py`, `gpunit/ledger.py`,
  `gpunit/volume.py` (new), `gpunit/lifecycle.py`, `gpunit/cli.py`, `gpunit/serve/session.py`, `gpunit/spend.py`,
  `gpunit/serve/models.toml`, `serve/Dockerfile`, `live/gpunit.volume.toml` (new), `live/gpunit.toml`, `live/gpunit.dead.toml`,
  `live/Dockerfile.dead`, `live/last_run.txt`, `live/serve_last_run.txt`, `Makefile`, `README.md`, `CLAUDE.md`, and
  the tests.
- **The `Provider` seam:** a card's data centres in stock, the data centres with standard volumes, and a volume's
  create, listing and delete.
- **Consumers:** nothing changes until a spec sets `volume_gb`; `volume = "<id>"` keeps its meaning.
- **Dependencies:** none ([Dependencies](design.md#dependencies)).
- **Spend:** a window volume bills $0.07/GB/month while it exists — 60 GB for 4 h is ~$0.02. The live runs cost about
  $0.40 by hand ([D10](design.md#d10)).

## Not in this change

- **High-performance or global volumes** — trigger: a window whose load from a standard volume is measured slow.
- **More than one card a pod** — trigger: *a very large model*.
- **A `serve` config file** — trigger: a `serve` user running the same row every day.
- **A watcher that deletes a volume no command reaches** — it costs more than the volume; README names the residual.
- **`status --json` naming the volume** — trigger: a consumer that reads it.
- **The consumers' move to `v0.7`** — their own versions.
