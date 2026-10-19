# Pins

Every input that shapes a pod or the build is pinned: where each pin is declared, what checks it, and how it moves.
The values live in the files named here, never on this page
([D50](decisions.md#d50--the-guide-why-flow-and-where-never-a-value-symbols-and-decision-ids-cited-held-by-teststest_docspy)).

| pin | declared in | checked by | moves by |
|---|---|---|---|
| the vLLM base image, by tag and digest | `serve/Dockerfile`'s `FROM` | `test_the_image_is_built_from_pinned_inputs` | editing the `FROM`, then rebuilding the serve image |
| the serve image, by digest | `gpunit/serve/models.toml`'s `image` | `gpunit/serve/table.py::load` refuses a missing digest | running `.github/workflows/build-serve-image.yml` by hand, then pinning its digest |
| the live images, by digest | `live/gpunit.toml`, `live/gpunit.volume.toml`, `live/gpunit.dead.toml` | `gpunit/spec.py::load_spec` refuses a missing digest (`test_an_image_without_a_digest_is_refused`) | building `live/Dockerfile` or `live/Dockerfile.dead` by hand, then pinning its digest |
| each row's model revision, a 40-hex commit | `gpunit/serve/models.toml`, `live/models.toml` | `gpunit/serve/table.py::_row` (`test_a_moving_revision_is_refused_naming_the_row`) | editing the row's `revision`, then `make live-serve MODEL=<row>` |
| each action, by commit | each workflow's `uses:` under `.github/workflows/` | `test_every_workflow_pins_its_actions` | editing the commit and its version comment |
| the locked environment | `uv.lock` | `make gate`, which syncs from the lock first | `uv lock`, with a dependency change human-approved |
| a consumer's `boot.py`, at a tag | the consumer's Dockerfile: `ADD --checksum=sha256:…` of `boot/boot.py` at a release tag | BuildKit, at the consumer's build | the consumer bumping the tag and the checksum; `docs/usage.md`'s *Use it from a project* shows the line |
| the OpenSpec CLI | recorded in `CLAUDE.md`, resolved on `PATH`; installed at that version by `.github/workflows/gate.yml` | `tests/test_ci.py` holds the two equal | editing both |
| the package's Python floor, 3.11 | `pyproject.toml`'s `requires-python` | nothing runs 3.11; `ruff` and `ty` read it as their target | a `vX.Y` change |
| `boot.py`'s Python, 3.10 | `pyproject.toml`'s `per-file-target-version` | `make gate`, which type-checks `boot/boot.py` as 3.10 | a change to the images' base, then to both |

## What the threat model relies on in vLLM

[The threat model](threat-model.md) holds two vLLM behaviours at the serve image's base: request logging is off by
default, and `--no-enable-log-requests` is its explicit off; output logging needs request logging. `serve/launch.py`
passes the off flag after every row's arguments, but vLLM rewrites argv and takes abbreviations, so a row's
arguments can still turn request logging on (`0015·F23`). A bump of the vLLM base re-reads both in the new version's source
and updates the threat model's *Sources*.

## How a pin moves

```
 edit the pin ──▶ its check (make gate) ──▶ rebuild what carries it ──▶ re-pin the digest ──▶ the live proof
```

A rebuild is by hand: `.github/workflows/build-serve-image.yml` runs on a dispatch alone, and the live images are
pushed from the laptop. The live proof that uses the pin runs last, by hand, its tail committed
([D6](decisions.md#d6--the-metered-proofs-run-by-hand-the-price-first-their-tails-committed-a-boot-change-rebuilds-the-images)).
