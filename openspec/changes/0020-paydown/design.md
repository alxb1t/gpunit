# Design — 0020 paydown

The backlog's nine cards, each closed where it was found. **Verdict: feasible.**

## Context

`gpunit/serve/table.py::_args` refuses a space, `--enable-log-requests` exactly, and each flag (`_` → `-`, cut at
`=`) found in `_LAUNCHERS` exactly. vLLM `v0.31.0`'s `FlexibleArgumentParser` keeps argparse's `allow_abbrev=True` and
rewrites `_` to `-`, so a unique prefix of a launcher flag, `--enable_log_requests`, or a dotted flag that takes the
next argument as its value, all slip past. `serve/launch.py::main` appends `--no-enable-log-requests` last and checks
nothing. A pod runs the `launch.py` of the image `gpunit/serve/models.toml`'s `image` digest pins, built by
`.github/workflows/build-serve-image.yml` on a manual run.

`THREAT_MODEL.md`'s worker row and G17 say *only a pushed commit leaves it*; T20 reads `mitigated` with *a worker in
the checkout* among its actors. `gpunit/lifecycle.py::up`'s wait loop clears `.gpunit/pending` between rounds
(decision D56), so nothing guards the checkout while it sleeps; `gpunit/volume.py::_datacenter`'s wait is the same.

## Goals / Non-Goals

**Goals:** a row cannot reset a launcher flag or turn request logging on, on the laptop or on the pod; the threat
model states each route a worker has to the key; a second `up` or `volume up` during a wait refuses.

**Non-Goals:** F9; a sandbox rule for `.env`; a live serve run.

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| <a id="d1"></a>**D1** | `_args` reads each argument that opens with `-` as a flag: `_` → `-`, cut at `=`. It refuses a flag outside `^--[a-z0-9-]+$` (a `.`, a bare `--`, a capital); a flag equal to, or a prefix of, one of `_LAUNCHERS`; and a flag equal to, or a prefix of, one of `_LOGGING` = `--enable-log-requests`, `--enable-log-outputs`, `--log-level`, `--logging-config`. `--config` is refused by name. Each refusal names the flag: `'args' holds <flag>; the launcher sets it`, or `…; request logging stays off` | argparse resolves a unique prefix to its flag, and vLLM rewrites `_`; a closed name form stops the dotted and `--config` routes | refusing only the named abbreviations: the next vLLM adds flags |
| <a id="d2"></a>**D2** | `serve/launch.py` holds the same rule as `_FLAG`, `_LAUNCHERS` and `_LOGGING` of its own, checks `SERVE_ARGS` before `os.execvp`, and on a match prints `launch: SERVE_ARGS holds <flag>; refused` to stderr and exits `1` | the image's script runs on the pod with no gpunit package to import | importing `gpunit.serve.table`: the image holds `launch.py` alone |
| <a id="d3"></a>**D3** | T13, T30 and T55 drop their *The hole* sentences and read `mitigated`, naming the rule; `docs/usage.md`'s row bullets say a flag is read as vLLM reads it and name the refused families | the claims then hold | |
| <a id="d4"></a>**D4** | The worker row: *its network reaches the package index alone, and only a pushed commit leaves it* → *its network reaches the package index alone; what it reads goes to its model provider and its session transcript, and a pushed commit is published*. G17 names both routes and stays **accepted**. T20 reads `accepted`, its residual a worker reading `.env`, G17 its proof | the accept then rests on the true flow | denying the read: MinionsFactory's sandbox holds it |
| <a id="d5"></a>**D5** | `State.waiting` is `.gpunit/waiting`; `State.mark_waiting()` writes `os.getpid()`, `State.clear_waiting()` removes it. `lifecycle.stock_round` marks before its first sleep; `lifecycle.up` and `volume.up` clear it in a `finally` around their wait. `lifecycle.refuse_waiting(state)`, asked by `_guarded` and `volume.up`: a mark naming another live pid (`os.kill(pid, 0)`) refuses, `a session is waiting for stock in this checkout (pid <n>)`; a dead or unreadable one is removed, `removed a stale wait mark (pid <n>)`; its own pid passes | a mark the process owns, cleared on every way out, and one `kill -9` cannot leave stuck | a lock file held open: a crash leaves it as a mark too |
| <a id="d6"></a>**D6** | After the code: the version branch pushed, `build-serve-image.yml` run on it with the tag `v0.12.1-rc1`, and the digest its summary prints set in `gpunit/serve/models.toml`'s `image`, by a person | a pod runs the image's `launch.py`; a worker reaches neither GitHub nor a token | an unrebuilt image: the launcher half would hold nowhere |
| <a id="d7"></a>**D7** | `0017·R6` and `0017·R7` close won't-fix: they name `openspec/changes/archive/0017-mf-readiness/`'s `tasks.md` and `design.md`; `THREAT_MODEL.md` already has G17 close T20 | an archived change is a record (decision D7) | editing the archive |

## Tests

| layer | adds | removes |
|---|---|---|
| unit | `tests/test_serve_table.py`: `serve:table:launcher-flags-refused`, `serve:table:logging-families-refused`, an argparse replay with `allow_abbrev=True` proving no passing row resets a launcher flag; `tests/test_serve_image.py`: `serve:image:launcher-refuses-a-row`; `tests/test_up.py`: `session:one:waiting-refuses`, `session:one:stale-waiting-removed`, `session:stock:waiting-marked`; `tests/test_volume.py`: `volume:stock:waiting-marked`; `tests/test_state.py`: the mark's write and clear | none |
| end-to-end | none | none |

The suite stands at 598 tests, by `uv run pytest --collect-only -q` at the base. Changed, not removed:
`test_the_launcher_keeps_logging_and_telemetry_off`'s `SERVE_ARGS` drops `--enable-log-requests`; the
`--enable-log-requests=yes` case of `tests/test_serve_table.py`'s `serve:rows:logging-on-refused` test is now
refused. This change deletes and merges no test.

## Dependencies

None.

## Risks / Trade-offs

- **A legitimate flag that prefixes a launcher flag is refused**, `--tokenizer` among them → a tokenizer from another
  repository is unpinned anyway (T13); the refusal names the flag.
- **A short flag or a value opening with `-` is read as a flag**, `-tp 2` and `--seed -1` among them → the refusal
  names it; the long name, or `--seed=-1`, passes.
- **The image rebuild needs a person** → one HUMAN phase, its commands written; the run rents nothing.
- **A reused pid can make a stale mark look live** → the refusal names the pid, and `rm .gpunit/waiting` clears it.

## Verdict

**feasible.** Every file and symbol named exists at `ba0fced`. Cards and fixes only, so a patch (decision D8).
