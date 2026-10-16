# Design — 0010 on-demand volumes

How a window volume is made, used and ended: new calls on the provider seam, the window's spec keys, a record beside
the pod's, a new `volume.py` with the verbs, one rule in `up`, and the live runs that close `v0.6`'s acceptance.
**Verdict: feasible** — the mount path exists (`volume = "<id>"`); the window only supplies the id.

## Context

See [proposal](proposal.md) — *Why*. What holds at the cut, `main` at `d92a84d` (`v0.6.0`):

- **The spec:** optional keys in `_OPTIONAL` (`gpunit/spec.py:26`), `Spec` (`:47`, `volume` at `:56`), `load_spec`
  (`:76`); `parse_ceiling` reads `600s`, `45m`, `4h`. A spec fault refuses with exit `1`, naming the field.
- **The mount:** `up` reads `spec.volume` before the create (`gpunit/lifecycle.py:89`); `RunPod.create` pins the
  volume's data centre and mounts it at `/runpod-volume`, telling the pod `GPUNIT_VOLUME_ID` and `GPUNIT_VOLUME_PATH`
  (`gpunit/runpod.py:127`). `_placeable` filters `gpus` by `vram_gb` and `max_hourly` (`gpunit/lifecycle.py:248`).
- **The state:** `State` names `.gpunit/pod`, `pending`, `known_hosts`, `key` (`gpunit/state.py:31`); `pending` is
  marked before a create and kept when its answer is lost.
- **The ledger:** `record` appends a pod line (`gpunit/ledger.py:28`); `read` keeps lines holding every `Entry` key
  and skips the rest (`:41`). `spend` maps pod ids to projects (`gpunit/spend.py:73`); `build` puts every volume on a
  storage line (`:80`).
- **The CLI:** `_parser` (`gpunit/cli.py:37`), `parse` (`:82`), `_run` (`:115`), `_serve` (`:161`); `down --serve
  <model>` is the one verb taking a model besides `serve`. `serve` builds its spec from the row (`gpunit/serve/session.py:57`)
  and keeps its session under `home(name)`, `~/.local/state/gpunit/serve/<model>/`.
- **RunPod v2, read 2026-10-15:** `POST /network-volumes` with `name`, `size`, `dataCenter`, `type` → `201`;
  `GET /network-volumes`, paginated, each with `id`, `name`, `dataCenter`; `DELETE /network-volumes/{id}` → `204`;
  `GET /catalog/gpus/{id}?include=AVAILABILITY&product=POD&cloud=SECURE` → `dataCenters[]` with `availability`
  `NONE | LOW | MEDIUM | HIGH`, omitted when out of stock everywhere; `GET /catalog/datacenters?networkVolumeTypes=STANDARD`
  → `dataCenters[]`. A volume attached to a running pod cannot be deleted (RunPod's global-volume docs; the network
  volume's delete documents no `409`). Standard storage is $0.07/GB a month under 1 TB.
- **The live runs:** `live`, `live-serve`, `live-dead`, `live-serve-dead` (`Makefile:21`, `:30`, `:47`, `:58`).
  `live/Dockerfile.dead` has no `curl`, so boot exits before `trap stop EXIT`; RunPod restarts the container and it
  never reads `EXITED` (`0009·L1`, `live/last_run.txt`).
- **No existing test turns red:** every change is additive — new keys, new methods on `FakeProvider`, a second status
  line only when a volume is recorded. Checked by `grep` for `build(`, `_placeable`, `USAGE` and `row.spec` in `tests/`.

## Goals / Non-Goals

**Goals:** a volume per working window, made and ended from `gpunit.toml`; no session outlives its volume; a forgotten
volume ends at the next command; `v0.6`'s acceptance run inside a window.

**Non-Goals:** a volume created by `up` or `serve`; high-performance or global volumes; a volume no command reaches
being deleted; `status --json` naming the volume.

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| [D1](#d1) | the seam gains a card's stock, the standard-volume data centres, a volume's create, listing and delete | the verbs need nothing else | a `Provider` per volume |
| [D2](#d2) | `volume_gb`, `volume_ceiling`, `volume_datacenter` in the spec, refused as spec faults | *infra as config*; every spec fault is exit `1` | CLI flags |
| [D3](#d3) | the data centre: the first placeable card's highest stock among standard-volume data centres | every pod of the window goes there | the cheapest data centre |
| [D4](#d4) | `.gpunit/volume` and `.gpunit/volume.pending`, beside the pod's | one record per project, as the pod | a record in the ledger alone |
| [D5](#d5) | `gpunit/volume.py`: `up` (create or extend, after the price) and `down` (delete, sweep by name after a lost create, on a `y` per volume) | the pod's lifecycle, for a volume | folding it into `lifecycle.py` |
| [D6](#d6) | `up` mounts the window volume by setting `spec.volume`; refuses no record, or a session that outlives it | the mount path exists | a second mount path |
| [D7](#d7) | `lifecycle.sweep_window` deletes an overdue volume first, in `up`, `status`, `volume up` and `volume down`; `down` after its pods | no chore to remember | a watcher pod |
| [D8](#d8) | `volume up --serve <row> --ceiling D`; `serve` mounts a recorded window volume | `serve` has no config file; no side effects | `serve` creating one |
| [D9](#d9) | volume lines in the ledger; `spend` bills a window volume under its project, names an overdue one | a window's storage is its project's | a storage line for every volume |
| [D10](#d10) | `make live-volume`; `live-serve` and `live-serve-dead` inside a window; `live-dead` asserts its reason | `v0.6`'s acceptance, in the window it now runs in | a dead image that reaches `EXITED` |
| [D11](#d11) | `gpunit-vllm`, `gpunit-live` and `gpunit-live-dead` rebuilt from `boot.sh` at HEAD, before the live runs | `0009·R6`, `0009·S3` | editing `v0.6.0`'s released entry |
| [D12](#d12) | README's *Working window*, the verbs, the exit `3` row; `CLAUDE.md`'s layout and live runs | the consumers' versions read it | — |
| [D13](#d13) | `serve/Dockerfile`'s `CMD` sets `HF_HOME` with an `if`, tested by running it under `sh`; `gpunit-vllm` rebuilt as `v0.7-rc2` | the `${…:+…}` form breaks every mounted volume | carding it past this change |
| [D14](#d14) | `RunPod.log` with `since` reads the last 5000 lines and keeps those stamped from that second on; the host-key poll makes one tail read, bounded at 5000 lines | RunPod's `since` stream sends no past line | a backfill; `Last-Event-ID` |

### D1

`Provider` gains, and `RunPod` and `FakeProvider` implement:

```
def stock(self, card: str) -> list[tuple[str, str]]: ...  # (data centre, availability), NONE dropped; Unknown, Lost
def volume_datacenters(self) -> set[str]: ...  # data centres offering STANDARD; Lost
def create_volume(self, name: str, size_gb: int, datacenter: str) -> str: ...  # id; Refused on 400/422, else Lost
def volumes(self, name: str) -> list[str]: ...  # ids of the volumes named `name`; Lost
def delete_volume(self, volume_id: str) -> int: ...  # the status; 0 when no answer came
```

`create_volume` sends `type: "STANDARD"`. `volumes` walks the pages as `list` does, with its `MAX_PAGES` and repeated
cursor guards.

### D2

`Spec` gains `volume_gb: int | None`, `volume_ceiling_s: int | None`, `volume_datacenter: str | None`. `load_spec`
refuses: `volume_gb` outside 10–4000; `volume_gb` without `volume_ceiling`; `volume_ceiling` or `volume_datacenter`
without `volume_gb`; `volume` and `volume_gb` together, naming both; a `volume_ceiling` `parse_ceiling` rejects. Each is
`log.refuse`, exit `1`, as every spec fault is.

### D3

`volume_datacenter` set → it, with no stock read. Else: `standard = provider.volume_datacenters()`; for each card of
`lifecycle.placeable(spec, provider)` in order, the first `(dc, availability)` of `provider.stock(card)` with `dc` in
`standard`, ranked `HIGH` > `MEDIUM` > `LOW`. None → `log.refuse("no card of gpus is in stock in a data centre with
standard volumes: <cards>")`. `_placeable` becomes public `placeable`; `up` calls it by the new name.

### D4

`State` gains `volume` (`.gpunit/volume`) and `volume_pending` (`.gpunit/volume.pending`), and a `Window` record:
`id`, `datacenter`, `size_gb`, `ends` (UTC, `2026-10-15T14:30:00Z`). `window()` reads it or None; `write_window`
writes it whole, as `write` does; `mark_volume_pending`, `clear_volume_pending`, `clear_window`.

### D5

`gpunit/volume.py`:

```
up:    sweep_window → pending? refuse → no volume_gb? refuse
       ├─ a live record: price the new window → ends = now + volume_ceiling → write, ledger
       └─ none: D3's data centre → price → mark pending → create_volume
                ├─ Refused: clear pending, refuse with the provider's words
                ├─ Lost: keep pending, say "run gpunit volume down", raise Lost (exit 3)
                └─ id: write the window, ledger, clear pending; say id, data centre, end
down:  sweep_window → delete the record's volume → 204: clear the window
       → no pending mark: done, exit 0, or 1 when the record's delete failed
       → pending: volumes(gpunit-<project>) → delete each other
       → every 204: clear the pending mark, exit 0; else keep it, say the answer, exit 1
```

**Amended in converge (`0010·S1`, `0010·R1`):** the name sweep runs only while `.gpunit/volume.pending` exists, the one
case where a volume of this checkout can go unrecorded; without the mark, any other `gpunit-<project>` volume is
another checkout's, a teammate's on the same account, or one made by hand, and a network volume's delete cannot be
undone. The record is cleared on its own `204`, before the sweep, so a sweep that fails after it leaves no record of
a deleted volume for every later `volume down` to 404 on; only the pending mark waits for the sweep.

**Amended in converge (`0010·S2`):** the mark alone does not prove a listed volume is this checkout's: a teammate's on
the same account, or another clone's, carries the same name. So the sweep narrows three ways:

```
down:  … → pending and a record: the create came back; clear the mark, no listing
       → pending, no record: volumes(gpunit-<project>) → skip each id ledger.volumes() records
       → each other: ask "delete volume <id>, named gpunit-<project> but in no record? [y/N]"
                ├─ y: delete; 204 says "swept volume <id>", else the answer, and the mark stays
                ├─ any other answer: keep it, "volume <id> kept"
                └─ no answer (EOF, Ctrl-C): keep it and the mark, name `gpunit volume down`, exit 1
       → no delete failed and every one answered: clear the mark, exit 0
```

`volume down` gets no `--yes`: `volume up`'s `--yes` agrees to a price, and nothing on the command line can vouch that
a volume of the name is this checkout's. The question is `volume up`'s `[y/N]`, no by default; a run with no terminal
deletes nothing and keeps the mark, so `volume up` keeps refusing until a person answers. A `n` settles the mark: the
person judged that volume another's. The ledger skip needs no question because a ledger line is written only after a
create's answer arrived, and a lost create, the one volume the sweep is for, therefore has none.

**The price:** `VOLUME_GB_MONTH = Decimal("0.07")`, `HOURS_A_MONTH = 730`; at most
`size_gb × 0.07 × ceil(volume_ceiling_s / 3600) / 730`, up to the cent. It prints `price: $0.07/GB a month` and
`at most $<x> for <n> GB over <ceiling>`, then asks `create volume gpunit-<project> for at most $<x>? [y/N]` (`extend …`
for a live one); anything but `y` refuses `not created`. `--yes` skips the question.

### D6

In `lifecycle.up`, after `sweep_window` and before `_refuse_listed`: when `spec.volume_gb` is set, read `state.window()`;
None → `log.refuse("no window volume is up; run gpunit volume up")`; `now + spec.ceiling_s + spec.timeout_s` after
`ends` → `log.refuse("the volume ends at <ends>; shorten the ceiling or run gpunit volume up")`; else
`spec = replace(spec, volume=window.id)`. The existing path then reads the volume, pins its data centre and mounts it.

### D7

`lifecycle.sweep_window(state, provider)`: a window whose `ends` has passed → `delete_volume`; `204` → clear it, say
`volume <id> passed its ceiling at <ends>; deleted`; else keep it and warn with the answer. `provider` is a callable,
built only for that delete. `up` then refuses naming `gpunit volume up` when `spec.volume_gb` is set and the record is
gone or still past its end. It is called first in `lifecycle.up`, `lifecycle.down`, `lifecycle.status`, `volume.up`
and `volume.down`; `run` and `serve` reach it through `up`. So `status` builds the provider only when a window is
overdue, keeping *no record needs no key*.

**Amended in converge (`0010·R2`):** `lifecycle.down` sweeps the window after its pod delete and pod sweep, not first:
a stopped pod still holds its volume, so a delete before the pod's is refused, and `down` would exit `0` with the
volume billing. The sweep runs whatever the pods' outcome; its failure still only warns.

### D8

`cli`: `volume` takes `up` or `down`; with `--serve <row>`, `up` requires `--ceiling`, and the spec is the row's spec
with `volume_gb = row.disk_gb` and `volume_ceiling_s` the ceiling, the state `State(home(row))`. `serve`: when
`volume` is None and `State(home(name)).window()` exists, `spec = replace(spec, volume_gb=row.disk_gb)`, so D6 mounts
it; with no window, nothing changes. The image keeps the weights on `GPUNIT_VOLUME_PATH`, per [D13](#d13).

### D9

`ledger.record_volume(project, volume_id, ends)` appends `{"id", "project", "kind": "volume", "ends", "at"}`;
`ledger.volumes()` returns each id's project and its last line's `ends`. `read` skips volume lines already: they lack
`card` and `image`. `spend` adds a window volume's charges to its project's amount — a project line with no pod shows
`0 pods` — and keeps other volumes on storage lines; a window volume whose `ends` has passed and whose billing holds a
charge on the window's last day is named on stderr: `volume <id> (<project>) passed its ceiling and still bills; run
gpunit volume down`.

### D10

- **`make live-volume`:** `live/gpunit.volume.toml` (the `live` image and cards, `ceiling = "10m"`,
  `volume_gb = 10`, `volume_ceiling = "30m"`); `volume up --yes`; a `run` that writes the UTC time to
  `/runpod-volume/proof` and prints it; a second `run`, on a new pod, that prints the file; the target fails unless the
  printed lines are equal; `volume down`; `status`.
- **`make live-serve`** runs between `volume up --serve $(MODEL) --ceiling 1h --yes` and `volume down --serve
  $(MODEL)`, a `trap` running the `down` on any exit; its endpoint session downloads into the volume and its chat
  session, a new pod, loads from it.
- **`make live-serve-dead`** runs the same way for `qwen3-4b`.
- **`make live-dead`** keeps its image, and asserts `up` exits `1` and prints its refusal's reason as `reason: <line>`.
  The dead-pod rule's live proof is `make live-serve-dead`, on the same `DeadPod`; `live/last_run.txt` says so.

### D11

`gpunit-vllm` through `.github/workflows/build-serve-image.yml` with the tag `v0.7-rc1`; `gpunit-live` and
`gpunit-live-dead` by `docker buildx build --platform linux/amd64 --push`; each digest replaces the old at
`gpunit/serve/models.toml:2`, `live/gpunit.toml:4`, `live/gpunit.dead.toml:4`. The CHANGELOG says the images now
carry the released `boot.sh`, and that `v0.6.0`'s digests carried `057ce89`'s.

### D12

README: `volume_gb`, `volume_ceiling`, `volume_datacenter` in the spec sample; a *Working window* section — the command
order for a project and for `serve`, the ceiling rule, and the residual: a volume no command reaches bills
$0.07/GB a month; `volume up` and `volume down` in *The verbs*; the exit `3` row names a volume's create.
`CLAUDE.md`: `volume.py` in the layout; `make live-volume` among the live runs never in CI.

### D13

Found by `make live-serve` on 2026-10-16, after the cut: the `CMD`'s
`${GPUNIT_VOLUME_PATH:+export HF_HOME="…";} exec vllm serve …` keeps the `;` as a word, so with a volume mounted `sh`
runs one `export` over vLLM's arguments, which refuses `Qwen/Qwen3-4B` as a name and exits `2` before vLLM starts.
It dates from `93c9081`; `serve --volume` broke the same way. The `CMD` becomes
`if [ -n "${GPUNIT_VOLUME_PATH:-}" ]; then export HF_HOME="$GPUNIT_VOLUME_PATH/huggingface"; fi; exec vllm serve …`.
`tests/test_serve_image.py` runs the `CMD` from the Dockerfile under `sh` with a stub `vllm`, with and without the
volume. `gpunit-vllm` is rebuilt through the workflow with the tag `v0.7-rc2` and re-pinned in `gpunit/serve/models.toml`.

### D14

Found by a probe pod on 2026-10-16, after `make live-serve-dead` kept no `pod:` line. On one live pod, the
`.minions/` probe read the container log each way:

| read | status | first byte | lines |
|---|---|---|---|
| `tail=50&source=container` | 200 | 0.55 s | 4 |
| `since=<created>&source=container` | 200 | 15.74 s, `: heartbeat` | 0 |
| `since=<created>`, no `source` | 200 | 15.48 s, `: heartbeat` | 0 |
| `since=<an hour before>&source=container` | 200 | 15.52 s, `: heartbeat` | 0 |

RunPod's docs say `since` drives the backfill; live, it sends none. So every `since` read gpunit made was empty: the
host-key fallback, the older-`boot.sh` judgment and `serve`'s `pod.log`. `RunPod.log` keeps the `Provider` contract
— with `since`, the lines from then on — by sending `tail=5000&source=container` and keeping each event whose `ts`,
to the second, is at or after `since`; an event with no `ts` is kept. The cost: a log longer than 5000 lines since
the create is read from its last 5000.

**Amended in converge (`0010·R3`):** a `since` read is then a subset of the host-key poll's own `tail=5000` read, so
the fallback to it could never find a key line the tail had lost; `session:hostkey:since-fallback` held only because
`FakeProvider` scripted `since_logs` apart from `logs` within one poll. A true backfill was rejected: RunPod's `since` sends no
past line (the probe above), and `Last-Event-ID` stays rejected. So the bound is stated, not hidden:

- `_verify_host_key` makes one read a poll, the last 5000 lines with no `since`; a key line further back is not read,
  and the poll tears down at its 60 seconds, as for no line at all.
- The older-`boot.sh` judgment runs only on a read of fewer than 5000 lines, which holds the whole log and so boot's
  own lines; a full tail can hold only a command's echo of an older key line, and is not judged.
- The session spec's host-key requirement is removed and re-added as *verified from the log's tail*, since OpenSpec
  cannot drop a scenario through `MODIFIED`: `session:hostkey:tail-bound` replaces `session:hostkey:since-fallback`.
- `Provider.log`'s and `RunPod.log`'s docstrings name the provider's tail as the bound of a `since` read; the
  `created` comment in `lifecycle.up` says the same. `FakeProvider` keeps `since_logs` for `serve`'s reads, which
  are later reads of the tail, and no test scripts a poll whose `since` read holds a line its tail read has lost.
- `RunPod.log`'s `since` tests move to `serve:wait:log-kept`, `serve`'s `pod.log` being the one `since` reader left.

## Dependencies

None.

## Risks / Trade-offs

- **Stock moves between `volume up` and a later pod** → the pod refuses naming the data centre; `volume down` and
  `volume up` again choose afresh.
- **A pod still attached at the volume's end blocks its delete** → D6 keeps a session inside the window; a stranded
  pod's delete fails, the record is kept and the next command retries.
- **A volume no command reaches bills on** → README names it; `spend` names it once it shows in the billing.
- **The price is a constant, not read from the provider** → RunPod's docs give it; the bill is `spend`'s, never the
  estimate's.
- **Hourly billing rounds a window up** → the price counts whole hours.

## Verdict

Feasible: the mount path, the pending-mark pattern and the price question exist; the new seam calls are documented;
the one unknown — the delete of a volume a pod still holds — fails safe, keeping the record.
