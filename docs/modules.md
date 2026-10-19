# Modules

Where each part of gpunit lives, the layer it sits in, and what it may import. A module imports its own layer,
without a cycle, and the layers below ([D49](decisions.md#d49--the-layers-held-by-teststest_layerspy)).
`tests/test_layers.py::LAYERS` holds the same table, and the gate fails when the two differ.

## The layers

Lowest last. A new module edits this table and `LAYERS` together.

| layer | modules |
|---|---|
| interface | `gpunit` · `gpunit.__main__` · `gpunit.cli` |
| serve | `gpunit.serve` · `gpunit.serve.table` · `gpunit.serve.chat` · `gpunit.serve.session` |
| session | `gpunit.library` · `gpunit.run` |
| lifecycle | `gpunit.lifecycle` · `gpunit.hostkey` · `gpunit.volume` · `gpunit.spend` |
| cloud | `gpunit.runpod` |
| model | `gpunit.spec` · `gpunit.state` · `gpunit.provider` · `gpunit.ledger` · `gpunit.contract` |
| foundation | `gpunit.log` · `gpunit.version` |

The main edges, each pointing down:

```
 interface   gpunit · __main__ ─▶ cli ─┬─▶ run · runpod · lifecycle
     │                                 └─▶ spend · volume · serve.*, lazy
     ▼
 serve       serve.session ─▶ serve.chat · serve.table
     ▼
 session     run ─▶ library ─▶ lifecycle · runpod
     ▼
 lifecycle   volume ─▶ lifecycle ─▶ hostkey        spend
     ▼
 cloud       runpod ─▶ contract
     ▼
 model       provider ─▶ spec    ledger ─▶ state    contract ─▶ spec
     ▼
 foundation  log · version
```

The rules beside the layers, each in `tests/test_layers.py`: nothing imports the package `gpunit` itself; the
package imports the standard library and `gpunit` alone, and `serve/launch.py` the standard library alone; `sys.exit` is called in `cli` alone.

## Each module

- `gpunit` — the public names: `session`, `Session`, `Refused`, `Lost`, `TeardownFailed`, `Interrupted`,
  `load_spec`, `__version__`.
- `gpunit.__main__` — `python -m gpunit`.
- `gpunit.cli` — parses the verbs, runs one, turns its outcome into the exit code.
- `gpunit.serve` — the `serve` package.
- `gpunit.serve.table` — the bundled table and the user file; a row's `Spec`.
- `gpunit.serve.chat` — the streamed chat in the terminal.
- `gpunit.serve.session` — a row on a session: the price, the wait for the model, the chat or the `--api` hold.
- `gpunit.library` — the session from Python: one `with` block, its signals, its tunnel, its teardown.
- `gpunit.run` — `gpunit run`: one command against a session that lives as long as it does.
- `gpunit.lifecycle` — `up`, `status`, `down` and `ssh`; placement, the wait, the window's sweep, the volume delete.
- `gpunit.hostkey` — the host key, proven over the authenticated log before anything connects.
- `gpunit.volume` — `volume up` and `volume down`: the window volume.
- `gpunit.spend` — `spend`: the billing over whole UTC days, by project.
- `gpunit.runpod` — RunPod's REST v2 behind the seam, on `urllib`.
- `gpunit.spec` — `gpunit.toml` into a `Spec`, refusing what no session may open on.
- `gpunit.state` — the session's files under `.gpunit/`, and gpunit's home state.
- `gpunit.provider` — the seam: the `Provider` protocol, its types and its exceptions.
- `gpunit.ledger` — each pod's and window volume's project, under the home directory.
- `gpunit.contract` — the laptop's half of the boot contract: the pod's env, and the lines boot prints back.
- `gpunit.log` — gpunit's lines, UTC-stamped, to stderr or a sink.
- `gpunit.version` — `__version__`, which hatch reads and `gpunit.runpod` sends as its User-Agent.

## Where RunPod is built

`gpunit/library.py::session` builds it from the environment it is given; `gpunit/cli.py::_run` builds it when a verb
first asks. `run` and `serve` open through `gpunit/library.py::open_session` with the provider already built, and the
tests pass a `FakeProvider` there. A second provider changes these sites (`0015·F2`).

## The lazy edges

`gpunit.cli` imports `gpunit.spend`, `gpunit.volume`, `gpunit.serve.session` and `gpunit.serve.table` inside the
function that runs their verb, so a verb loads only what it uses. The layer test reads these imports too.

## The test seams

What the tests replace, and where it lives:

| seam | replaced for |
|---|---|
| `gpunit/lifecycle.py::CLOCK` | every wait's time, by `tests/conftest.py`'s `clock` |
| `gpunit/lifecycle.py::NONCE` | the session's nonce, so the fakes' key line matches |
| `gpunit/spend.py::utc_now` | the day `spend` counts back from |
| `gpunit/log.py::_sink` | where gpunit's lines go |
| `gpunit/library.py::TUNNEL_POLL_S`, `gpunit/library.py::REOPEN_FIRST_S` | a fast tunnel watcher |
| `gpunit/serve/table.py::load` | the bundled table |

## Known shape

`gpunit/library.py` holds both the session and the tunnel; the tunnel moves to its own module at the next tunnel
change (`0015·F8`).
