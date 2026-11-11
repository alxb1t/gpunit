---
bump: patch
after: [0021-gone-pod]
---

# The seam

The provider seam made neutral before Vast.ai: one place builds the provider, the seam speaks in outcomes, and RunPod's words live in `runpod.py` alone — no behaviour change.

Reading map: [design](design.md) holds the decisions, the test cost and the cutter's calls that part from the brief, [tasks](tasks.md) holds the phases: the builder, the outcomes, the words.

## Why

[The decision on the provider protocol](../../../docs/decisions.md) says the seam's nouns are gpunit's, and names its breaches: `gpunit/lifecycle.py::_delete_pods` compares HTTP codes, `DEAD` and `STOCK` are RunPod's words, and `gpunit/library.py::session`, `gpunit/cli.py::_run`, `live/price.py` and `live/serve_dead.py` each build `RunPod`. A second provider, Vast.ai, would meet every one of them. Closing them first leaves Vast.ai's change to add an implementation, not to unpick RunPod from the callers.

This change builds on `0021-gone-pod`, which adds `Provider.pod`, `Provider.pod_ids` and `lifecycle.pod_gone` to the seam: its `_delete_pods` branch on a gone pod is moved off HTTP codes here too.

## What Changes

- `gpunit/providers.py::build(environ)` is the one place that builds the provider; `cli`, `library`, `live/price.py` and `live/serve_dead.py` call it, and only `providers` imports the RunPod module.
- The `architecture` rule says so, `tests/test_layers.py` holds it, and decision D51 is amended to let the `architecture` spec move with a refactor.
- `Provider.delete`, `Provider.delete_volume` and `Provider.stop` return a `Deleted` result with a `kind`, not an HTTP code; callers branch on `kind`, and `DELETED` leaves `gpunit/provider.py` for `gpunit/runpod.py`.
- RunPod's words leave `lifecycle`, `volume`, `hostkey` and `run`: `PodInfo.dead`, a ranked `Provider.stock`, `Provider.log_cap`, `Provider.volume_rate` and `Provider.key_names` carry them.
- No message, exit code, scenario of behaviour or `gpunit.toml` key changes ([D8](../../../docs/decisions.md), [D51](../../../docs/decisions.md)).

Requirement lines:

- `architecture` · MODIFIED · The modules import down the layers: its scenario `architecture:layers:provider-built` names `providers` as the one importer of the RunPod module.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `architecture`: the requirement *The modules import down the layers*, one sentence and one scenario.

## Impact

- **Code:** `gpunit/providers.py` (new), `gpunit/provider.py`, `gpunit/runpod.py`, `gpunit/lifecycle.py`, `gpunit/volume.py`, `gpunit/hostkey.py`, `gpunit/run.py`, `gpunit/cli.py`, `gpunit/library.py`, `gpunit/serve/session.py` (one rename), `live/price.py`, `live/serve_dead.py`.
- **Tests:** `tests/fakes.py`, `tests/test_layers.py`, `tests/test_runpod.py`, `tests/test_library.py`, `tests/test_down.py`, `tests/test_run.py`, `tests/test_up.py`, `tests/test_serve_session.py`, `tests/test_volume.py`.
- **Docs:** `docs/decisions.md` (the decisions on the provider protocol, on teardown and on refactors), `docs/principles.md`, `docs/modules.md`, `docs/extending.md`.
- **Spec:** the `architecture` requirement, through the delta.
- **Threat model:** none; no flow, secret, file mode, network call or log line moves.

## Not in this change

- F9, one price prompt, and F10, one card filter — Vast.ai's cut, because merging them changes messages (D51) and Vast.ai places on offers, so its probe decides where pricing lives.
- A `provider` key, Vast.ai itself, boot's stop (F14) — Vast.ai's minor.
- `spec.py`'s `RUNPOD_*` refusal: it stays where it is until the second provider's names are known, because `spec` is a model-layer module that cannot import a provider.
- Any behaviour, message or exit code (D51).
