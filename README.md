# gpunit

[![gate](https://github.com/alxb1t/gpunit/actions/workflows/gate.yml/badge.svg)](https://github.com/alxb1t/gpunit/actions/workflows/gate.yml)

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

## What holds

| rule | held by |
|---|---|
| the host key is proven over the provider's log, with a session nonce, before anything connects | [D22](docs/decisions.md#d22--the-host-key-is-proven-over-the-log) |
| the pod enforces its own spend ceiling, with the laptop asleep | [D25](docs/decisions.md#d25--the-pod-stops-at-its-ceiling-and-on-any-end-down-deletes) |
| a pod or a window volume is gone only when its read and the account's listing both lack it | [D57](docs/decisions.md#d57--a-pod-is-gone-when-its-read-and-the-accounts-listing-both-lack-it) |
| nothing is rented without the price and a `y` | [D35](docs/decisions.md#d35--the-price-first-yn---yes-skips-it) |
| the standard library alone, no runtime dependency | [D1](docs/decisions.md#d1--a-flat-stdlib-package-python-311-no-runtime-dependency) |
| `boot.py` at 100 % line and branch coverage | [D5](docs/decisions.md#d5--the-gate-fakes-every-provider-answer-bootpy-at-100-) |

## Try it

A `gpunit.toml`, an image whose entrypoint is `boot.py`, and gpunit [from a release tag](docs/usage.md#use-it-from-a-project):

```toml
project = "demo"
image = "ghcr.io/you/demo@sha256:<64 hex>"
gpus = ["NVIDIA RTX A5000", "NVIDIA A40"]
vram_gb = 24
ceiling = "15m"
disk_gb = 20
```

```sh
export RUNPOD_API_KEY=...
uv run gpunit run -- sh -c '$GPUNIT_SSH nvidia-smi'
```

```python
import gpunit

with gpunit.session("gpunit.toml") as s:
    print(s.host, s.port(8188))
```

`gpunit serve qwen3-4b --ceiling 2h` chats with a model on a rented card ([how](docs/usage.md#serve-a-model)).

[usage](docs/usage.md) · [proofs](docs/proofs.md) · [architecture](ARCHITECTURE.md) ·
[threat model](THREAT_MODEL.md) · [CHANGELOG](CHANGELOG.md) · [LICENSE](LICENSE)
