# gpunit

[![gate](https://github.com/alxb1t/gpunit/actions/workflows/gate.yml/badge.svg)](https://github.com/alxb1t/gpunit/actions/workflows/gate.yml)
[![license](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

**Rent a cloud GPU, use it, and tear it down on every way out.**

```
laptop                                           pod
gpunit run -- <cmd>                              boot.py -- <cmd>
 ├─ up: place · wait · verify host key ────────▶  ceiling armed · sshd · fingerprint
 ├─ ssh -N -L <ports>  ◀─────────────────────────▶ sshd
 ├─ <cmd> with GPUNIT_HOST, GPUNIT_PORT_*, GPUNIT_SSH
 └─ down: delete · sweep                          stops itself at the ceiling
```

## Why

Each project carried its own RunPod scripts, copied from the last and drifted apart. gpunit is the one session they
all open, use and close, from the CLI or from Python.

## Built so

| claim | held by |
|---|---|
| the host key is proven over the provider's log, with a session nonce, before anything connects | [D22](docs/decisions.md#d22--the-host-key-is-proven-over-the-log) |
| the pod enforces its own spend ceiling, with the laptop asleep | [D25](docs/decisions.md#d25--the-pod-stops-at-its-ceiling-and-on-any-end-down-deletes), [D46](docs/decisions.md#d46--the-ceiling-in-a-forked-watchdog-the-stop-in-a-finally-retried) |
| teardown on every way out; a 404 is never "gone" | [D20](docs/decisions.md#d20--teardown-only-when-a-create-began-here-or-was-lost), [D23](docs/decisions.md#d23--teardown-a-404-keeps-the-record-the-projects-pods-are-swept) |
| nothing is rented without the price and a `y` | [D35](docs/decisions.md#d35--the-price-first-yn---yes-skips-it) |
| the standard library alone; `boot.py` at 100 % coverage | [D1](docs/decisions.md#d1--a-flat-stdlib-package-python-311-no-runtime-dependency), [D5](docs/decisions.md#d5--the-gate-fakes-every-provider-answer-bootpy-at-100-) |
| the layers and the docs held by tests | [D49](docs/decisions.md#d49--the-layers-held-by-teststest_layerspy), [D50](docs/decisions.md#d50--the-guide-why-flow-and-where-never-a-value-symbols-and-decision-ids-cited-held-by-teststest_docspy) |

## Try it

A `gpunit.toml` at the project root, for an image whose entrypoint is `boot.py`
([how](docs/usage.md#use-it-from-a-project)):

```toml
project = "demo"
image = "ghcr.io/you/demo@sha256:<64 hex>"
gpus = ["NVIDIA RTX A5000", "NVIDIA A40"]
vram_gb = 24
ceiling = "15m"
disk_gb = 20
```

```sh
uv add --dev git+https://github.com/alxb1t/gpunit@v0.11.1
export RUNPOD_API_KEY=...
uv run gpunit run -- sh -c '$GPUNIT_SSH nvidia-smi'
```

## Read more

[usage](docs/usage.md) · [proofs](docs/proofs.md) · [the guide](docs/README.md) ·
[threat model](docs/threat-model.md) · [CHANGELOG](CHANGELOG.md) · [LICENSE](LICENSE)
