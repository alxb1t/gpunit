# Extending gpunit

A recipe for each kind of change: the files to touch, the spec to change, the tests and the proof. Every change is
cut, built, checked and released as one OpenSpec change under `openspec/changes/`, and ends on a green `make gate`.

## A verb

- **Files:** `gpunit/cli.py::_parser` for the arguments and `USAGE`, `gpunit/cli.py::_run` to dispatch; the verb's
  own module in its layer ([modules](modules.md)). A verb that only some runs need is imported inside its function,
  as `spend`, `volume` and `serve` are.
- **Spec:** `openspec/specs/cli/spec.md`, plus the capability the verb belongs to.
- **Tests:** `tests/test_cli.py` and the module's own `tests/test_<module>.py`, on `tests/fakes.py::FakeProvider`.
- **Docs:** `README.md`'s *The verbs*, and a line in [modules](modules.md) for a new module.
- **Version:** a new verb needs a `vX.Y`, never a patch
  ([D8](decisions.md#d8--a-patch-closes-cards-it-adds-no-verb-gpunittoml-key-or-exit-code)).

## A gpunit.toml key

- **Files:** `gpunit/spec.py`: the key in `_REQUIRED` or `_OPTIONAL` with its TOML types, a field on `Spec`, and its
  check in `load_spec`. A key that reaches the pod goes through `gpunit/contract.py::pod_env` or
  `gpunit/runpod.py::RunPod.create`.
- **Spec:** `openspec/specs/spec/spec.md`.
- **Tests:** `tests/test_spec.py`: the key read, and each fault refused before any request, naming the field.
- **Docs:** `README.md`'s *Use it from a project*; [the threat model](threat-model.md) when the key reaches the pod
  or the API.
- **Version:** a `vX.Y`.

## A serve row

- **Files:** `gpunit/serve/models.toml`: the row's repository at a pinned revision, its cards, its flags. A row that
  needs no code changes nothing else.
- **Spec:** none, unless the row needs a new key: then `openspec/specs/serve/spec.md` and `gpunit/serve/table.py`.
- **Tests:** `tests/test_serve_table.py` reads the bundled table, so a faulty row fails the gate.
- **Proof:** `make live-serve MODEL=<row>`, by hand ([D6](decisions.md#d6--the-metered-proofs-run-by-hand-the-price-first-their-tails-committed-a-boot-change-rebuilds-the-images)).
- **Docs:** `README.md`'s *Serve a model*.

## A provider

A second provider implements `gpunit/provider.py::Provider` in a module of the cloud layer, beside
`gpunit.runpod`, and adds it to `tests/test_layers.py::LAYERS` and [modules](modules.md). What it meets today:

- **Where it is built:** `gpunit/library.py::session` and `gpunit/cli.py::_run` build `RunPod`; neither chooses
  (`0015·F2`).
- **HTTP statuses in the seam:** `delete`, `stop` and `delete_volume` return HTTP codes the callers compare
  (`0015·F3`).
- **RunPod's words outside `gpunit/runpod.py`:** the dead statuses, the stock levels, the log tail, the volume price
  and the key's name (`0015·F5`).
- **Boot's stop:** `boot/boot.py` stops a RunPod pod over RunPod's API (`0015·F14`).

Its tests are `tests/test_<provider>.py` on hand-written bodies in `tests/fixtures/`, as `tests/test_runpod.py`
does; the session tests stay on `FakeProvider`. Its proof is a live target against the new cloud.

## A boot.py change

- **Files:** `boot/boot.py`, one stdlib file for Python 3.10
  ([D45](decisions.md#d45--bootpy-one-stdlib-file-for-python-310-no-gpunit-import)).
- **Spec:** `openspec/specs/boot/spec.md`.
- **Tests:** `tests/test_boot_steps.py` for each step alone, `tests/test_boot.py` for the whole run; the gate holds
  `boot/boot.py` at 100 % line and branch, and type-checks it as 3.10.
- **Images:** the images carry `boot/boot.py`, so a change to its code rebuilds them and re-pins their digests:
  the serve image through `.github/workflows/build-serve-image.yml` into `gpunit/serve/models.toml`, and the live
  images from `live/Dockerfile` and `live/Dockerfile.dead` into `live/gpunit.toml`, `live/gpunit.volume.toml` and
  `live/gpunit.dead.toml`. A change to comments alone rebuilds nothing.
- **Proof:** the live targets on the new images. [The threat model](threat-model.md) moves with any new line, env
  name or network call.

## A pin bump

Each pin, where it is checked and how it moves, is in [pins](pins.md). A bump edits the pin, runs the check that
holds it, and runs the live proof that uses it.

## A live proof

- **Files:** `live/<name>.py` for the steps and the check, a `make live-<name>` target in `Makefile`, and
  `live/window.py` when the proof runs in a window volume.
- **Rules:** the price prints first, the run is by hand and never in CI, and whatever it rents is deleted however
  it ends ([D6](decisions.md#d6--the-metered-proofs-run-by-hand-the-price-first-their-tails-committed-a-boot-change-rebuilds-the-images)).
- **Tests:** the check's logic, offline, in `tests/test_live.py`.
- **Record:** the run's tail in `live/last_run.txt`, under a dated heading naming the change.

## The rules

- A refactor changes no spec scenario, message or exit code; tests change in names and imports alone
  ([D51](decisions.md#d51--a-refactor-changes-no-scenario-message-or-exit-code)).
- A new module edits `tests/test_layers.py::LAYERS` and [modules](modules.md) together
  ([D49](decisions.md#d49--the-layers-held-by-teststest_layerspy)).
- A decision made or overturned edits [decisions](decisions.md); the change's own `design.md` keeps the history.
- A change that adds a flow, secret, file mode, network call or log line edits [the threat model](threat-model.md)
  ([D9](decisions.md#d9--the-threat-model-lives-in-docs-and-moves-with-every-trust-boundary-change)).
- A patch adds no verb, `gpunit.toml` key or exit code
  ([D8](decisions.md#d8--a-patch-closes-cards-it-adds-no-verb-gpunittoml-key-or-exit-code)).
