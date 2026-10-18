---
version: v0.9
backlog: [0012·R3, 0012·R4, 0012·R5, 0012·R6, 0012·R7, 0012·R8, 0012·R9]
---

# 0013 — secure and private

**gpunit closes the gaps its threat model found:** the account key stops reaching `run`'s local command, `[env]`
refuses `RUNPOD_*`, a taken tunnel port ends the session, vLLM logs no request, pod-log lines print cleaned, and
`datacenters = [...]` places pods and window volumes. What gpunit cannot protect is written down, a short metered probe
measures what RunPod leaves undocumented, and the threat model moves into the repo as `docs/threat-model.md`.

| read | for |
|---|---|
| this file | why, and what changes |
| [design](design.md) | each fix, the placement rule, the probe, the docs |
| [tasks](tasks.md) | the phases, in build order |
| `specs/` | `run` · `library` · `spec` · `session` · `volume` · `serve` · `boot` |

## Why

**The threat model, drafted from `v0.8` and RunPod's docs, found gaps a line or two each closes.** `run` hands its
command the account key (T21); a squatter on the tunnel's local port gets the traffic while gpunit reopens (T9);
`[env]` takes `RUNPOD_API_KEY` (T26); pod-log lines reach the terminal raw (T39); a pod without a volume has no
placement control (T34). Its ids are cited as `G…` (gaps) and `T…` (threats) throughout.

**Privacy is gpunit's to document, not to own.** gpunit carries a consumer's data; it puts nothing on RunPod beyond
the session's need, names where data can land, and offers placement. RunPod documents neither the pod-scoped key's
powers, nor the key permissions REST v2 needs, nor whether account SSH keys reach a pod: a probe measures them.

**The `0012` cards close** — `R5`, `R6`, `R8` and `R9` in live text; `R3`, `R4`, `R7` and `R6`'s CHANGELOG half
won't-fix ([D12](design.md#d12)).

## What Changes

- **BREAKING — `run`'s command gets no `RUNPOD_API_KEY`** (G2) ([D1](design.md#d1)).
- **`[env]` refuses `RUNPOD_*` names** (G7); a `{{ RUNPOD_SECRET_name }}` value passes as written
  ([D2](design.md#d2)).
- **`.gpunit/` is set to `0700` on every write** (G13) ([D3](design.md#d3)).
- **Pod-log lines print with control characters removed** (G11) ([D4](design.md#d4)).
- **A taken local port refuses and tears down** in place of a reopen; the busy-port probe reads `::1` too (G3)
  ([D5](design.md#d5), [D6](design.md#d6)).
- **`datacenters = [...]`**, an optional allow-list in `gpunit.toml`: the pod's create, a mounted volume, the pod's
  reported data centre and `volume up`'s stock choice are held to it (G8) ([D7](design.md#d7), [D8](design.md#d8),
  [D9](design.md#d9)).
- **Each serve row turns vLLM's request logging off** with `--no-enable-log-requests` (G9) ([D10](design.md#d10)).
- **The `0012` cards** ([D11](design.md#d11)).
- **README's *Security and privacy***: where data lands (G10), secrets, the key's permissions, the accepted risks
  (G4, G16); **`docs/threat-model.md`** at `v0.9`'s state; **`CLAUDE.md`**'s trust-boundary rule
  ([D13](design.md#d13), [D14](design.md#d14)).
- **The probe**, by hand and metered: G5, G6, G12, and `make live` and `make live-volume` on a restricted key
  ([D15](design.md#d15)).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `run`:
  - *Run hands the session over* — the command's environment holds no `RUNPOD_API_KEY`.
  - *A port already answering refuses before anything is rented* — the probe reads `127.0.0.1` and `::1`.
  - *A dead tunnel is reopened* — a taken local port refuses and tears down; only a free one is reopened.
- `library`:
  - *The tunnel stays open while the block runs* — a taken local port raises `Refused` and tears down.
- `spec`:
  - *The spec is one TOML file* — `datacenters` loads; `[env]` refuses `RUNPOD_*`; a `volume_datacenter` outside
    `datacenters` is refused.
- `session`:
  - *Pods are placed within the allow-list* (added) — the create names `datacenters`; a mounted volume outside it
    refuses; a pod reported outside it tears down.
  - *A fresh keypair per session* — `.gpunit/` is set to `0700` on every write.
  - *The wait is bounded and a timeout tears down* — `live/dead.py`'s guard gets its own scenario (`0012·R9`).
- `volume`:
  - *A window volume is created from the spec* — the stock choice stays within `datacenters`.
- `serve`:
  - *The model table names what each model serves on* — every row turns request logging off.
  - *A served session waits for the model, within a bound* — pod-log lines print cleaned.
- `boot`:
  - *Boot runs on a Python image and refuses what it lacks* — `boot:refuse:no-ca-store` (`0012·R5`).

## Impact

- **Code:** `gpunit/run.py`, `gpunit/spec.py`, `gpunit/state.py`, `gpunit/log.py`, `gpunit/serve/session.py`,
  `gpunit/library.py`, `gpunit/provider.py`, `gpunit/runpod.py`, `gpunit/lifecycle.py`, `gpunit/volume.py`,
  `gpunit/serve/models.toml`, `boot/boot.py`, and the tests.
- **Docs:** `README.md`, `CLAUDE.md`, `docs/threat-model.md` (new); `live/last_run.txt` after the probe.
- **Consumers:** a `run` command that read `RUNPOD_API_KEY` breaks; an `[env]` naming `RUNPOD_*` is refused. isekai
  gains `datacenters`.
- **The serve image:** unchanged; the rows' `args` reach vLLM through the pod's environment.
- **Dependencies:** none ([Dependencies](design.md#dependencies)).
- **Spend:** the probe, about $0.05 by hand ([D15](design.md#d15)).

## Not in this change

- **A `compliance` or country key** — the operator saw no use for it (Q7).
- **Encrypting a volume** — RunPod offers none for network volumes.
- **A change to the host-key protocol.**
- **Moving a consumer** — isekai's and Synthetic Portraits' own versions.
- **`datacenters` for `serve`** — trigger: a served model whose prompts must stay in a region.
- **Unix-socket forwards** for a shared laptop (G4) — trigger: a consumer on a shared machine.
- **The session key in the state directory** (G16) — trigger: a consumer whose project folder is synced.
- **Published `boot.py` checksums and install by commit** (G14), **a serve-image rebuild schedule** (G15) — cards at
  the release; triggers: the next release, an OpenSSH CVE or a vLLM bump.
- **Proving `{{ RUNPOD_SECRET_name }}` resolves through v2's create** — trigger: a consumer that puts a token in a
  secret.
