# Extending gpunit

A recipe for each kind of change: the files to touch, the spec to change, the tests and the proof. Every change is
cut, built, checked and released as one OpenSpec change under `openspec/changes/`, and ends on a green `make gate`.

## A verb

- **Files:** `gpunit/cli.py::_parser` for the arguments and `USAGE`, `gpunit/cli.py::_run` to dispatch; the verb's
  own module in its layer ([modules](modules.md)). A verb that only some runs need is imported inside its function,
  as `spend`, `volume` and `serve` are.
- **Spec:** `openspec/specs/cli/spec.md`, plus the capability the verb belongs to.
- **Tests:** `tests/test_cli.py` and the module's own `tests/test_<module>.py`, on `tests/fakes.py::FakeProvider`.
- **Docs:** `docs/usage.md`'s *The verbs*, and a line in [modules](modules.md) for a new module.
- **Version:** a new verb needs a `vX.Y`, never a patch
  ([D8](decisions.md#d8--a-patch-closes-cards-it-adds-no-verb-gpunittoml-key-or-exit-code)).

## A gpunit.toml key

- **Files:** `gpunit/spec.py`: the key in `_REQUIRED` or `_OPTIONAL` with its TOML types, a field on `Spec`, and its
  check in `load_spec`. A key that reaches the pod goes through `gpunit/contract.py::pod_env` or
  `gpunit/runpod.py::RunPod.create`.
- **Spec:** `openspec/specs/spec/spec.md`.
- **Tests:** `tests/test_spec.py`: the key read, and each fault refused before any request, naming the field.
- **Docs:** `docs/usage.md`'s *Use it from a project*; [the threat model](../THREAT_MODEL.md) when the key reaches
  the pod or the API.
- **Version:** a `vX.Y`.

## A serve row

Your own model needs no change to gpunit: it is a row of your user file, read beside the bundled ones. A bundled row
is a change:

- **Files:** `gpunit/serve/models.toml`: the row's repository at a pinned revision, its cards, its flags.
- **Spec:** `openspec/specs/serve/spec.md`'s *the table loads* names the bundled rows, so a new row edits it; a row that
  needs a new key edits its requirement and `gpunit/serve/table.py` too.
- **Tests:** `tests/test_serve_table.py::test_the_bundled_table_holds_both_rows_at_pinned_revisions` names the rows;
  a faulty row fails the gate.
- **Version:** a `vX.Y`.
- **Proof:** `make live-serve MODEL=<row>`, by hand ([D6](decisions.md#d6--the-metered-proofs-run-by-hand-the-price-first-their-tails-committed-a-boot-change-rebuilds-the-images)).
- **Docs:** `docs/usage.md`'s *Serve a model*.

## A provider

A second provider implements `gpunit/provider.py::Provider` in a module of the cloud layer, beside
`gpunit.runpod`, and adds it to `tests/test_layers.py::LAYERS` and [modules](modules.md), and has
`gpunit/providers.py::build` return it. What it meets today:

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
- **Proof:** the live targets on the new images. [The threat model](../THREAT_MODEL.md) moves with any new line, env
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
- **Docs:** edit `docs/proofs.md`: the target's section, and its latest run.

## The rules

The rules for a change are in [the contribution guide](../CONTRIBUTING.md#the-rules-for-a-change).
