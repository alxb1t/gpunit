# The seam — tasks

One builder, an outcome for each delete, and RunPod's words in `runpod.py`. Decisions are in [design](design.md).

## Progress

- [x] 1 — The builder · moderate
- [ ] 2 — The outcomes · hard
- [ ] 3 — The words · moderate

## 1 — The builder

- [x] 1.1 Add `gpunit/providers.py` per [D1](design.md#d1): the docstring `The one place that builds the provider.`, the imports of `Mapping`, `Provider` and `RunPod`, and `build(environ: Mapping[str, str]) -> Provider` returning `RunPod(environ)`. Add `"gpunit.providers": "cloud",` to `LAYERS` in `tests/test_layers.py` after the `gpunit.runpod` entry, and `gpunit.providers` to the cloud row and the module list of `docs/modules.md`.
  Verify: `grep -n "def build" gpunit/providers.py` prints a line, and `grep -n "gpunit.providers" tests/test_layers.py docs/modules.md` prints a line in each file.

- [x] 1.2 In `gpunit/cli.py`, change `from gpunit import lifecycle, log, run` to `from gpunit import lifecycle, log, providers, run`, delete `from gpunit.runpod import RunPod`, and make `lazy` return `provider or providers.build(os.environ)`. In `gpunit/library.py`, change `from gpunit import lifecycle, log` to `from gpunit import lifecycle, log, providers`, delete `from gpunit.runpod import RunPod`, and make `session` call `providers.build(environ if environ is not None else os.environ)`.
  Verify: `grep -n "providers.build" gpunit/cli.py gpunit/library.py` prints a line in each file, and `grep -n "RunPod" gpunit/cli.py gpunit/library.py` prints nothing.

- [x] 1.3 In `live/price.py` and `live/serve_dead.py`, delete `from gpunit.runpod import RunPod`; `live/price.py` imports `os` and `from gpunit import providers` and builds `providers.build(os.environ)` where it built `RunPod()`; `live/serve_dead.py` changes `from gpunit import log` to `from gpunit import log, providers` and passes `providers.build(os.environ)` where it passed `RunPod(os.environ)`.
  Verify: `grep -n "providers.build" live/price.py live/serve_dead.py` prints a line in each file, and `grep -n "RunPod" live/price.py live/serve_dead.py` prints nothing.

- [x] 1.4 In `tests/test_layers.py`, set `BUILDERS = {"gpunit.providers"}`, rename `test_runpod_is_built_in_library_and_cli_alone` to `test_runpod_is_imported_by_providers_alone`, and rename `test_a_third_runpod_importer_is_caught` to `test_a_second_runpod_importer_is_caught`: in its package `gpunit/providers.py` imports `RunPod` from `gpunit.runpod`, `gpunit/library.py` and `gpunit/cli.py` import `providers`, and `run`, `spend` and `volume` stay the importers the assertion names.
  Verify: `uv run pytest tests/test_layers.py -q` exits 0.

- [x] 1.5 In `tests/test_library.py`, import `providers` in `from gpunit import library, lifecycle, providers` and patch it in place of `library`: `monkeypatch.setattr(providers, "RunPod", lambda environ: RunPod(environ, opener=opener))`. In `tests/test_runpod.py`, import `providers` from `gpunit` and add `test_the_builder_returns_runpod_for_now`, marked `architecture:layers:provider-built`: `providers.build({"RUNPOD_API_KEY": KEY})` is a `RunPod`, and `providers.build({})` raises `Refusal` matching `RUNPOD_API_KEY`.
  Verify: `uv run pytest tests/test_library.py tests/test_runpod.py -q -k "key_comes_from_the_mapping or builder_returns"` exits 0.

- [x] 1.6 In `docs/decisions.md`, replace the statement of D51 with the text in [D2](design.md#d2), its title unchanged, and add `0022·D2` to its *Made by*.
  Verify: `grep -n "which states the repo's shape" docs/decisions.md` prints a line.

- [x] 1.7 In `docs/modules.md`, make the main edges read `cli ─┬─▶ run · providers · lifecycle`, `run ─▶ library ─▶ lifecycle · providers` and `cloud       providers ─▶ runpod ─▶ contract`, and rewrite *Where RunPod is built* to say `gpunit/providers.py::build` builds it, `gpunit/library.py::session` and `gpunit/cli.py::_run` call it, and a second provider changes that function.
  Verify: `grep -n "gpunit/providers.py::build" docs/modules.md` prints a line.

- [x] 1.8 In `docs/extending.md`, in *A provider*, delete the bullet *Where it is built*, and add to the opening sentence that a second provider has `gpunit/providers.py::build` return it.
  Verify: `grep -n "Where it is built" docs/extending.md` prints nothing.

## 2 — The outcomes

- [x] 2.1 In `gpunit/provider.py`, delete `DELETED` and its comment, import `Literal`, and add `class Deleted` after `PodInfo` per [D3](design.md#d3): a frozen dataclass of `kind: Literal["gone", "missing", "refused", "no answer"]` and `code: int`, its docstring the table's meanings. Make `Provider.delete`, `Provider.delete_volume` and `Provider.stop` return `Deleted`, their docstrings ending `no answer when none came`.
  Verify: `grep -n "class Deleted" gpunit/provider.py` prints a line, and `grep -n "DELETED" gpunit/provider.py` prints nothing.

- [x] 2.2 In `gpunit/runpod.py`, import `Deleted` in place of `DELETED`; add `DELETED = (200, 204)`, `VOLUME_DELETED = (204,)` and `STOPPED = (200,)` after `MAX_TAIL`; add `def outcome(status: int, taken: tuple[int, ...]) -> Deleted` after `_quote`: `gone` when `status in taken`, `missing` on `404`, `no answer` on `0`, else `refused`. `delete` returns `outcome(answer.status, DELETED)`, `delete_volume` returns `outcome(answer.status, VOLUME_DELETED)` and logs when `answer.status not in VOLUME_DELETED`, and `stop` passes its call's `.status` with `STOPPED`.
  Verify: `grep -n -E "^(DELETED|VOLUME_DELETED|STOPPED) = " gpunit/runpod.py` prints a line for each, and `grep -n "def outcome" gpunit/runpod.py` prints a line.

- [ ] 2.3 In `gpunit/lifecycle.py`, import `Deleted` from `gpunit.provider` in place of `DELETED` and rename `code` to `deleted` in `_delete_pods`: the recorded pod's branches are `deleted.kind == "gone"`, then `0021`'s `elif pod_gone(provider, record.id) and state.clear_gone(record.id):` as it is, then `deleted.kind == "missing"` with the `404` message as it is, then the rest with `answered HTTP {deleted.code}`; the sweep reads `deleted.kind == "gone"` and prints `{deleted.code}` ([D4](design.md#d4)). **HALT CHECK**: `grep -n "elif pod_gone(provider, record.id) and state.clear_gone(record.id):" gpunit/lifecycle.py` prints a line before this task; `0021` adds it.
  Verify: `grep -n "code in DELETED" gpunit/lifecycle.py` prints nothing, and `grep -n "elif code == 404:" gpunit/lifecycle.py` prints nothing.

- [ ] 2.4 In `gpunit/lifecycle.py`, make `delete_volume` return `Deleted` and call `ledger.record_deleted` on `deleted.kind == "gone"`; in `sweep_window` read `deleted.kind == "gone"` and `deleted.kind == "missing" and gone(built, window.id)` for its branches, and print `deleted.code` in the warning.
  Verify: `grep -n -E "code == 204|code == 404 and" gpunit/lifecycle.py` prints nothing.

- [ ] 2.5 In `gpunit/volume.py`, make `down` read `deleted.kind == "gone"` and `deleted.kind == "missing" and lifecycle.gone(...)`, and `_sweep` read `(deleted := lifecycle.delete_volume(provider, volume_id)).kind == "gone"`; both messages print `deleted.code` where they printed `code`.
  Verify: `grep -n -E "code == (204|404)|\) == 204" gpunit/volume.py` prints nothing.

- [ ] 2.6 In `tests/fakes.py`, import `Deleted` from `gpunit.provider` and `outcome` with the sets of statuses it takes from `gpunit.runpod`; `FakeProvider.delete` returns `outcome(self.deletes.get(pod_id, 204), DELETED)`, `stop` returns `outcome(200, STOPPED)`, `delete_volume` returns `outcome(self.volume_deletes.get(volume_id, 204), VOLUME_DELETED)`, each annotated `-> Deleted`; the scripts keep their codes ([D10](design.md#d10)).
  Verify: `grep -n -E "\) -> Deleted:" tests/fakes.py` prints a line for each of the three.

- [ ] 2.7 In `tests/test_down.py`, `tests/test_library.py` and `tests/test_run.py`, import `Deleted` from `gpunit.provider` and annotate the `FakeProvider` subclasses' `delete` and `delete_volume` `-> Deleted`; `HeldVolume.delete_volume` in `tests/test_down.py` returns `deleted` as it came when the pod was deleted, else `Deleted("refused", 409)`.
  Verify: `grep -n "Deleted" tests/test_down.py tests/test_library.py tests/test_run.py` prints a line in each file.

- [ ] 2.8 In `tests/test_runpod.py`, import `Deleted` and assert the outcome: rename `test_delete_returns_the_status_and_0_without_an_answer` to `test_delete_returns_what_happened_and_the_code` with `[Deleted("gone", 204), Deleted("missing", 404), Deleted("no answer", 0)]`; `test_stop_posts_the_stop_action` expects `Deleted("gone", 200)`; rename `test_delete_volume_returns_the_status_and_0_without_an_answer` to `test_delete_volume_returns_what_happened_and_the_code` with `[Deleted("gone", 204), Deleted("refused", 409), Deleted("no answer", 0)]`.
  Verify: `uv run pytest tests/test_runpod.py -q -k "delete or stop"` exits 0.

- [ ] 2.9 In `docs/decisions.md`, replace the sentence of D23 that cites `gpunit/provider.py::DELETED` with the sentence: `gpunit/provider.py::Deleted` says what a delete did, in its `kind`. **HALT CHECK**: `grep -n "provider.py::DELETED" docs/decisions.md` prints a line before this task; `0021` leaves it in place.
  Verify: `grep -n "provider.py::DELETED" docs/decisions.md` prints nothing, and `grep -n "provider.py::Deleted" docs/decisions.md` prints a line.

- [ ] 2.10 In `docs/extending.md`, delete the bullet *HTTP statuses in the seam*, the one that cites `0015·F3`.
  Verify: `grep -n "0015·F3" docs/extending.md` prints nothing.

## 3 — The words

- [ ] 3.1 In `gpunit/provider.py`, add `dead: bool = False` as the last field of `PodInfo`, its docstring ending `and whether the container is not running`. In `gpunit/runpod.py`, add `DEAD_STATUSES = ("EXITED", "ERROR", "TERMINATED")` after `MAX_TAIL` with the comment `The statuses of a container that is not running.`, and have the helper that `RunPod.get` and `RunPod.pod` call to build a `PodInfo` set `dead=str(body["status"]) in DEAD_STATUSES` ([D5](design.md#d5)). **HALT CHECK**: `grep -c "PodInfo(" gpunit/runpod.py` prints `1` before this task.
  Verify: `grep -n -E "dead=.*DEAD_STATUSES" gpunit/runpod.py` prints a line.

- [ ] 3.2 In `gpunit/lifecycle.py`, delete `DEAD` and its comment, and make `DeadPod.seen` read `dead = info is not None and info.dead`.
  Verify: `grep -n -E "^DEAD|status in DEAD" gpunit/lifecycle.py` prints nothing.

- [ ] 3.3 In `tests/test_up.py` and `tests/test_serve_session.py`, make the `EXITED` fixture `PodInfo(status="EXITED", host=None, port=None, dead=True)`. In `tests/test_runpod.py`, extend `test_get_reads_the_direct_ssh_address_or_none` with more answers, each `pod_running.json` with `status` set to `EXITED`, `ERROR` and `TERMINATED`, read `dead` true, and its earlier `PENDING` and `RUNNING` reads `dead` false.
  Verify: `uv run pytest tests/test_runpod.py tests/test_up.py tests/test_serve_session.py -q -m "not e2e"` exits 0.

- [ ] 3.4 In `gpunit/runpod.py`, add `STOCK_LEVELS = ("HIGH", "MEDIUM", "LOW")` after `MAX_TAIL` and `ranked(stocked: list[tuple[str, str]]) -> list[tuple[str, str]]` after `outcome`: the pairs whose level is in `STOCK_LEVELS`, best first, equal levels in their order. `RunPod.stock` returns `ranked(...)` in place of its `!= "NONE"` filter. In `gpunit/provider.py`, `Provider.stock`'s docstring says `best first`.
  Verify: `grep -n -E "^STOCK_LEVELS = |def ranked" gpunit/runpod.py` prints a line for each.

- [ ] 3.5 In `gpunit/volume.py`, delete `STOCK` and its comment, and make `_stocked` return the first data centre of `stocked` that is in `standard` ([D6](design.md#d6)), where it chose by level with `min`.
  Verify: `grep -n "STOCK" gpunit/volume.py` prints nothing.

- [ ] 3.6 In `tests/fakes.py`, make `FakeProvider.stock` answer `ranked(...)` of its script and import `ranked`. In `tests/test_runpod.py`, rename `test_stock_reads_the_secure_pod_stock_and_drops_none` to `test_stock_reads_the_secure_pod_stock_best_first` and expect `[("CA-MTL-4", "HIGH"), ("EU-RO-1", "MEDIUM")]`.
  Verify: `uv run pytest tests/test_runpod.py tests/test_volume.py -q` exits 0.

- [ ] 3.7 In `gpunit/provider.py`, add to `Provider`, after `list`, the read-only properties `log_cap -> int`, `volume_rate -> str` and `key_names -> tuple[str, ...]`, docstrings: the most lines `log` returns, the price of a GB-month as a decimal string, and the names of the environment variables that hold the account key. In `gpunit/runpod.py`, add `VOLUME_RATE = "0.07"` with `volume.py`'s comment on it, and on `RunPod` the class attributes `log_cap = MAX_TAIL`, `volume_rate = VOLUME_RATE` and `key_names = ("RUNPOD_API_KEY",)` ([D7](design.md#d7), [D8](design.md#d8), [D9](design.md#d9)).
  Verify: `grep -n -E "def (log_cap|volume_rate|key_names)" gpunit/provider.py` prints a line for each, and `grep -n -E "^    (log_cap|volume_rate|key_names) = " gpunit/runpod.py` prints a line for each.

- [ ] 3.8 In `tests/fakes.py`, give `FakeProvider` the class attributes `log_cap = MAX_TAIL`, `volume_rate = VOLUME_RATE` and `key_names = ("RUNPOD_API_KEY",)`, importing the constants from `gpunit.runpod`. In `tests/test_runpod.py`, add `test_runpod_states_its_own_words`, marked `session:hostkey:tail-bound`, `volume:up:price-names-the-window` and `run:handover:no-account-key`, asserting `log_cap == 5000`, `volume_rate == "0.07"` and `key_names == ("RUNPOD_API_KEY",)`.
  Verify: `uv run pytest tests/test_runpod.py -q -k test_runpod_states_its_own_words` exits 0.

- [ ] 3.9 In `gpunit/hostkey.py`, delete `LOG_TAIL = 5000`; `read` calls `provider.log(record.id, tail=provider.log_cap)` and tests `len(lines) < provider.log_cap`, its comment saying `The provider's longest tail alone`. In `gpunit/serve/session.py`, rename `LOG_TAIL = 50` and its readers to `PROGRESS_TAIL`.
  Verify: `grep -n -E "^(DEAD|STOCK|LOG_TAIL|VOLUME_GB_MONTH) =" gpunit/hostkey.py gpunit/serve/session.py` prints nothing.

- [ ] 3.10 In `gpunit/volume.py`, delete `VOLUME_GB_MONTH` and its comment; `most_cost(size_gb, ceiling_s, rate: Decimal)` multiplies by `rate`; `_agree(size_gb, ceiling_s, rate, question, refused, yes)` prints `price: ${rate}/GB a month`; `_extend` takes `rate` after `ceiling_s` and passes it on; `up` passes `Decimal(provider.volume_rate)` to `_agree` and `_extend` ([D8](design.md#d8)). In `tests/test_volume.py`, `most_cost` takes `Decimal("0.07")` as its third argument.
  Verify: `grep -n "VOLUME_GB_MONTH" gpunit/volume.py` prints nothing, and `uv run pytest tests/test_volume.py -q` exits 0.

- [ ] 3.11 In `gpunit/run.py`, make `_command(spec, opened, command, withheld)` drop each name of `withheld` from the command's env where it dropped `"RUNPOD_API_KEY"`, and `run` pass `provider.key_names` ([D9](design.md#d9)).
  Verify: `grep -n "RUNPOD_API_KEY" gpunit/run.py` prints nothing.

- [ ] 3.12 In `docs/decisions.md`, in the decision titled *A `Provider` protocol, its nouns not RunPod's*, delete the sentence beginning `Breached:` and add `0022·D1`, `0022·D3`, `0022·D5`, `0022·D6`, `0022·D7` and `0022·D8` to its *Made by*; in `docs/principles.md`, the row *The seam names no provider noun* is held by `architecture:layers:provider-built` and its breach is `—`.
  Verify: `grep -n "0015·F[235]" docs/decisions.md docs/principles.md` prints nothing.

- [ ] 3.13 In `docs/extending.md`, delete the bullet on RunPod's words outside `gpunit/runpod.py`, the one that cites `0015·F5`.
  Verify: `grep -n "0015·F5" docs/extending.md` prints nothing.
