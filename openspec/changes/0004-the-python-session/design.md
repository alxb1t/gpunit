# Design — 0004 the Python session

How the lifecycle becomes a library: one context manager owning the session, the failures, the signals, the tunnel
and the log, with `gpunit run` rebuilt as its first caller. **Verdict: feasible** — every part already runs inside
`run`; the work moves it behind an object and tests it there.

## Context

See [proposal](proposal.md) — *Why*. What holds at the cut, `main` at `0841e07` (`v0.1.2`):

- **`run`** (`gpunit/run.py:79-200`) owns everything around `up` and `down`: `_refuse_busy_ports` (`:195`), the
  signal handler in `_Children` (`:28-46`), the teardown guard keyed on `state.began` (`:119-128`), the command and
  tunnel children in `_supervise` (`:137-171`), `_tunnel` (`:174`), `_Backoff` (`:49-76`), `_kill` (`:186`), and the
  exit codes (`:129-134`). `TUNNEL_POLL_S`, `REOPEN_FIRST_S`, `REOPEN_CAP_S` sit at `:17-21`.
- **`session.up` and `session.down`** (`gpunit/session.py:49`, `:147`) are already plain functions on a `Spec`, a
  `Provider` and a `State`.
- **`log`** (`gpunit/log.py`): `say` prints `<UTC> <text>` to stderr (`:17-19`); `refuse` says and raises `Refusal`
  (`:22-25`). `provider.Refused` (`gpunit/provider.py:64`) is a different thing: a create's 400.
- **`RunPod(environ=…)`** reads the key from the mapping it is given (`gpunit/runpod.py:66`); the create's pod
  environment is `[env]` plus `PUBLIC_KEY` and `GPUNIT_CEILING` (`:123`); `VOLUME_PATH` is `/runpod-volume`
  (`:35`).
- **`_env`** (`gpunit/spec.py:152-156`) checks only that each value is a string.
- **The CLI's tests** reach `run` through `cli.main(argv, provider=FakeProvider())` (`tests/helpers.py`); two of them
  patch `run.TUNNEL_POLL_S`, `run.REOPEN_FIRST_S` and call `run._Backoff` (`tests/test_run.py:233-234`, `:252`).

## Goals / Non-Goals

**Goals:** one implementation of the session, public in Python, with the CLI on top; the pod told its volume in
gpunit's words.

**Non-Goals:** a second provider; a change to `boot.sh`; a fake for consumers; a promise about anything private.

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| [D1](#d1) | `gpunit/library.py`: `session()` a context manager over `_open(spec, provider, state, say)`; `Session` frozen | the public call builds the provider from `environ`; the tests inject a `FakeProvider` into `_open` | a class users construct |
| [D2](#d2) | `Refused` is `log.Refusal`; `Lost` is `provider.Lost`; `TeardownFailed` and `Interrupted` new in `library.py` | one exception per outcome the CLI already distinguishes | an error code on the object |
| [D3](#d3) | signal handlers installed on open, raising `Interrupted(signal)`; `SIG_IGN` during the teardown; restored after; main thread only | `run`'s single loop gave this; a library must keep it | `KeyboardInterrupt` alone, which names no signal |
| [D4](#d4) | the tunnel watched by a daemon thread with `_Backoff`, stopped by an `Event` before the teardown | there is no main loop to poll from | polling in `s.port()` |
| [D5](#d5) | `log.say` writes through a module sink; `session(say=…)` swaps it for its life; the default sink swallows `BrokenPipeError` and `ValueError` | the tunnel thread logs too; a dead pipe ends no teardown | a logger object threaded through every call |
| [D6](#d6) | `run` = busy ports, `with _open(...)`, the command child, exit codes from the exceptions | one implementation; the CLI's specs prove the library | two lifecycles |
| [D7](#d7) | `RunPod.create` adds `GPUNIT_VOLUME_ID`, `GPUNIT_VOLUME_PATH` when `volume` is set; `_env` refuses a `GPUNIT_` key | the path is the provider's; `boot.sh` passes the environment on | `boot.sh` exporting them |
| [D8](#d8) | README gains *Use it from Python*; `CLAUDE.md`'s layout names `library.py` | the README is the promise | — |
| [D9](#d9) | `make live` by hand on the existing live image | `run` is rebuilt; the gate fakes the pod | a rebuilt image: `boot.sh` is unchanged |

### D1

```python
@contextmanager
def session(
    spec: str | Path | Spec,
    *,
    environ: Mapping[str, str] | None = None,
    cwd: Path | None = None,
    say: Callable[[str], None] | None = None,
) -> Iterator[Session]:
    provider = RunPod(environ if environ is not None else os.environ)
    with _open(_spec(spec), provider, State(cwd or Path.cwd()), say) as s:
        yield s
```

`Session` is a frozen dataclass: `host`, `pod_id`, `image`, `ssh` (the argv of `session.ssh_command`), and
`port(remote) → local`, refusing a remote port the spec does not forward. `_open` refuses busy ports, installs the
handlers ([D3](#d3)), runs `session.up`, starts the tunnel ([D4](#d4)), yields, and in its `finally` tears down when
`state.began` or a create was lost, exactly as `run`'s guard does today.

```
open ─▶ busy ports ─▶ handlers ─▶ up ─▶ tunnel thread ─▶ yield s
                                                           │ block ends, raises, or a signal
                                                           ▼
                        restore ◀─ down (signals ignored) ◀─ stop tunnel
```

### D2

`gpunit/__init__.py` exports `session`, `Session`, `Refused`, `Lost`, `TeardownFailed`, `Interrupted` and
`load_spec`. `TeardownFailed(Exception)` is raised from `_open`'s `finally` when `down` returns non-zero, `raise …
from` the exception that ended the block. `Interrupted(KeyboardInterrupt)` carries `signal: int`.
`provider.Refused` stays private.

### D3

`_open` checks `threading.current_thread() is threading.main_thread()` first, refusing otherwise. It saves the
handlers for `SIGINT`, `SIGTERM`, `SIGHUP` and sets one that raises `Interrupted(number)` once; a later signal
before the teardown is ignored, as `_Children.handle` does. The teardown sets `SIG_IGN` for all three, and the
outer `finally` restores the saved ones.

### D4

`_Tunnel` in `library.py` holds the child, a `threading.Event` and the `_Backoff`. Its thread polls every
`TUNNEL_POLL_S`; on an exit it logs `the tunnel exited (<code>); reopening it in <n>s` and reopens when due.
`stop()` sets the event, joins the thread and `_kill`s the child. `_tunnel`, `_kill`, `_Backoff`, `TUNNEL_POLL_S`,
`REOPEN_FIRST_S`, `REOPEN_CAP_S` move from `run.py` to `library.py`.

### D5

`log.py` gains `_sink`, `redirect(sink)` (a context manager restoring the previous one) and a default sink that
prints to stderr and swallows `BrokenPipeError` and `ValueError` (a closed stream). `say` writes `<UTC> <text>`
through `_sink`; `refuse` is unchanged.

### D6

`run.run(spec, provider, state, command)` keeps its signature for the CLI. It opens `_open(...)`, starts the
command with `GPUNIT_HOST`, `GPUNIT_PORT_<remote>`, `GPUNIT_SSH` from the `Session`, and waits. On `Interrupted`
it terminates the command, waits for it, and re-raises. It maps the outcome: the command's code (`128 + n` for a
signal-killed command), `Refused` → `1`, `Lost` → `3`, `TeardownFailed` → `1` (`3` after a lost create),
`Interrupted(n)` → `128 + n`.

### D7

`RunPod.create`'s environment becomes `{**spec.env, "PUBLIC_KEY": …, "GPUNIT_CEILING": …}` plus, when
`spec.volume` is set, `"GPUNIT_VOLUME_ID": spec.volume, "GPUNIT_VOLUME_PATH": VOLUME_PATH`. `_env` refuses a key
that starts with `GPUNIT_`, naming it.

### D8

README *Use it from Python*: the `with` block, the attributes, the exceptions, the signal rule, `environ` and
`say`, and the main-thread rule. *The verbs* says `run` is the same session. `CLAUDE.md`'s *Layout* gains
`library.py` (the public session) and drops `run`'s tunnel from `run.py`'s line.

### D9

A **HUMAN · METERED** phase: `make live` with `RUNPOD_API_KEY` set, on the image `live/gpunit.toml` pins today;
confirm no pod is left; append the tail to `live/last_run.txt`.

## Dependencies

None.

## Risks / Trade-offs

- **A caller's own SIGTERM handler is replaced for the block's life** → restored on close; README says so.
- **A signal between `up`'s create and its record** → `state.began` is already set by `mark_pending`, so the
  teardown sweeps, as `run` does today.
- **The tunnel thread logs while the caller's sink is not thread-safe** → the sink is called from two threads;
  README says a sink must accept that.

## Verdict

Feasible: the lifecycle is already functions; `run`'s guards move behind one context manager, and the CLI's own
specs prove it unchanged.
