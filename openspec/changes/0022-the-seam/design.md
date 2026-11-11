# The seam — design

The provider seam is made neutral: `providers.build` builds it, `Deleted` answers a delete, and RunPod's words stay in `runpod.py`. Verdict: ready to build, in the phases of [tasks](tasks.md).

## Context

[The decision on the provider protocol](../../../docs/decisions.md) names the breaches: callers compare HTTP codes, `DEAD` and `STOCK` are RunPod's words, and the provider is built in `cli`, `library`, `live/price.py` and `live/serve_dead.py`. Vast.ai's change would meet each one, so they close first, with no behaviour change ([D51](../../../docs/decisions.md)).

`0021-gone-pod` is not built when this is cut: it adds `Provider.pod`, `Provider.pod_ids`, `lifecycle.pod_gone` and a pod-gone branch in `lifecycle._delete_pods`, and moves `RunPod.get`'s `PodInfo` code into one helper that `RunPod.pod` calls too (its design: `git show 0021-gone-pod:openspec/changes/0021-gone-pod/design.md`). The tasks name those symbols as `0021` names them, and each **HALT CHECK** below fails if the build meets a different tree.

```
 before                                      after
 ──────                                      ─────
 cli · library · live ─▶ RunPod              cli · library · live ─▶ providers.build ─▶ RunPod
 lifecycle · volume: code in DELETED,        lifecycle · volume: deleted.kind == "gone"
   DEAD, STOCK, VOLUME_GB_MONTH              PodInfo.dead · stock() ranked · volume_rate
 hostkey: LOG_TAIL · run: RUNPOD_API_KEY     log_cap · key_names
```

## Goals / Non-Goals

- Goal: the RunPod module is imported by `gpunit/providers.py` alone, and the gate holds it.
- Goal: no caller of the seam reads an HTTP code, a RunPod status, a stock level, a log cap, a price or a key name.
- Non-goal: one price prompt or one card filter — Vast.ai's cut.
- Non-goal: a `provider` key in `gpunit.toml`, a second provider, boot's stop.
- Non-goal: a changed message, exit code or scenario of behaviour.

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| [D1](#d1) | `gpunit/providers.py::build(environ)` returns `RunPod(environ)`; `cli`, `library`, `live/price.py` and `live/serve_dead.py` call it | one builder | building in `lifecycle`: it would put a provider choice under the session |
| [D2](#d2) | The `architecture` requirement and `tests/test_layers.py` say only `providers` imports the RunPod module; D51 is amended so the `architecture` spec may move with a refactor | otherwise no refactor could move a module that spec names | a new requirement beside the old: a second rule for the same import |
| [D3](#d3) | `delete`, `delete_volume` and `stop` return `Deleted(kind, code)`; callers branch on `kind` and their messages print `code`; `DELETED` leaves `provider.py` for `runpod.py` | outcomes, not HTTP codes | a bool: the callers tell a missing name from a refusal |
| [D4](#d4) | `0021`'s `_delete_pods` branches on `Deleted.kind`; `Provider.pod` and `pod_ids` stay as `0021` adds them | their symbols are this change's input, so `after:` | recasting `0021`'s reads: they are gpunit's nouns already |
| [D5](#d5) | `PodInfo.dead` is set by the provider; `DEAD` becomes `DEAD_STATUSES` in `runpod.py` | RunPod's statuses stay in `runpod.py` | a `dead` method on the provider: `DeadPod` reads one poll's `PodInfo` |
| [D6](#d6) | `stock()` answers best first, and `volume` takes the first data centre it can use | RunPod's levels stay in `runpod.py` | a level ranking in the seam: it names RunPod's levels |
| [D7](#d7) | `log_cap` is the provider's longest log tail; `hostkey` reads it; `serve`'s own tail constant is renamed | the cap is RunPod's; the acceptance grep finds no `LOG_TAIL =` left | leaving `serve`'s `LOG_TAIL = 50`: it fails the grep |
| [D8](#d8) | `volume_rate` is the price of a GB-month as a decimal string; `most_cost` and `_agree` take it as a `Decimal` | the rate is RunPod's, and the seam imports no `decimal`, which `cli` keeps off every other verb's start | a `Decimal` on the seam: every verb would import `decimal` |
| [D9](#d9) | `key_names` names the environment variables that hold the account key; `run` drops each from the command's env; `spec`'s `RUNPOD_*` refusal stays | `spec` is a model-layer module and cannot import a provider (`provider` imports `spec`); a parameter on `load_spec` would change every test's call | the brief's `spec` reading of Q5: a cycle, or a changed signature |
| [D10](#d10) | Tests change in names, imports, fakes and the expected value of a retyped seam answer alone | Q4 and Q5 retype answers the tests assert on | tests unchanged: a `Deleted` is not `204` |

### D1

`build` takes a mapping, as `RunPod.__init__` does, and returns `Provider`. It sits in the cloud layer beside `gpunit.runpod`, so `library` and `cli` import it and it imports `RunPod`; `RunPod` needs a key, so `build` refuses as `RunPod` does.

```python
def build(environ: Mapping[str, str]) -> Provider:
    """Return the provider; RunPod, until a `provider` key chooses."""
    return RunPod(environ)
```

`cli` calls `providers.build(os.environ)` where it called `RunPod()`; `library.session` calls it with the mapping it has; `live/price.py` and `live/serve_dead.py` call it with `os.environ`.

### D2

| page | change |
|---|---|
| `openspec/specs/architecture/spec.md` | the delta: `providers` is the one importer, and the scenario `architecture:layers:provider-built` says so |
| `tests/test_layers.py` | `LAYERS` gains `gpunit.providers` in `cloud`; `BUILDERS` is `{"gpunit.providers"}`; the two RunPod-import tests are renamed |
| `docs/decisions.md` | D51's statement is amended to the text below; its title stays, so its anchor holds |
| `docs/modules.md` | the layers table, the main edges, the module list and *Where RunPod is built* name `gpunit.providers` |

D51, amended:

```
**A change that moves or renames code leaves every spec scenario of behaviour, message and exit code as it was; the
`architecture` spec, which states the repo's shape, moves with it. Tests change in names, imports, fakes and the
expected value of a retyped seam answer alone.**
```

### D3

`Deleted` is a frozen dataclass in `gpunit/provider.py`. Its `kind` is one of these words, defined once:

| kind | means | RunPod's answer |
|---|---|---|
| `gone` | the call took effect | a delete: `200`, `204` (`DELETED`); a volume delete: `204`; a stop: `200` |
| `missing` | the provider does not know the name | `404` |
| `refused` | the provider answered and did not do it | any other status |
| `no answer` | no answer came | status `0` |

The module function `gpunit.runpod.outcome(status, taken)` is the one rule; `RunPod.delete`, `RunPod.delete_volume` and `RunPod.stop` return it. A message that named `HTTP {code}` still does, from `deleted.code`.

### D4

`_delete_pods` branches in the order `0021`'s D5 sets: `gone` clears and says deleted; else a gone pod (`pod_gone`) clears and says so; else `missing` keeps the record with its "may be wrong key" line; else the record is kept with `answered HTTP {deleted.code}`. The sweep reads `kind == "gone"` for each listed pod.

Everything else of `0021` stands: `pod_gone` reads `Provider.pod` and `Provider.pod_ids`, and `status` is untouched.

### D5

The helper that builds a `PodInfo` for `RunPod.get` and `RunPod.pod` sets `dead=status in DEAD_STATUSES`. `PodInfo` gains `dead: bool = False` as its last field, so a hand-built `PodInfo` of a live status stays equal. `DeadPod.seen` reads `info.dead`.

### D6

`RunPod.stock` keeps the levels of `STOCK_LEVELS`, best first, and sorts stably, so equal levels keep RunPod's order. `volume._stocked` takes the first data centre of the answer that is in the standard set. This is what `min(..., key=STOCK.index)` chose.

### D7

`Provider.log_cap` is a read-only property, `RunPod.log_cap` is `MAX_TAIL`. `gpunit/serve/session.py`'s `LOG_TAIL = 50`, the lines `serve` shows, becomes `PROGRESS_TAIL`: it is not RunPod's word, but the acceptance grep for `^LOG_TAIL =` reads it.

### D8

`RunPod.volume_rate` is `VOLUME_RATE`, `"0.07"`, with the comment `VOLUME_GB_MONTH` carries now. `volume.up` and `volume._extend` pass `Decimal(provider.volume_rate)` down to `most_cost` and `_agree`; `most_cost(size_gb, ceiling_s, rate)` is otherwise as it was.

### D9

`RunPod.key_names` is `("RUNPOD_API_KEY",)`. `run.run` hands it to `_command`, which drops each name from the command's environment ([D33](../../../docs/decisions.md)). `gpunit/spec.py::_env` keeps refusing `RUNPOD_*` with its message; moving it is Vast.ai's cut, which knows the second provider's names. The brief's `C2` row records the call.

### D10

`FakeProvider` keeps its scripts as they are, `deletes={"pod-1": 404}` among them, and answers through `outcome`, `ranked` and the properties above. The tests that assert a delete's answer, a ranked stock, an `EXITED` fixture and `most_cost` change by the retyped value; no scenario, message or exit-code assertion changes. The brief's `C1` row records the call.

## Tests

No test is added to the end-to-end layer, and no engine matrix applies ([T1](../../../CODING_STANDARDS.md)). The tests that change are unit and integration tests on faked answers; a step in an existing test is chosen before a new test ([T2](../../../CODING_STANDARDS.md)).

| layer | file | change | because |
|---|---|---|---|
| unit | `tests/test_runpod.py` | add `test_the_builder_returns_runpod_for_now` | `providers.build` has no test |
| unit | `tests/test_runpod.py` | add `test_runpod_states_its_own_words`: `log_cap`, `volume_rate`, `key_names` | each is new on the seam, and one test reads them all |
| unit | `tests/test_runpod.py` | a step in `test_get_reads_the_direct_ssh_address_or_none`: `dead` for `EXITED`, `ERROR`, `TERMINATED` and `RUNNING` | the page is already there |
| unit | `tests/test_runpod.py` | the delete, volume-delete and stop tests, and the stock test, assert the retyped values | D3 and D6 |
| unit | `tests/test_layers.py` | `LAYERS`, `BUILDERS` and the RunPod-import tests renamed and re-pointed at `providers` | D2 |
| fake | `tests/fakes.py` | `FakeProvider` answers `Deleted`, ranks its stock and states `log_cap`, `volume_rate`, `key_names` | the protocol gains them |
| integration | `tests/test_library.py`, `tests/test_down.py`, `tests/test_run.py` | the `FakeProvider` subclasses return `Deleted`; the library test patches `providers.RunPod` | D1, D3 |
| integration | `tests/test_up.py`, `tests/test_serve_session.py` | the `EXITED` fixture gains `dead=True` | D5 |
| integration | `tests/test_volume.py` | `most_cost` takes the rate | D8 |

The count of `tests/test_runpod.py` and `tests/test_layers.py` together, by `uv run pytest tests/test_runpod.py tests/test_layers.py --collect-only -q -m "not e2e"`: 71 at `54c3a97`, 74 once `0021` adds its three cases to `tests/test_runpod.py`, 76 after this change, two added.

No test is deleted or merged.

## Dependencies

None.

## Risks / Trade-offs

- **`0021` is not built at the cut.** The tasks name its symbols as its design does; the helper it moves `PodInfo`'s code into has no name there, so task 3.1 names it by what it does and a **HALT CHECK** holds that `gpunit/runpod.py` builds a `PodInfo` in one place. If `0021`'s build differs, the check halts and a rescue amends the task.
- **A scenario's heading is pinned.** `openspec validate` requires a MODIFIED block to keep each scenario's name, so *the provider is built in two places alone* keeps its heading while its key, `WHEN` and `THEN` say `providers` alone; renaming it takes a REMOVED and an ADDED requirement, so it waits for the change that next rewrites this requirement.
- **`stop` answers `Deleted`.** `kind == "gone"` reads "the stop took effect"; no gpunit code calls `Provider.stop`, so nothing branches on it today.
- **`spec.py` still names `RUNPOD_`.** It is the one RunPod word left outside `runpod.py` and `boot/boot.py` ([D9](#d9)); Vast.ai's cut moves it.
- **The decimal rate is a string.** `Decimal(provider.volume_rate)` is the one conversion, in `gpunit/volume.py`.

## Verdict

Ready to build, in the phases of [tasks](tasks.md): each ends on a green `make check`, the last on a green `make gate`.
