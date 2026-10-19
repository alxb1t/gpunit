# Design — 0015 architecture and docs

How the code moves, how the layer and links tests hold the guide, and what each page of `docs/` says. **Verdict:
feasible.** Every refactor here is a move or a rename that the existing tests already cover. The pages are written from
seed tables kept here ([Seed: decisions](#seed-decisions), [Seed: principles](#seed-principles)), so the build reads
nothing outside the repo.

## Context

See [proposal](proposal.md) — *Why*. Terms used throughout:

- **the guide** — the pages of `docs/`: `README.md`, `principles.md`, `decisions.md`, `data-flow.md`, `modules.md`,
  `extending.md`, `pins.md`, `threat-model.md`.
- **a finding** — a fault the architecture audit found at `v0.10.0`, cited `0015·Fn`. [The findings](#the-findings)
  lists those this change names.
- **an archived citation** — a comment citing an archived design by decision id: `0010 design D10`, `(0004 D7)`.
- **a symbol citation** — `` `gpunit/lifecycle.py::up` ``, or `Class.method` after the `::`.

What holds at the cut, `main` at `5eccc80` (`v0.10.0`):

- **The cycle:** `gpunit/runpod.py` does `from gpunit import __version__, log`. `gpunit/__init__.py` sets
  `__version__` before it imports `gpunit.library`, which imports `gpunit.runpod`. `[tool.hatch.version]` reads
  `path = "gpunit/__init__.py"`. Only `RunPod._request` reads `__version__`, for its `User-Agent`.
- **The boot-log contract in the seam:** `gpunit/provider.py` holds `_HOST_KEY`, `_OLD_KEY`, `_BOOT_STEP`,
  `_BOOT_START`, `fingerprint` and `old_boot` beside the `Provider` protocol. `gpunit/lifecycle.py` imports
  `fingerprint` and `old_boot`. `tests/test_runpod.py` and `tests/test_boot.py` import `fingerprint` from
  `gpunit.provider`.
- **The pod's env:** `RunPod.create` builds `PUBLIC_KEY`, `GPUNIT_CEILING`, `GPUNIT_NONCE`, and with a volume
  `GPUNIT_VOLUME_ID` and `GPUNIT_VOLUME_PATH` (`VOLUME_PATH = "/runpod-volume"`), over `spec.env`.
- **The host-key proof:** `lifecycle._verify_host_key` reads the log through `provider.log(record.id, tail=LOG_TAIL)`,
  polls with `lifecycle._poll` (which reads `lifecycle.CLOCK`), scans with `_scan`, compares with `_fingerprint_of`,
  and calls `lifecycle._tear_down` on each failure. `LOG_WAIT_S`, `SCAN_WAIT_S` and `LOG_TAIL` are read in
  `lifecycle.py` alone. `tests/conftest.py` patches `lifecycle.CLOCK` and `lifecycle.NONCE`.
- **The private session seam:** `library._open` is called by `library.session`, `run.py` and `serve/session.py`, and by
  `tests/test_library.py`. `library._Tunnel._open` is a different method and stays.
- **`Refused`, twice:** `library.Refused = log.Refusal` is public as `gpunit.Refused`. `provider.Refused` is the
  provider's 400: raised in `runpod.py`, caught in `lifecycle._create` and `volume.up`, imported by
  `tests/test_up.py`, `tests/test_volume.py` and `tests/test_runpod.py`.
- **The volume delete, in each caller:** `lifecycle.sweep_window`, `volume.down` and `volume._sweep` each call
  `provider.delete_volume`, compare `204` and call `ledger.record_deleted`. `volume` imports `lifecycle`, so the one
  delete must live in `lifecycle`.
- **`cli`'s eager import:** `from gpunit.serve import table` at the top of `cli.py`. Only `cli._known` reads it.
  `spend`, `serve.session` and `volume` are already imported inside functions.
- **Archived citations:** 61 lines, by
  `grep -rnE "[0-9]{4} (design )?D[0-9]+" gpunit boot serve live tests Makefile pyproject.toml .github docs README.md CLAUDE.md | grep -v last_run.txt | wc -l`.
  They are in the package, `boot/boot.py`, `serve/launch.py`, `serve/Dockerfile`, `live/Dockerfile`, `live/*.py`,
  `live/models.toml`, `gpunit/serve/models.toml`, `tests/`, the image workflow, `Makefile`, `pyproject.toml` and
  `docs/threat-model.md`. `live/last_run.txt` holds more, and is a record.
- **Line citations:** `docs/threat-model.md` cites lines as `file:N` throughout. `README.md` and `CLAUDE.md` cite none.
- **Spec keys:** every test carries `@pytest.mark.spec("<key>")`, and repo properties are scenarios already
  (`serve:image:pinned-inputs`). Hence the new `architecture` capability.

### The findings

| id | finding | here |
|---|---|---|
| `0015·F1` | the import cycle through `__version__` | [D2](#d2) |
| `0015·F2` | `session()` and `cli` construct `RunPod`; no provider choice | trigger: the Vast.ai cut |
| `0015·F3` | the seam returns HTTP statuses from `delete`, `stop` and `delete_volume` | trigger: the Vast.ai cut |
| `0015·F4` | the pod's env built inside `RunPod.create` | [D7](#d7) |
| `0015·F5` | RunPod's dead statuses, stock levels, log tail, volume price and key name read outside `runpod.py` | trigger: the Vast.ai cut |
| `0015·F6` | the boot-log contract in `provider.py` | [D7](#d7) |
| `0015·F7` | `lifecycle.py` proves the host key beside its other jobs | [D8](#d8) |
| `0015·F8` | `library.py` is the session and the tunnel | trigger: the next tunnel change |
| `0015·F9` | a price prompt in `volume` and another in `serve`, with different Ctrl-C and EOF rules | trigger: the paydown of `0014·R5` |
| `0015·F10` | the card filter in `lifecycle` and again in `serve`, each with its own message | trigger: the Vast.ai cut |
| `0015·F11` | the volume delete, written in each caller | [D6](#d6) |
| `0015·F12` | `run` and `serve` call `library._open`, a private name | [D4](#d4) |
| `0015·F13` | the provider's 400 and gpunit's refusal both named `Refused` | [D5](#d5) |
| `0015·F14` | `boot.py`'s stop is RunPod's | trigger: the Vast.ai desk research |
| `0015·F15` | `cli` imports `serve.table` at load | [D3](#d3) |
| `0015·F20` | Ctrl-C at the price exits `1` for `volume up` and `130` for `serve` | trigger: the paydown of `0014·R5` |
| `0015·F21` | code cites archived designs by decision id | [D11](#d11) |
| `0015·F23` | the launcher-flag refusal matches exact names; T13 and T30 claim `mitigated` | [D15](#d15); the fix: the paydown of `0014·R5` |
| `0015·F24` | `serve` has no Python call | trigger: an agent that needs more than the CLI |

## Goals / Non-Goals

**Goals:** a reader learns from `docs/` what holds and where to change it; the gate fails when an import or a citation
breaks the guide; the moves leave every scenario as it is.

**Non-Goals:** making the provider seam neutral; any behaviour change; a doc that restates a spec or a value.

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| [D1](#d1) | a refactor changes no scenario, message or exit code; tests change in names and imports alone | the unchanged tests prove nothing moved | taking the small behaviour fixes too (`0015·F10`, `0015·F20`) |
| [D2](#d2) | `__version__` in `gpunit/version.py`, hatch's `path` following it | a foundation module breaks the cycle with no run-time lookup | `importlib.metadata.version` |
| [D3](#d3) | `cli._known` imports `serve.table` inside the function | every heavy module is imported where it is used | leaving one eager edge |
| [D4](#d4) | `library._open` → `library.open_session`, not exported from `gpunit` | the seam `run`, `serve` and the tests use gets an honest name; `session()` stays the consumer's | exporting it |
| [D5](#d5) | `provider.Refused` → `provider.Unplaceable` | one word, *refusal*, for gpunit's own refusal | keeping both |
| [D6](#d6) | `lifecycle.delete_volume(provider, volume_id) -> int` records `deleted` on a `204`; the call sites keep their messages | one copy of a step the ledger depends on; `volume` already imports `lifecycle` | `volume.delete`, which `lifecycle` cannot import |
| [D7](#d7) | `gpunit/contract.py` at the model layer: `pod_env`, the boot-log patterns, `fingerprint`, `old_boot`; `Provider.create`'s signature unchanged | both halves of the laptop's boot contract in one file; the fake and the create tests stay as they are | `create` taking the env, which changes the seam |
| [D8](#d8) | `gpunit/hostkey.py` at the lifecycle layer: `verify` returns a reason or `None`; `lifecycle` tears down; `lifecycle` passes its own `_poll` | `hostkey` cannot import `lifecycle` without a cycle; `CLOCK` and `NONCE` stay where the tests patch them | moving `_tear_down` or `CLOCK` |
| [D9](#d9) | the layers, held by `tests/test_layers.py` | the guide states a rule only a test keeps | a rule in prose alone |
| [D10](#d10) | `tests/test_docs.py` holds links, anchors, decision ids, paths, symbols, no line citations, no archived citation | docs a test holds stay true | checking links alone |
| [D11](#d11) | code cites `decision Dn`; an archived citation becomes the decision whose *Made by* holds it | the code cites what holds; the archive is reached through *Made by* | keeping archive ids resolvable |
| [D12](#d12) | `docs/decisions.md`: the decisions in force, D1–D51, each with *Why* and *Made by*; no overturned ones | the repo states what holds | a history page |
| [D13](#d13) | `docs/principles.md`: the words, then each rule with what holds it and its breach | the docs never claim more than the code holds | listing only the rules that hold |
| [D14](#d14) | `modules.md`, `data-flow.md`, `extending.md`, `pins.md` | one job a page | one long architecture page |
| [D15](#d15) | the threat model cites symbols; T13 and T30 become `partly` | line numbers drift; the claim exceeds the code | leaving the claim until the fix |
| [D16](#d16) | `docs/README.md` is the map; `README.md` the user's guide; `CLAUDE.md` the agent's entry | a reader and a contributor want different pages | — |
| [D17](#d17) | one `make live` after the moves, its tail committed | the create's env and the host-key proof moved; the fakes cannot prove the real API | no live run; every live target |

### D1

**A refactor changes no behaviour.** No spec scenario, no printed message and no exit code changes. A test changes only
where it imports or names what moved. `docs/extending.md` states it as a rule ([D14](#d14)), and `docs/decisions.md`
records it as D51 ([D12](#d12)).

The one order that moves: `lifecycle.sweep_window` and `volume.down` now write the ledger's `deleted` line before they
clear the window record, through [D6](#d6). No scenario reads that order.

### D2

`gpunit/version.py` holds `__version__ = "0.10.0"` and a docstring. `gpunit/__init__.py` does
`from gpunit.version import __version__` and drops its "Before the imports" comment. `runpod.py` does
`from gpunit.version import __version__`. `pyproject.toml`'s `[tool.hatch.version]` reads
`path = "gpunit/version.py"`. The release bumps that file.

### D3

`from gpunit.serve import table` moves from the top of `gpunit/cli.py` into `_known`, with the comment the other lazy
imports carry.

### D4

`library._open` → `library.open_session`, with a docstring. `library.session`, `run.run`, `serve/session.py` and
`tests/test_library.py` call the new name. `gpunit/__init__.py` does not export it.

### D5

`class Refused` in `gpunit/provider.py` → `class Unplaceable`, docstring unchanged. The protocol's `create` and
`create_volume` docstrings, `runpod.py`'s raises, `lifecycle._create`'s and `volume.up`'s `except`, and the imports in
`tests/test_up.py`, `tests/test_volume.py` and `tests/test_runpod.py` follow. The message each carries is unchanged.

### D6

```python
def delete_volume(provider: Provider, volume_id: str) -> int:
    """Delete the volume; on a 204, record `deleted` in the ledger. Return the status."""
```

`lifecycle.sweep_window`, `volume.down` and `volume._sweep` call it, then clear their own state and print their own
lines, as today.

### D7

`gpunit/contract.py`, docstring: the laptop's half of the boot contract — what the pod is told, and the lines it
prints back. It moves `_HOST_KEY`, `_OLD_KEY`, `_BOOT_STEP`, `_BOOT_START`, `fingerprint` and `old_boot` out of
`provider.py`, and adds:

```python
def pod_env(
    spec: Spec, pubkey: str, ceiling_s: int, nonce: str, *, volume_path: str
) -> dict[str, str]:
    """Return the pod's environment: the spec's, then gpunit's own names, which win."""
```

It returns `{**spec.env, "PUBLIC_KEY": …, "GPUNIT_CEILING": …, "GPUNIT_NONCE": …}`, plus `GPUNIT_VOLUME_ID` and
`GPUNIT_VOLUME_PATH` when `spec.volume` is set. `RunPod.create` calls it with `volume_path=VOLUME_PATH`, and keeps the
mount. `lifecycle.py`, `tests/test_runpod.py` and `tests/test_boot.py` import from `gpunit.contract`. `provider.py`
keeps the seam's types, `pod_name`, `DELETED` and the protocol.

### D8

`gpunit/hostkey.py`, docstring: the host key, proven over the authenticated log before anything connects. It moves
`LOG_WAIT_S`, `SCAN_WAIT_S`, `LOG_TAIL`, `_scan` and `_fingerprint_of` out of `lifecycle.py`, and turns
`_verify_host_key` into:

```python
def verify(
    provider: Provider, state: State, record: Record, nonce: str, poll: Poll
) -> str | None:
    """Prove the pod's host key; write known_hosts and say so, or return why not."""
```

`Poll` is a `Protocol` in `hostkey.py` with `_poll`'s signature. On an old boot, `verify` returns at once: a private
exception ends the poll. `lifecycle.up` does `if reason := hostkey.verify(..., _poll): _tear_down(spec, provider,
state, reason)`. Each reason is today's message, word for word.

### D9

```
 interface   cli · __main__ · gpunit (__init__)
 serve       serve (__init__) · serve.table · serve.chat · serve.session
 session     library · run
 lifecycle   lifecycle · hostkey · volume · spend
 cloud       runpod
 model       spec · state · provider · ledger · contract
 foundation  log · version
```

A module imports its own layer, without a cycle, and the layers below. `tests/test_layers.py` holds the table as
`LAYERS`, a dict from module to layer. Each rule is a function over a root directory, run on the repo and on a small
package under `tmp_path` that breaks it:

| rule | key |
|---|---|
| no import names a higher layer, lazy ones included; no cycle within a layer; no `import gpunit` or `from gpunit import <name>` that is not a module | `architecture:layers:hold`, `upward-caught`, `cycle-caught` |
| `gpunit.runpod`'s importers are `gpunit.library` and `gpunit.cli` | `architecture:layers:provider-built` |
| `gpunit/` and `serve/launch.py` import `sys.stdlib_module_names` or `gpunit` alone; nothing in `gpunit/` imports `boot`, `live` or `tests` | `architecture:layers:stdlib-only` |
| `sys.exit` is called in `gpunit/cli.py` alone | `architecture:layers:exit-in-cli` |
| `docs/modules.md`'s layer table names every module of `LAYERS`, each in its layer, and `LAYERS` names every file of `gpunit/` | `architecture:layers:modules-named` |

The last rule lands with `docs/modules.md` ([D14](#d14)). A new module edits `LAYERS` and `docs/modules.md` together.

### D10

`tests/test_docs.py` scans **the guide** plus `README.md` and `CLAUDE.md` for links, and **the scanned files** for
citations: `gpunit/`, `boot/`, `serve/`, `live/` but its `*last_run.txt` tails, `tests/`, `.github/`, `docs/`,
`Makefile`, `pyproject.toml`, `README.md`, `CLAUDE.md`.

| rule | key |
|---|---|
| a relative link names a file that exists; its anchor is a heading's GitHub slug in that file (`### D22 · The host key` → `#d22--the-host-key`) | `architecture:docs:links-resolve`, `link-caught` |
| each `decision Dn` in the scanned files, and each `decisions.md#dn…` link, names a `### Dn · ` heading | `architecture:docs:decisions-resolve` |
| no scanned file but `docs/decisions.md` matches `[0-9]{4} (design )?D[0-9]+` | `architecture:docs:archive-caught` |
| a backticked path under a tracked top-level directory exists; a `path.py::name` citation names a function, class or assignment the file defines, `Class.method` included; no guide page cites `file:N` | `architecture:docs:symbols-resolve` |

Each rule has a twin under `tmp_path` that breaks it. The twins build their sample archived citation by joining parts,
so `tests/test_docs.py` never matches itself. The symbol rule lands with the threat model's conversion
([D15](#d15)).

### D11

Each archived citation becomes `decision Dn`: the decision of [Seed: decisions](#seed-decisions) whose *Made by* holds
the archived id. One `decision` per id: `(decision D45, decision D46)`. A cited id that no decision holds — overturned,
or a chore — becomes the decision that overturned it, or the sentence keeps its reason and drops the citation.
`boot/boot.py` changes in comments alone, at 100 % coverage still, so no image is rebuilt.

### D12

`docs/decisions.md` follows this shape:

```markdown
### D22 · The host key is proven over the log

**The pod prints its key, with the session's nonce, before its command; the laptop compares it to the scan.** …

- **Why:** a command's output cannot supply the key, and nothing connects first.
- **Made by:** `0001·D8`, `0003·D2`, `0006·D1`, `0009·D3`, `0010·D14`, `0011·D8`, `0015·D8`.
```

It opens with what the page is for, and with the rule: a change that makes or overturns a decision edits this page, and
its own design keeps the history. The decisions are grouped under `##` headings by area. Each states the choice and
why, links the spec for behaviour, and names the file for a value ([D14](#d14)'s rule). A converge amendment with no
D-id is folded into the decision it amends, its id in *Made by*. A decision whose code the audit found disputed says
so, in one line naming the symbol (`0015·F23`). The overturned decisions are left out.

### D13

`docs/principles.md` opens with **the words**: *session*, *record*, *pending* and `began`, *refusal* vs *lost* vs
*teardown failed*, *the seam*, *the boot contract*, *the ceiling*, *the window*, *the sweep*, *a row*, *the ledger*,
*the price*. Each is defined once, in bold. Then come **the rules** of [Seed: principles](#seed-principles), grouped,
each with the decision it comes from and what holds it: test names, a gate step, `review`, or `nothing`.

A rule the code breaches names the breach by symbol and finding, unlinked: "breached: `gpunit/lifecycle.py::_delete_pods`
compares HTTP codes (`0015·F3`)". It links no backlog card.

### D14

Each page opens with what it is for. None restates a spec's behaviour or a value. It links the spec, and names the
file that holds the value.

- **`docs/modules.md`** — the layer table of [D9](#d9), as the test reads it; a diagram of the graph; one line a
  module; the construction sites of `RunPod` (`library.session`, `cli`); `cli`'s lazy edges; the test seams
  (`lifecycle.CLOCK`, `lifecycle.NONCE`, `spend.utc_now`, `log._sink`, `library.TUNNEL_POLL_S`,
  `library.REOPEN_FIRST_S`, `serve.table.load`); the session and the tunnel, both still in `library.py` (`0015·F8`).
- **`docs/data-flow.md`** — a diagram each: a session (checks → place → create → wait → host key → tunnel → command →
  teardown); the boot contract (the env in, from `gpunit/contract.py::pod_env`; the lines out, in order; the stop);
  the state files and their lifetimes (`pending` → `began` → `pod`; `volume.pending` beside `volume`); `serve` (the
  price, the wait, the chat or the hold); the window volume and its sweep; `spend`'s join through the ledger; how an
  outcome becomes an exit code (`gpunit/run.py::outcome`, `gpunit/cli.py::_run`).
- **`docs/extending.md`** — a recipe each: a verb; a `gpunit.toml` key; a bundled `serve` row; a provider, with the
  findings a second provider meets today (`0015·F2`, `F3`, `F5`, `F14`); a `boot.py` change and its image rebuild; a
  pin bump; a live proof. Each names the files to touch, the spec to change, the tests and the proof. Then the rules:
  a refactor changes no scenario; a new module edits `LAYERS` and `modules.md`; a decision edits `decisions.md`.
- **`docs/pins.md`** — each pin, where it is declared and checked, and how it moves: the vLLM base in
  `serve/Dockerfile`, the serve image in `gpunit/serve/models.toml`, the live images in `live/gpunit*.toml`, the model
  revisions, the actions by commit in `.github/workflows/build-serve-image.yml`, `uv.lock`, a consumer's `boot.py` by
  `ADD --checksum` at a tag, the OpenSpec CLI (recorded, not pinned), the Python floors (3.11 for the package, 3.10 for
  `boot.py`), and the vLLM behaviours the threat model relies on.

### D15

`docs/threat-model.md` cites symbols, not lines: `` `gpunit/serve/table.py:17` `` → `` `gpunit/serve/table.py::_row` ``,
whichever symbol holds the line. A line with no symbol of its own — a Dockerfile, a TOML key — cites the file alone.
T13 and T30 move from `mitigated` to `partly`, naming the hole: the refusal matches exact flag names, while vLLM
`v0.31.0` takes abbreviations and rewrites argv (`0015·F23`). The *Counts* line becomes `mitigated 26 · partly 16`.
Line 3 and *Sources* name `v0.11`.

### D16

- **`docs/README.md`** — what gpunit is, briefly; one diagram of the laptop half (`cli`, `library`, `lifecycle`,
  `volume`, `spend`, `serve`) and the pod half (`boot/boot.py`, `serve/launch.py`) and where they meet; the layers in
  one line; the map: each page of the guide, one line each; where to start for a task.
- **`README.md`** — stays the user's guide: install, the spec, the verbs, the costs, the proofs. How it works moves to
  the guide, linked from one line under the opening diagram. The pointer to an archived design goes.
- **`CLAUDE.md`** — opens with "read `docs/README.md` first". It keeps *The quality gate*, *How a change is cut here*
  and *Guardrails*. *Layout* is replaced by a link to `docs/modules.md`, and *Invariants* by a link to
  `docs/principles.md`. A new section, *The rules for a change*, holds: an archived change is a record (decision D7); a
  patch adds no verb, key or exit code (decision D8); a trust-boundary change edits the threat model (decision D9); a
  decision made or overturned edits `docs/decisions.md`; a new module edits `LAYERS` and `docs/modules.md`; a
  refactor changes no scenario (decision D51). It names `gpunit/version.py` as the version file.

### D17

`make live` rents the cheapest card on `live/gpunit.toml` for one `nvidia-smi`, its price printed first. It proves the
moved create env and the host-key proof against RunPod. Its tail goes in `live/last_run.txt` under
`<date> — make live, 0015-architecture-and-docs`. No other live target runs: `boot.py` and the images do not change.

## Seed: decisions

The decisions in force at `v0.10.0`, read against the code by the audit, and those this change adds. *Made by*
lists the archived ids, `change·D`; `S` and `R` ids are converge amendments. Phase 5 writes the headings, and phase 6
the bodies, each re-read against the code.

| id | title | Made by |
|---|---|---|
| D1 | A flat stdlib package, Python 3.11, no runtime dependency | `0001·D1` |
| D2 | A `Provider` protocol, its nouns not RunPod's | `0001·D2`, `0007·D2`, `0010·D1` |
| D3 | RunPod on `urllib`: bounded calls, the key in a header, no redirect, quiet log reads end | `0001·D3`, `0002·D4`, `0002·D6` |
| D4 | gpunit's lines: UTC-stamped, to stderr or a sink; `refused:` opens a refusal; a dead pipe swallowed; `sys.exit` in `cli` alone | `0001·D12`, `0004·D5` |
| D5 | The gate fakes every provider answer; `boot.py` at 100 % | `0001·D13`, `0007·D5`, `0012·D5`, `0012·D6`, `0012·D7` |
| D6 | The metered proofs run by hand, the price first, their tails committed; a boot change rebuilds the images | `0001·D14`, `0002·D13`, `0008·D4`, `0009·D7`, `0009·D8`, `0010·D10`, `0010·D11`, `0012·D10`, `0012·D12`, `0012·D13`, `0014·D12` |
| D7 | An archived change is a record; a card against it closes won't-fix | `0002·D12`, `0003·D6`, `0006·D7`, `0009·D6`, `0011·D9`, `0012·D11`, `0013·D12`, `0014·D10` |
| D8 | A patch closes cards; it adds no verb, `gpunit.toml` key or exit code | `0006·D5` |
| D9 | The threat model lives in `docs/` and moves with every trust-boundary change | `0013·D14` |
| D10 | The lifecycle module is `lifecycle.py` | `0004·D10` |
| D11 | `Spec` from `gpunit.toml`: strict keys, a digest, a required ceiling, checked ports | `0001·D4`, `0002·D3` |
| D12 | `[env]` passes as written, names no `GPUNIT_*` or `RUNPOD_*`; gpunit's names win | `0001·D4`, `0004·D7`, `0013·D2`, `0015·D7` |
| D13 | The window keys, never beside `volume` | `0010·D2` |
| D14 | `datacenters` is an allow-list | `0013·D7` |
| D15 | `.gpunit/` in the working directory, each record written whole, the directory 0700 | `0001·D5`, `0010·D4`, `0013·D3` |
| D16 | A keypair per session, deleted at teardown | `0001·D6` |
| D17 | The ledger: best effort to write, refuses to read; `spend` joins on it | `0007·D1`, `0010·D9`, `0011·D7`, `0015·D6` |
| D18 | `serve`'s state under the home directory, one session per model | `0005·D2` |
| D19 | Placement: the catalogue floor, one create per card, a 400 moves on, the rest is `Lost` | `0001·D7`, `0015·D5` |
| D20 | Teardown only when a create began here or was lost | `0003·D1` |
| D21 | The wait: a bounded poll; a failed read is not yet; two dead polls end any wait | `0001·D8`, `0006·D2`, `0009·D1` |
| D22 | The host key is proven over the log | `0001·D8`, `0003·D2`, `0006·D1`, `0009·D3`, `0010·D14`, `0010·R3`, `0011·D8`, `0015·D7`, `0015·D8` |
| D23 | Teardown: a 404 keeps the record; the project's pods are swept | `0001·D9`, `0002·D5` |
| D24 | gpunit's ssh is its own; the tools checked before any request | `0002·D1`, `0002·D2` |
| D25 | The pod stops at its ceiling and on any end; `down` deletes | `0001·D11` |
| D26 | A pod outside `datacenters` is torn down | `0013·D8`, `0013·D9` |
| D27 | `session()` is a context manager over `open_session`; `run` is its first caller | `0001·D10`, `0004·D1`, `0004·D6`, `0015·D4` |
| D28 | One exception per outcome; the provider's `Unplaceable` stays private | `0004·D2`, `0015·D5` |
| D29 | Signals raise `Interrupted` once, are ignored during teardown, restored after | `0004·D3` |
| D30 | The tunnel: a watched `ssh -N -L`, a backoff, one forward per loopback family | `0002·D8`, `0004·D4`, `0013·D5`, `0013·S1`, `0013·S6` |
| D31 | A taken local port refuses, from any thread, unlatched | `0013·D5`, `0013·D6`, `0013·S2` |
| D32 | Exit codes: `0`, `1`, `2`, `3`, `128+n` | `0001·D10`, `0002·D7`, `0004·D6`, `0006·D3` |
| D33 | `run`'s command gets the host, the ports and `GPUNIT_SSH`, never the account key | `0001·D10`, `0004·D6`, `0013·D1` |
| D34 | A model is a row: the bundled table and one user file | `0005·D1`, `0008·D1`, `0008·D2`, `0014·D1`, `0014·D2`, `0014·D3`, `0014·D5`, `0014·D7`, `0014·S2` |
| D35 | The price first, `y/N`; `--yes` skips it | `0005·D3` |
| D36 | `serve`'s wait polls `/v1/models`; the local port is picked before the price | `0005·D4`, `0006·D3` |
| D37 | The chat: streamed, in memory, cleaned on screen | `0005·D5`, `0006·D3`, `0014·D9`, `0014·S4` |
| D38 | `--api`: a fresh key, the URL and key on stdout, a hold | `0005·D6` |
| D39 | `pod.log` holds the log since the create; printed lines are cleaned | `0009·D2`, `0013·D4` |
| D40 | The serve image: vLLM by digest; the launcher turns logging and telemetry off | `0005·D7`, `0012·D9`, `0014·D4`, `0014·D6` |
| D41 | `volume up` and `down`; the sweep asks a person at a terminal | `0010·D5`, `0010·S1`, `0010·S2`, `0010·R1`, `0011·D1`, `0011·D4`, `0011·D5` |
| D42 | The window's data centre | `0010·D3` |
| D43 | Every session mounts the window; the sweep runs first | `0010·D6`, `0010·D7`, `0010·D8`, `0010·R2`, `0011·D2`, `0011·D3` |
| D44 | `spend`: whole UTC days, the provider's amounts, one rounding | `0007·D3`, `0007·D4` |
| D45 | `boot.py`: one stdlib file for Python 3.10, no gpunit import | `0012·D1`, `0012·D2`, `0012·D8` |
| D46 | The ceiling in a forked watchdog; the stop in a `finally`, retried | `0001·D11`, `0003·D4`, `0009·D4`, `0012·D1`, `0012·D3` |
| D47 | Boot's stop over `urllib`; the command's env without the key and the nonce | `0003·D3`, `0012·D4` |
| D48 | sshd on boot's own config and a fresh host key | `0001·D11`, `0002·D9` |
| D49 | The layers, held by `tests/test_layers.py` | `0015·D9` |
| D50 | The guide: why, flow and where, never a value; symbols and decision ids cited, held by `tests/test_docs.py` | `0015·D10`, `0015·D11`, `0015·D14` |
| D51 | A refactor changes no scenario, message or exit code | `0015·D1` |

## Seed: principles

The rules the code follows, and what holds each at the cut. The held-by column names tests in `tests/`. Phase 6
re-reads each against the code and adds the decision it comes from.

| rule | held by | breach |
|---|---|---|
| The account key travels in a request header alone: never on argv, a redirect or a subprocess | `test_gpu_reads_the_memory_and_the_secure_price`, `test_the_commands_end_stops_the_pod`, `test_a_redirect_is_not_followed`, `test_a_redirect_is_a_failed_stop_never_followed`, `test_the_key_comes_from_the_environment_only` | — |
| The key comes from the environment alone; no `.env` | `test_no_key_refuses_at_construction`, `test_a_dotenv_beside_the_spec_is_ignored` | — |
| The consumer's command gets no account key; `[env]` names no `RUNPOD_*` or `GPUNIT_*` | `test_the_command_gets_no_account_key`, `test_the_child_holds_no_key_and_no_nonce`, `test_a_runpod_variable_in_env_is_refused`, `test_a_gpunit_variable_in_env_is_refused` | — |
| A refusal is one stamped stderr line; `refused:` opens it | `test_a_refusal_is_one_stamped_stderr_line`; review for the other sites | — |
| Teardown on every way out of the block; signals ignored during it | `test_the_blocks_end_tears_down`, `test_an_error_in_the_block_tears_down`, `test_sigterm_ends_the_block_and_tears_down`, `test_a_signal_during_the_teardown_is_ignored`, `test_the_deadline_tears_down`, `test_a_mismatch_tears_down` | — |
| Nothing is torn down that this session did not make | `test_an_interrupt_before_the_create_sweeps_nothing`, `test_an_interrupt_beside_an_earlier_record_deletes_nothing`, `test_a_look_alike_image_is_not_ours`, `test_down_leaves_a_volume_of_its_name_it_did_not_make` | — |
| One live session per project | `test_a_recorded_pod_refuses_up`, `test_a_pending_create_refuses_up`, `test_a_listed_pod_refuses_up` | — |
| The ceiling is required, and the pod enforces it | `test_no_ceiling_no_pod`, `test_the_ceiling_reaches_the_pod_in_seconds`, `test_the_watchdog_stops_the_pod_at_the_ceiling` | — |
| A 404 is never gone | `test_a_404_keeps_the_record`, `test_a_refused_delete_keeps_the_record` | — |
| A lost create exits `3`, keeps its mark, and the next `down` finds it | `test_a_5xx_create_is_lost`, `test_a_lost_create_tears_down_and_exits_3`, `test_a_lost_create_keeps_the_pending_mark`, `test_a_lost_create_is_swept` | — |
| Nothing is rented or created without the price and a `y` (`serve`, `volume up`) | `test_nothing_is_rented_unless_the_operator_says_y`, `test_no_is_the_default`, `test_an_interrupt_at_the_price_creates_nothing` | — |
| Every input that shapes a pod is pinned | `test_an_image_without_a_digest_is_refused`, `test_a_moving_revision_is_refused_naming_the_row`, `test_the_image_is_built_from_pinned_inputs`, `test_each_action_is_pinned_by_commit` | `gpunit/serve/table.py::_args` matches exact launcher flags; an abbreviation repins a user row (`0015·F23`) |
| The host key is proven over the authenticated log before anything connects | `test_a_match_is_recorded`, `test_a_mismatch_tears_down`, `test_a_key_line_the_command_echoes_is_not_the_key`, `test_a_key_line_with_another_nonce_is_not_the_key`, `test_an_older_boot_is_refused_at_once` | — |
| gpunit's ssh is its own | `test_ssh_reads_no_config_and_offers_the_session_key_alone` | — |
| A fresh keypair per session, private, deleted with the pod | `test_the_keypair_is_made_and_passed`, `test_the_key_files_are_0600`, `test_the_keypair_leaves_with_the_pod` | — |
| No request before the spec, the record and the tools are checked | `NO_REQUESTS` in `tests/helpers.py`, `test_a_busy_port_refuses_before_any_request`, `test_no_ssh_keygen_refuses_before_any_request` | — |
| stdout belongs to the command; gpunit's lines go to stderr | `test_stdout_carries_only_the_commands_output`, `test_the_lines_open_with_the_utc_time` | — |
| A dead pipe on stderr ends no teardown | `test_a_dead_pipe_on_stderr_ends_no_teardown`, `test_a_dead_pipe_on_stderr_leaves_the_process_exit_code` | — |
| A dead pod ends every wait | `test_a_dead_pod_ends_the_wait`, `test_one_dead_poll_is_not_yet`, `test_a_dead_pod_ends_the_hold` | — |
| A spec or table fault refuses before any request, naming the field | `test_a_missing_required_field_is_named`, `test_an_unknown_key_is_refused_naming_the_nearest`, `test_a_faulty_table_is_refused_naming_the_field` | — |
| The sweep runs first; a forgotten volume ends at the next command | `test_an_overdue_volume_is_deleted_first`, `test_serve_sweeps_an_overdue_volume_before_the_price`, `test_down_deletes_an_overdue_volume_after_its_pods` | — |
| No session outlives its volume | `test_a_session_past_the_volumes_end_refuses`, `test_up_again_never_pulls_the_end_in` | — |
| An unrecorded volume is deleted only on a person's `y` at a terminal | `test_the_sweep_asks_before_each_delete`, `test_the_sweep_asks_only_a_terminal`, `test_ctrl_c_ends_the_sweep` | — |
| Every amount is the provider's; an unreadable billing is an error | `test_the_total_is_the_providers_rounded_once`, `test_an_unreadable_billing_is_an_error_not_zeros` | — |
| The ledger never blocks a session | `test_an_unwritable_ledger_blocks_nothing`, `test_no_home_blocks_nothing` | — |
| Untrusted lines are cleaned before the terminal | `test_printed_log_lines_are_cleaned`, `test_streamed_text_is_cleaned_and_kept_as_streamed` | `0014·S1`: a row's arguments can turn request logging back on (`0015·F23`) |
| A taken loopback port never receives the session's traffic | `test_a_taken_port_ends_the_block`, `test_each_loopback_family_is_its_own_forward` | — |
| Secure cloud, port 22 alone | `test_the_create_is_secure_and_exposes_22_only` | — |
| The standard library alone: the package, `boot.py`, `serve/launch.py` | `architecture:layers:stdlib-only`, `test_boot_imports_the_stdlib_alone` | — |
| `sys.exit` in `cli` alone | `architecture:layers:exit-in-cli` | — |
| Imports point down the layers | `architecture:layers:hold` | — |
| Every scenario has a test, every test a key | `--strict-markers`; the one-to-one held by review | — |
| The seam names no provider noun | nothing | `gpunit/lifecycle.py::_delete_pods` compares HTTP codes (`0015·F3`); `gpunit/lifecycle.py::DEAD` and `gpunit/volume.py::STOCK` are RunPod's words (`0015·F5`); `gpunit/library.py::session` builds `RunPod` (`0015·F2`) |
| A signal exits `128+n` | `test_a_signal_during_the_teardown_is_ignored` and the `run` tests | `gpunit/volume.py::_agree` exits `1` on Ctrl-C at the price (`0015·F20`) |
| An archived change is never edited | review | — |
| A patch adds no verb, key or exit code | review | — |
| A trust-boundary change edits the threat model | review | — |
| The live proofs are never in CI; the price prints first | review | — |
| A refactor changes no scenario | the unchanged tests; review | — |

## Dependencies

None.

## Risks / Trade-offs

- [A moved name breaks an import a test or a live script makes] → the tasks name each importer;
  `live/price.py`, `live/serve_dead.py` and `live/dead.py` import none of the moved names.
- [`test_docs.py`'s slug differs from GitHub's] → the twins hold the `### Dn · title` and the plain heading cases.
- [A harvested decision misstates the code] → phase 6 re-reads each against the code; converge's review reads the pages.
- [A page claims what no test holds] → [D13](#d13) names what holds each rule, `nothing` included; the hand read checks.
- [The release bumps the old version file] → `CLAUDE.md` names `gpunit/version.py`, and hatch reads it.

## Verdict

Feasible. The refactors are moves and renames the existing tests cover. The pages come from seed tables that were read
against the code.
