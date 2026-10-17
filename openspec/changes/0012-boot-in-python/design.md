# Design — 0012 boot in Python

How `boot.sh` becomes `boot.py` with every step unit-tested, how the gate holds it, and how the serve image's command
and the live recipes leave shell. **Verdict: feasible** — each step of `boot.sh` has a stdlib equivalent, and the lines
gpunit reads are plain strings.

## Context

See [proposal](proposal.md) — *Why*. What holds at the cut, `main` at `ecda749` (`v0.7.1`):

- **`boot/boot.sh`:** the stop over `curl`, retried from 30 s to 300 s (`:21-39`); the checks of `sshd`, `curl`, `env`
  and the variables (`:41-51`); the ceiling armed in a sleeping subshell, then `trap stop EXIT` (`:53-61`); the nonce,
  checked once armed (`:63`); sshd on a fresh host key with boot's own config (`:65-90`); the key line (`:94`); the
  command through `env -u`, `SIGTERM` forwarded (`:96-110`); the 60 s grace (`:112`).
- **The contract gpunit reads:** `gpunit host key <nonce>: SHA256:…` (`fingerprint`, `gpunit/provider.py:32`),
  `<UTC> step: the command` (`_BOOT_STEP`, `:15`), and `<UTC> step: the ceiling, Ns` as boot's first line
  (`_BOOT_START`, `:17`). An older `boot.sh` is refused naming `v0.6.0` (`gpunit/lifecycle.py:403`).
- **`tests/test_boot.py`:** real bash against stub `curl`, `sleep`, `sshd` and `ssh-keygen` (`:24-80`); every test
  carries a `boot:*` key.
- **The images:** `serve/Dockerfile` installs `openssh-server curl` (`:6`), copies `boot.sh` (`:9`), and runs `sh -c`
  as its `CMD` (`:13`); `live/Dockerfile` installs `openssh-server curl ca-certificates` (`:8`); `live/Dockerfile.dead`
  drops `curl` (`:8`). Each copies `boot/boot.sh` and runs it as `ENTRYPOINT`.
- **The `Makefile`:** the gate (`:9-17`); the inline shell of `live-volume` (`:30`), `live-serve` (`:49`), `live-dead`
  (`:70`) and `live-serve-dead` (`:84`), to the file's end.
- **`pyproject.toml`:** `requires-python = ">=3.11"` (`:6`); the `dev` group (`:20-25`); no `[tool.ruff]` table, no
  `[tool.ty]` table, no coverage config.
- **`.gitignore`** names `.minions/`, `.gpunit/`, `.venv/`, `__pycache__/`, `.env`; not `.coverage`.

| measure | value | command |
|---|---|---|
| `boot.sh`'s lines | 113 | `wc -l boot/boot.sh` |
| `test_boot.py`'s test functions | 16 | `grep -c '^def test_' tests/test_boot.py` |
| ruff | 0.16.10 | `uv run ruff --version` |
| ty | 0.0.85 | `uv run ty --version` |
| the gate's Python | 3.12.14 | `uv run python --version` |
| `pytest-cov`'s latest release | 7.1.0 | `curl -s https://pypi.org/pypi/pytest-cov/json` |

**The 3.10 checks, probed at the cut** on a file holding `import tomllib`, `except*` and `datetime.UTC`, in a scratch
directory outside the repo:

| tool, setting | `except*` | `tomllib` | `datetime.UTC` |
|---|---|---|---|
| ruff, `per-file-target-version = { "boot/boot.py" = "py310" }` | caught | passed | passed |
| `ty check` at the project's `requires-python` | passed | passed | passed |
| `ty check --python-version 3.10 boot/boot.py` | caught | caught | caught |
| `[[tool.ty.overrides]]` with an `environment` key | refused: `unknown field environment, expected one of include, exclude, rules, analysis` |

## Goals / Non-Goals

**Goals:** every step of boot tested alone; the whole still proven by running it; the stop guarantee unchanged;
no shell left in what the images run or the live recipes hold.

**Non-Goals:** a new log line; a change on the laptop's side; a Python 3.10 interpreter in the gate.

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| [D1](#d1) | `boot/boot.py`: one function a step, `main(argv) -> int` | each step tested alone | a class; a package |
| [D2](#d2) | Python 3.10, stdlib only, no gpunit import; `ENTRYPOINT ["python3", "/opt/gpunit/boot.py", "--"]` | Ubuntu 22.04 ships 3.10; a consumer `ADD`s one file | 3.11, gpunit's own floor |
| [D3](#d3) | the ceiling in a forked watchdog; the main flow in `try … finally: stop()`; `SIGTERM` forwarded | a separate process outlives a crash in the main one, as bash's subshell does | a thread; `signal.alarm` |
| [D4](#d4) | the stop over `urllib`, the key in a header; the command's environment built in Python | `curl` and `env` drop out; the key never on an argv | keeping `curl` |
| [D5](#d5) | `tests/test_boot_steps.py` imports `boot.py` and binds every `boot:*` key on fakes | the steps alone, and the 100 % gate | one file for both kinds |
| [D6](#d6) | `tests/test_boot.py` runs `boot.py` against stub `sshd` and `ssh-keygen`, and a `sitecustomize.py` for the stop and the waits | the whole proven, no test knob in `boot.py` | an API URL from the environment |
| [D7](#d7) | `pytest-cov`; `uv run pytest --cov` at 100 % line and branch on `boot/`; ruff's per-file target and `ty --python-version 3.10` hold 3.10 | the probe: ruff alone misses the stdlib | `pragma: no cover`; a 3.10 interpreter |
| [D8](#d8) | `boot/boot.sh` deleted once `boot.py` is proven, and every `COPY` and `ENTRYPOINT` repointed with it | no two boots to keep in step; nothing names a missing file | keeping both |
| [D9](#d9) | `serve/launch.py` sets `HF_HOME` on a volume and `exec`s vLLM | the shell that broke once | a fixed `sh -c` |
| [D10](#d10) | `live/volume.py`, `live/serve.py`, `live/dead.py`; `live/serve_dead.py` gains its window; `live/window.py` holds the window's teardown | the logic tested offline, as `serve_dead.py`'s `check` | logic left in the `Makefile` |
| [D11](#d11) | `0011·R4` closes won't-fix | it names archived text | editing the archive |
| [D12](#d12) | `gpunit-vllm`, `gpunit-live` and `gpunit-live-dead` rebuilt and re-pinned | every entrypoint changes | — |
| [D13](#d13) | `make live`, `make live-dead`, `make live-volume`, `make live-serve` on the new images | the boot runs on a real pod | the serve-dead run again |
| [D14](#d14) | README's step 2, `CLAUDE.md`, the boot spec's Purpose | the consumers read them | — |

### D1

`boot/boot.py`, as `boot.sh` runs it:

```
main(argv)
  check(environ, argv)            refuse → exit 1, nothing armed, no stop
  say "step: the ceiling, Ns"     boot's first line, as now
  arm(ceiling_s)                  fork the watchdog: sleep(ceiling) → say "reached" → stop() → _exit
  try:
    the nonce                     refuse → exit 1
    sshd(home, public_key)        "step: sshd"; refuse → exit 1
    the key line                  stdout: gpunit host key <nonce>: SHA256:…
    code = run(command, environ)  "step: the command" … "the command exited <code>"
    sleep(GRACE_S)                only after the command's end
  finally:
    stop()                        every way out of the try
  return code
```

- **Names and values kept:** `API`, `RETRY_S = 30`, `MAX_RETRY_S = 300`, `GRACE_S = 60`; every message of `boot.sh`,
  word for word, but `use boot.sh -- <command>` → `use boot.py -- <command>`, and a stop with no answer names its
  cause, `HTTP 000 (<cause>)` ([D4](#d4)). Two lines are new: `the command could not start: <error>` and the
  watchdog's `the ceiling's stop failed; delete the pod by hand` ([D3](#d3)). `say` writes
  `<UTC as %Y-%m-%dT%H:%M:%SZ> <text>` to stderr.
- **Every line is flushed when written**, stdout and stderr, as bash's `echo` is: gpunit reads the key line before
  `step: the command`, and a buffered line would reach the log late. Stdout and stderr are flushed before the fork.
- **`KEY_GAP_S = 1`:** boot sleeps 1 s after the key line, before `step: the command`. Stdout and stderr reach
  RunPod's log on separate pipes, and two lines written microseconds apart can merge swapped; gpunit then never
  accepts the key. Found by `make live-volume` in phase 7: the log read `step: the command`, then the key line.
  `boot.sh`'s `$(date …)` in `say` put milliseconds between them.
- **`sshd`** keeps `boot.sh`'s order and config text: `~/.ssh` at `0700`, `authorized_keys` written under umask `077`
  then `0600`, `/run/sshd` made with errors ignored, a `tempfile.mkdtemp` directory, `ssh-keygen -q -t ed25519 -N ''
  -f <dir>/ssh_host_ed25519_key`, the same `sshd_config`, `sshd` by its absolute path from `shutil.which`.
- **The fingerprint** is the second field of `ssh-keygen -lf <key>.pub`.
- **`main`** runs under `if __name__ == "__main__": sys.exit(main(sys.argv[1:]))`; a leading `--` is dropped once.

### D2

- **3.10:** Ubuntu 22.04, the base of `gpunit-live` and isekai's image, ships Python 3.10.
- **Stdlib only, no gpunit import, one file:** a consumer's Dockerfile `ADD`s `boot.py` alone, by its tag URL.
- **The entrypoint:** `ENTRYPOINT ["python3", "/opt/gpunit/boot.py", "--"]`. The file needs no `chmod`.
- **`boot:file:stdlib-only`:** a test parses `boot.py`'s `import` and `from … import` nodes with `ast` and checks each
  top-level name is in `sys.stdlib_module_names`, and none is `gpunit`.

### D3

- **The watchdog:** `arm` calls `os.fork()`; the child sleeps `GPUNIT_CEILING`, says `the ceiling of Ns is reached`,
  runs `stop()` and leaves by `os._exit(0)`, so it never reaches the parent's `finally`. An error in that stop is
  caught by `except BaseException`: the child says `the ceiling's stop failed; delete the pod by hand`, prints the
  traceback and leaves by `os._exit(1)`. The parent returns at once.
- **The `finally`:** a refusal raised after the arm, an error of boot's own, and the command's end each reach
  `stop()`. Only the command's end sleeps `GRACE_S` first.
- **`SIGTERM`:** once the command starts, a handler sends `SIGTERM` to it; `Popen.wait` resumes after the handler
  (PEP 475), so boot waits for the command's own end, as `boot.sh`'s loop does.
- **The code:** the command's own; a command a signal ended gives `128 + n`, as bash reports it. A command that cannot
  start (`OSError` from `Popen`) says `the command could not start: <error>` and gives `127`, as `env` does; the grace
  and the stop follow.
- **An error of boot's own** (`boot:stop:own-error`) propagates after the `finally`'s stop; Python exits `1` with the
  traceback on stderr.

### D4

- **The image needs** `python3` ≥ 3.10, `openssh-server` (it brings `ssh-keygen`) and `ca-certificates` (for the
  stop's TLS). `check` no longer looks for `curl` or `env`.
- **The stop:** an opener built with `_NoRedirect`, which follows no 3xx, sends a `POST` to
  `{API}/pods/{RUNPOD_POD_ID}/action`, body `{"action":"stop"}`, headers `Authorization: Bearer <key>` and
  `Content-Type: application/json`, timeout 30 s. A `200` stops; an `HTTPError`, a 3xx among them, gives its code; any
  other `OSError` or `http.client.HTTPException` gives `000 (<cause>)`, `curl -w '%{http_code}'`'s `000` with the
  error's reason. The backoff is `boot.sh`'s, and so are the messages, but for that cause.
- **The command's environment:** a copy of `os.environ` without `RUNPOD_API_KEY` and `GPUNIT_NONCE`, passed to
  `subprocess.Popen`.

### D5

`tests/test_boot_steps.py` imports `from boot import boot` (`boot/` as a namespace package, on pytest's
`pythonpath = ["."]`) and replaces, with `monkeypatch`, what reaches outside the process: `os.fork`, `os._exit`,
`time.sleep`, `urllib.request.build_opener`, `subprocess.run`, `subprocess.Popen`, `shutil.which`, `signal.signal`, and
the home directory. Each test binds a `boot:*` key; together they bind every key of
[the boot delta](specs/boot/spec.md) and of `openspec/specs/boot/spec.md`. The `__main__` guard is covered by
`runpy.run_path` on a call that refuses before the arm.

### D6

`tests/test_boot.py` keeps the shape of today's tests and their keys, and runs `[sys.executable, "boot/boot.py",
"--", …]`:

- **Stub `sshd` and `ssh-keygen`** on `PATH`, today's scripts unchanged.
- **A `sitecustomize.py`** written into the test's directory and put first on `PYTHONPATH`: it replaces
  `urllib.request.build_opener` with a recorder that logs `header-ok` or `no-header`, the URL and the body, and answers from
  `$STOP_CODES`; and `time.sleep` with a logger that returns at once, but holds the ceiling's own wait when
  `HOLD_CEILING` is set — today's `curl` and `sleep` stubs, moved into Python. `boot.py` holds no test knob.
- **`boot:needs:no-curl` and `boot:needs:no-env`** — in place of `boot:refuse:no-curl` and `boot:refuse:no-env`, whose
  names a refusal no longer fits — run boot on a `PATH` holding only the stubs, the command by its
  absolute path, and assert the command ran, the stop carried the key in its header, and the command's environment
  held neither `RUNPOD_API_KEY` nor `GPUNIT_NONCE`.
- **`test_the_commands_end_stops_the_pod`** keeps its name: `CLAUDE.md`'s *key never on argv* invariant cites it.

### D7

- **`pyproject.toml`:** `"pytest-cov>=7.1,<8"` in the `dev` group;
  `[tool.ruff] per-file-target-version = { "boot/boot.py" = "py310" }`;
  `[tool.coverage.run] source = ["boot"]`, `branch = true`; `[tool.coverage.report] fail_under = 100`,
  `show_missing = true`. No `exclude_also`, no `pragma: no cover`.
- **The gate recipe**, `Makefile:9-17`: `uv run pytest` → `uv run pytest --cov`; after `uv run ty check`, a new line
  `uv run ty check --python-version 3.10 boot/boot.py`. The config holds the parameters; the commands stay bare but
  for `--python-version`.
- **`.gitignore`** gains `.coverage`, so a gate run leaves the tree clean.
- **Why both tools:** per the probe in *Context*, ruff's per-file target catches 3.11 syntax but not a 3.11 stdlib
  name, and ty has no per-file Python version; its command-line flag catches both.
- **Coverage counts the unit tests alone:** the end-to-end tests run `boot.py` in a child process, which coverage does
  not follow.

### D8

- **Order:** phase 1 proves `boot.py` by its unit tests; phase 2 ports the end-to-end tests to it, repoints the
  Dockerfiles, and deletes `boot/boot.sh` last.
- **The Dockerfiles**, `serve/Dockerfile`, `live/Dockerfile` and `live/Dockerfile.dead`:
  `COPY boot/boot.sh /opt/gpunit/boot.sh` → `COPY boot/boot.py /opt/gpunit/boot.py`; the `ENTRYPOINT` → [D2](#d2)'s;
  `RUN chmod +x` goes; the install lines → [D4](#d4)'s and [D12](#d12)'s; each comment naming `boot.sh` or `curl`
  follows. `serve/Dockerfile`'s `CMD` waits for [D9](#d9).
- **Consumers** keep `boot.sh` at `v0.7.0` by its tag URL; the file at that tag stays reachable whatever the tree
  holds.
- **The laptop is unchanged:** `old_boot` and its message naming `boot.sh` from `v0.6.0` stay; they speak of a file at
  a tag.

### D9

`serve/launch.py`, stdlib only, run by the serve image as `CMD ["python3", "/opt/gpunit/launch.py"]` after
`COPY serve/launch.py /opt/gpunit/launch.py`:

```
GPUNIT_VOLUME_PATH set and non-empty → HF_HOME = <it>/huggingface
os.execvp("vllm", ["vllm", "serve", SERVE_REPO, "--revision", SERVE_REVISION,
                   "--served-model-name", SERVE_NAME, "--host", "127.0.0.1", "--port", "8000",
                   *SERVE_ARGS.split()])
```

`SERVE_ARGS.split()` undoes `" ".join(self.args)` (`gpunit/serve/table.py:69`), as `sh`'s field splitting did,
without its globbing.
`tests/test_serve_image.py` runs the `CMD`'s script from the repo, `serve/launch.py`, under the test's Python with a
stub `vllm`; the `${…:+…}` twin becomes an empty `GPUNIT_VOLUME_PATH`, which leaves `HF_HOME` unset.

### D10

A script per target, named for it: `live-volume` → `live/volume.py`, `live-serve` → `live/serve.py`, `live-dead` →
`live/dead.py`, `live-serve-dead` → `live/serve_dead.py`. Each recipe becomes one line:
`uv run python live/<script>.py`, `live/serve.py` taking `$(MODEL)`. `make live` keeps its plain lines.

```
volume.py      price → volume up → run (write) → run (read) → check(wrote, read) → status   window
serve.py       serve --api ─ OPENAI_BASE_URL, OPENAI_API_KEY ─ a chat request ─ tool_call.py ─ SIGTERM   window
               → volume up again → a chat of one prompt
dead.py        price → up → "up exited <code> after <s>s", "reason: <line>" → status → check(code, lines)
serve_dead.py  today's main                                                                 window
```

- **The commands are the recipes'**, each `uv run gpunit …` as `[sys.executable, "-m", "gpunit", …]` through
  `subprocess`, and `live/price.py` as `[sys.executable, "live/price.py", <spec>]`.
- **`live/window.py`:** `window(up, down, body, run) -> int` runs `up`, then `body`, then `down` in a `finally`; a
  failed `down` makes the result `1`; an exception in `body` still reaches `down`. It is the recipes' `trap`.
- **`serve.py`'s chat request** goes over `urllib`, the key in a header, as `tool_call.py`'s does.
- **Offline, in `tests/test_live.py`:** `volume.check` under `session:volume:window-mounted`, `dead.check` under
  `session:wait:dead-pod-tears-down`, `serve.py`'s reading of the `OPENAI_BASE_URL` and `OPENAI_API_KEY` lines under `serve:api:prints-the-endpoint`,
  and `window` with a fake `run` under `volume:down:deletes`: a body that fails, one that raises, and a failed `down`.

### D11

`0011·R4` asks to edit task 2.2's `Verify:` in `openspec/changes/archive/0011-paydown/tasks.md`. An archived change
records what was checked then (`0008·R5`).

- **It closes won't-fix**, listed in the proposal's `backlog:`.
- **No task edits the archive.**

### D12

- **`gpunit-vllm`:** `.github/workflows/build-serve-image.yml` with the tag `v0.8-rc1`, rebuilt as `v0.8-rc2`
  after `4ee00fd`'s key pause, and as `v0.8-rc3` at `fa98cdf` after `3209e68` and `fa98cdf` changed `boot.py`'s
  stop, the shipped build; its digest replaces the old at `gpunit/serve/models.toml:2`. `gpunit-live` and
  `gpunit-live-dead` are rebuilt with it, at the same tags.
- **`gpunit-vllm`'s install line:** `openssh-server curl` → `openssh-server ca-certificates`.
- **`gpunit-live`:** `live/Dockerfile` installs `openssh-server python3 ca-certificates`, no `curl`: `python3`, not
  `python3-minimal`, whose module set lacks `http.client`, `json` and `shutil` (settled at the cut).
- **`gpunit-live-dead`:** `live/Dockerfile.dead` is `live/Dockerfile` without `python3`, so the entrypoint
  cannot start and the container exits at once. Its header comment says so.
- **Built by hand** with `docker buildx build --platform linux/amd64 --push` from the repository root; the digests
  replace the old at `live/gpunit.toml:4`, `live/gpunit.volume.toml:4` and `live/gpunit.dead.toml:4`.

### D13

With `RUNPOD_API_KEY` set, the human runs `make live`, `make live-dead`, `make live-volume` and `make live-serve`, and
appends each tail under a header `<date> — make <target>, 0012-boot-in-python`: `make live`'s, `make live-dead`'s and `make live-volume`'s to
`live/last_run.txt`, `make live-serve`'s to `live/serve_last_run.txt`. About $0.40 in all.

- **They ran on the `v0.8-rc2` images, at `01ba5d9`.** The `v0.8-rc3` rebuild changed only `boot.py`'s stop and its
  log lines, held offline at 100 % coverage, so the human chose not to re-run them.

### D14

- **README:** step 2 becomes *Make `boot.py` the image's entrypoint*: it needs `python3` 3.10 or newer with its standard library,
  `openssh-server` and `ca-certificates`; the `ADD` line reads
  `https://raw.githubusercontent.com/alxb1t/gpunit/v0.8.0/boot/boot.py /opt/gpunit/boot.py`; the `ENTRYPOINT` is [D2](#d2)'s;
  the `chmod` line goes; one sentence says `boot.sh` at `v0.7.0` still works. Every other `boot.sh` in the README's
  present tense becomes `boot.py`; the line naming `v0.6.0` stays.
- **`CLAUDE.md`:** the opening line and the layout name `boot/boot.py`, `serve/launch.py` and `live/*.py`; the
  invariant *the key never on argv* says `boot.py` sends it in a request header; the tests line names `tests/test_boot_steps.py` and
  `tests/test_boot.py` for `boot.py`; the gate's paragraph says it holds `boot/boot.py` at 100 % line and branch coverage.
- **The boot spec's Purpose:** "one shell file" → "one Python file", edited in `openspec/specs/boot/spec.md`, as
  OpenSpec's instructions say for a Purpose.

## Dependencies

- **`pytest-cov>=7.1,<8`** — a dev dependency in `pyproject.toml`'s `[dependency-groups] dev`, approved in the
  grilling. It measures `boot/boot.py`'s line and branch coverage for the gate ([D7](#d7)). It brings `coverage`, which
  `uv.lock` records.

## Risks / Trade-offs

- **A consumer installs `python3-minimal`** → Ubuntu 22.04's `libpython3.10-minimal` lacks `http/client.py`, `json/`
  and `shutil.py` (packages.ubuntu.com, jammy, read 2026-10-17), so `boot.py` cannot import `urllib.request`; README
  asks for `python3` with its standard library, and `gpunit-live` installs `python3` ([D12](#d12)).
- **No 3.10 interpreter in the gate** → ruff and ty hold the syntax and the stdlib's names; a behaviour that differs
  between 3.10 and 3.12 at run time shows only on a pod.
- **A unit test fakes what it tests against** → the end-to-end tests run the real file against stubs, and the live
  runs on a real pod.
- **A buffered line reaches the log late** → every line is flushed when written ([D1](#d1)).
- **A consumer on `boot.sh` sees no fix made after `v0.7.0`** → none is planned; README names both.

## Migration Plan

Consumers move when they choose: `ADD` `boot.py` at `v0.8.0`, install `python3`, and use [D2](#d2)'s `ENTRYPOINT`. Rollback
is `boot.sh` at `v0.7.0`, whose lines gpunit still reads.

## Verdict

Feasible: every step of `boot.sh` maps to the stdlib; the stop guarantee keeps its shape, a process for the ceiling and
a `finally` for every other end; the version checks were probed at the cut. An image needs `python3` with
its standard library, not `python3-minimal`.
