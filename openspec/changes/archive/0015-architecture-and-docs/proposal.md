---
version: v0.11
---

# 0015 — architecture and docs

**`docs/` becomes the guide to working in gpunit: the architecture on one page, its principles, the decisions in
force, the data flow, the modules and their layers, how to extend it, and what is pinned. A layer test and a links
test hold it true.** First, refactors that change no behaviour give the guide a clean shape to describe.

| read | for |
|---|---|
| this file | why, and what changes |
| [design](design.md) | the refactor bar, the moves, the layer rule, the layer and links tests, each page, the proof |
| [tasks](tasks.md) | the phases, in build order |
| `specs/` | `architecture` (new) |

## Why

**Nothing in the repo says how gpunit is built, or holds it.** `docs/` holds only the threat model. The `### D…`
sections of the archived designs mark none as in force. `CLAUDE.md`'s *Layout* is a list of files. No test holds
an import rule, and one cycle exists: `gpunit.runpod` → `gpunit` → `gpunit.library` → `gpunit.runpod`. A person or an
agent who comes to change gpunit has to read every archived design to learn what still holds.

**The code has seams worth fixing before the guide describes them.** The boot-log contract lives in the provider seam.
`lifecycle.py` proves the host key beside five other jobs. The real session seam is a private name, `library._open`.
The provider's 400 and gpunit's refusal are both called `Refused`. Each volume delete writes its own ledger line. Every one of these is a move or a
rename.

## What Changes

- **A refactor changes no behaviour:** no spec scenario, message or exit code changes; tests change only in names
  and imports ([D1](design.md#d1)).
- **`gpunit/version.py`** holds `__version__`, which breaks the cycle ([D2](design.md#d2)). **`cli` imports
  `serve.table` lazily** ([D3](design.md#d3)).
- **`library._open` → `library.open_session`** ([D4](design.md#d4)). **`provider.Refused` → `provider.Unplaceable`**
  ([D5](design.md#d5)). **`lifecycle.delete_volume`** is the one volume delete ([D6](design.md#d6)).
- **`gpunit/contract.py`** holds the laptop's half of the boot contract: the pod's env, the boot-log lines,
  `fingerprint` and `old_boot` ([D7](design.md#d7)). **`gpunit/hostkey.py`** proves the host key
  ([D8](design.md#d8)).
- **`tests/test_layers.py`** holds the layers, lazy imports included, plus the stdlib-only, `sys.exit` and
  provider-construction rules ([D9](design.md#d9)).
- **`tests/test_docs.py`** holds every link, anchor, decision id and symbol citation in `docs/`, `README.md` and
  `CLAUDE.md` ([D10](design.md#d10)). **Code cites `decision Dn`**, never an archived design
  ([D11](design.md#d11)).
- **`docs/decisions.md`** lists the decisions in force ([D12](design.md#d12)). **`docs/principles.md`** lists the
  words and the rules, each with what holds it ([D13](design.md#d13)).
- **`docs/modules.md`, `docs/data-flow.md`, `docs/extending.md`, `docs/pins.md`** ([D14](design.md#d14)). **The threat
  model cites symbols, not lines; T13 and T30 become `partly`** ([D15](design.md#d15)).
- **`docs/README.md`** is the map. **`README.md`** keeps the user's guide. **`CLAUDE.md`** becomes the agent's entry
  point ([D16](design.md#d16)).
- **One `make live`** after the moves, by hand and metered ([D17](design.md#d17)).

## Capabilities

### New Capabilities

- `architecture`: the repo's shape and its guide hold each other.
  - *The modules import down the layers* (added): the layer table, lazy imports, no cycle, nothing imports `gpunit`
    itself, `runpod` imported only where a provider is built, stdlib only, `sys.exit` in `cli` alone, every module
    named in `docs/modules.md`.
  - *The guide's citations resolve* (added): links and anchors, decision ids, `path::symbol` citations, no line
    citations, no archived-design citation left.

### Modified Capabilities

None. No existing requirement changes ([D1](design.md#d1)).

## Impact

- **Code:** `gpunit/__init__.py`, `gpunit/version.py` (new), `gpunit/contract.py` (new), `gpunit/hostkey.py` (new),
  `gpunit/provider.py`, `gpunit/runpod.py`, `gpunit/lifecycle.py`, `gpunit/volume.py`, `gpunit/library.py`,
  `gpunit/run.py`, `gpunit/cli.py`, `gpunit/serve/session.py`, `pyproject.toml`. Comments in `gpunit/`, `boot/`,
  `serve/`, `live/`, `tests/`, `.github/`, `Makefile` and `pyproject.toml`.
- **Tests:** `tests/test_layers.py` and `tests/test_docs.py` (new); imports and names in `tests/test_library.py`,
  `tests/test_up.py`, `tests/test_volume.py`, `tests/test_runpod.py` and `tests/test_boot.py`.
- **Docs:** `docs/README.md`, `docs/principles.md`, `docs/decisions.md`, `docs/data-flow.md`, `docs/modules.md`,
  `docs/extending.md`, `docs/pins.md` (new); `docs/threat-model.md`, `README.md`, `CLAUDE.md`.
- **Consumers:** none break. `gpunit.session`, `gpunit.Refused` and every verb are unchanged. `library._open` and
  `provider.Refused` were private.
- **Images:** no rebuild. `boot/boot.py` changes in comments alone.
- **Dependencies:** none ([Dependencies](design.md#dependencies)).
- **Spend:** one `make live` on the cheapest card, cents, by hand ([D17](design.md#d17)).

## Not in this change

- **The provider seam made provider-neutral:** HTTP statuses as results (F3), RunPod's words outside `runpod.py`
  (F5), one construction site (F2), boot's stop per provider (F14), one card filter (F10). Trigger: the Vast.ai cut.
- **`gpunit/tunnel.py`** (F8). Trigger: the next tunnel change.
- **One price prompt and one Ctrl-C rule** (F9, F20). Trigger: the paydown that closes `0014·R5`, `R6`, `S1` and
  `S2`.
- **`serve` as a Python call** (F24). Trigger: an agent that needs more than the URL and key the CLI prints.
- **`0014·R5`, `R6`, `S1`, `S2`:** the launcher-flag fix. The threat model only stops claiming it holds
  ([D15](design.md#d15)).
- **Overturned decisions in `docs/`:** the archive keeps them ([D12](design.md#d12)).
- **Small duplicates, the ledger's `kind`, `CLOCK` in its own module, the test seams** (F16–F19, F22). Trigger: the
  file is open for another reason.
