# Design — 0017 mf readiness

The tests made sandbox-safe, the root documents MinionsFactory reads, and a protected `main`, each as an unattended run
needs it. **Verdict: feasible.**

## Context

`mf-ship` builds each phase in a fresh worktree, and its worker runs `make gate` inside an OS sandbox. That sandbox
refuses every bind on loopback, and sends `urllib` through its own proxy. A worker reached the gate at `55fdae3`:

| what failed | where | count |
|---|---|---|
| `_free_port`'s bind on `127.0.0.1` | `tests/test_serve_session.py`, `tests/test_cli.py` | 34 |
| a loopback server: the `free_port` fixture or `ModelServer` | `tests/test_library.py`, `tests/test_run.py`, `tests/test_serve_chat.py`, `tests/test_tool_call.py` | 31 |
| a redirect test, through the proxy | `tests/test_boot_steps.py`, `tests/test_runpod.py` | 2 |

The counts are the worker's report, `.minions/runs/agent-20261103-120649.log`. `boot/`'s coverage fell to 99 %, with
the redirect test of `tests/test_boot_steps.py`.

MinionsFactory's review reads `THREAT_MODEL.md`, `ARCHITECTURE.md`, `CODING_STANDARDS.md` and `CONTRIBUTING.md` at the
root, by name. `AGENTS.md` came from `CLAUDE.md` by hand at `55fdae3`; `CLAUDE.md` is a link to it. `AGENTS.md` gained
`Worktrees:` and `Workspace setup:` at `841ec7b`.

## Goals / Non-Goals

**Goals:** `make gate` passes under a sandboxed worker; every test still runs, in `make gate` or `make e2e`, and CI runs
both. Review finds the root documents. `main` refuses a force-push and a deletion.

**Non-Goals:** any behaviour of gpunit; a new `Ship network:` or `Ship tools:` line; reading the docs again for style.

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| <a id="d1"></a>**D1** | An autouse fixture `fixed_port` in `tests/conftest.py` sets `gpunit.serve.session._free_port` to return `18000`, `gpunit.library._taken` to return `None` and `gpunit.library._binds_v6_loopback` to return `True`, except for a test marked `e2e` | the tests that reach it prove serve's flow, not the probe | marking all of `tests/test_serve_session.py` `e2e`: serve's suite would leave the gate |
| <a id="d2"></a>**D2** | A test whose proof is a real loopback socket carries `@pytest.mark.e2e`. `make gate` runs `pytest --cov -m "not e2e"`; `make e2e` runs `pytest -m e2e`. The marked tests are listed in [The tests moved](#the-tests-moved) | a worker may not bind loopback (MinionsFactory `0056-loopback-removal`), and the tunnel and the stream are proved by a real socket alone | faking the stream at `urllib`: the tests would no longer prove it |
| <a id="d3"></a>**D3** | A fixture `no_proxy` in `tests/conftest.py` deletes `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `http_proxy`, `https_proxy` and `all_proxy`; `test_a_redirect_is_not_followed` and `test_a_redirect_is_a_failed_stop_never_followed` use it. gpunit itself keeps honouring a proxy | `urllib`'s opener reads them, so the sandbox's proxy took the faked request | ignoring proxies in gpunit: a user's proxy is legitimate |
| <a id="d4"></a>**D4** | `.github/workflows/gate.yml` runs `make e2e` in a step after `make gate`; `tests/test_ci.py` holds it | every test still runs on every push | a second workflow |
| <a id="d5"></a>**D5** | D54 in `docs/decisions.md`, per [D54's text](#d54s-text) | the rule review reads | |
| <a id="d6"></a>**D6** | `git mv docs/threat-model.md THREAT_MODEL.md`; its links re-pointed into `docs/`; it gains [the worker](#the-threat-models-additions). D9 in `docs/decisions.md` is rewritten per [D9's text](#d9s-text) | MinionsFactory reads the root file by name | a copy in each place |
| <a id="d7"></a>**D7** | `git mv docs/README.md ARCHITECTURE.md`; its title `# The guide to gpunit` → `# gpunit — architecture`; its links re-pointed into `docs/` and to `THREAT_MODEL.md` | the guide's front page is the architecture | a new page beside `docs/README.md` |
| <a id="d8"></a>**D8** | `CODING_STANDARDS.md` and `CONTRIBUTING.md` per [The root documents](#the-root-documents). *How a change is cut here* and *The rules for a change* move from `AGENTS.md` into `CONTRIBUTING.md`; `docs/extending.md`'s `## The rules` becomes one line linking there | one copy of each rule | copies beside `AGENTS.md` |
| <a id="d9"></a>**D9** | `AGENTS.md` per [The root documents](#the-root-documents). `tests/test_docs.py`'s `guide` and `SCANNED_FILES` take `AGENTS.md`, `ARCHITECTURE.md`, `THREAT_MODEL.md`, `CODING_STANDARDS.md` and `CONTRIBUTING.md` in place of `CLAUDE.md`; `tests/test_ci.py` reads the OpenSpec version from `CONTRIBUTING.md`. The `CLAUDE.md` link stays | the links test holds every page review reads; one file is read once | dropping the link: Claude Code reads `CLAUDE.md` |
| <a id="d10"></a>**D10** | A ruleset `protect main` on `~DEFAULT_BRANCH`: `deletion`, `non_fast_forward`. Secret scanning and push protection are on already, read at the cut by `gh api repos/alxb1t/gpunit --jq .security_and_analysis`. The version branch pushed, so CI runs `make gate` and `make e2e`. By a person, last | a release pushes to `main`; `.env` sits in a worker's reach (Q5); a worker cannot reach GitHub | a pull-request rule |

## The tests moved

Each gets `@pytest.mark.e2e`. In `tests/test_tool_call.py`, each test that serves a `ModelServer` gets it; the
`serve:tools:key-from-the-environment` tests call `live/tool_call.py::main` on a faked `OPENER` and stay in the gate
(converge S2).

| file | tests |
|---|---|
| `tests/test_library.py` | `test_the_block_sees_the_session`, `test_a_dead_tunnel_is_reopened`, `test_a_taken_port_ends_the_block`, `test_a_port_taken_while_the_tunnel_waits_refuses`, `test_a_port_taken_while_the_pod_came_up_refuses`, `test_a_swallowed_refusal_leaves_the_signals_live`, `test_each_loopback_family_is_its_own_forward`, `test_a_host_without_v6_loopback_forwards_v4_alone`, `test_the_tunnels_connect_is_bounded` |
| `tests/test_run.py` | `test_the_environment_names_the_session`, `test_a_dead_tunnel_is_reopened`, `test_a_busy_port_refuses_before_any_request`, `test_a_port_busy_on_v6_loopback_refuses`, `test_a_taken_port_ends_the_run` |
| `tests/test_serve_chat.py` | `test_each_part_is_written_as_it_arrives_and_the_answer_is_kept`, `test_thinking_is_off_unless_asked_for`, `test_exit_or_the_end_of_input_ends_the_chat`, `test_streamed_text_is_cleaned_and_kept_as_streamed` |
| `tests/test_tool_call.py` | `test_a_tool_call_passes`, `test_plain_text_fails`, `test_unparseable_arguments_fail`, `test_a_call_to_another_function_fails` |
| `tests/test_serve_session.py` | `test_a_busy_local_port_is_skipped_before_the_price` |

`pyproject.toml` registers the mark beside `spec(key)`:
`"e2e: needs a real loopback socket; runs in make e2e, out of the gate (decision D54)",`. Its comment
`the end-to-end tests run it in a child process` → `the child-process tests run it`, so *end-to-end* names one thing.

The `Makefile`'s `pytest` line and the new target:

```diff
-	uv run pytest --cov
+	uv run pytest --cov -m "not e2e"
```

```make
# The loopback proof: the tests a sandboxed worker cannot run, since they bind a real
# socket (decision D54). Not part of the gate; CI runs it after the gate.
e2e:
	uv run pytest -m e2e
```

`e2e` joins `.PHONY`. `gate.yml` gains `      - run: make e2e` after `      - run: make gate`, and its step name
`Install the OpenSpec CLI at the version CLAUDE.md records` → `… CONTRIBUTING.md records`.

## D54's text

```markdown
### D54 · The gate runs inside a sandboxed worker

**`make gate` binds no loopback socket and reaches no host but the package index; a test whose proof is a real loopback
socket is marked `e2e` and runs in `make e2e`, which `.github/workflows/gate.yml` runs after the gate.**

- **Why:** MinionsFactory runs each phase's gate in an OS sandbox that refuses a loopback bind.
- **Made by:** `0017·D2`.
```

## D9's text

```markdown
### D9 · The threat model is `THREAT_MODEL.md` and moves with every trust-boundary change

**`THREAT_MODEL.md` is edited by the change that adds a flow, secret, file mode, network call or log line.**

The page is [the threat model](../THREAT_MODEL.md).

- **Why:** It is versioned with the code, so it is current when the code is; MinionsFactory's review reads it at the
  root.
- **Made by:** `0013·D14`, `0017·D6`.
```

Its links in `docs/extending.md` and `docs/principles.md` take the new anchor,
`decisions.md#d9--the-threat-model-is-threat_modelmd-and-moves-with-every-trust-boundary-change`.

## The threat model's additions

*§2 Actors and trust boundaries* gains a row after *the operator*:

```markdown
| a MinionsFactory worker in the checkout | trusted with the code, inside an OS sandbox | it reads the repo folder, `.env` with the account key (A1) among it; its network reaches the package index alone, and only a pushed commit leaves it ([G17](#5-gaps)) |
```

*§5 Gaps* gains a row:

```markdown
| G17 | `.env` holds the account key in the repo folder, where a worker reads it; a commit carrying it would be published by the release's push | design change (a guard in the conductor) | A1 | **accepted**: gpunit reads no `.env`, the file is gitignored, and GitHub's push protection is on; a guard is MinionsFactory's |
```

## The root documents

**`AGENTS.md`** — the title `# gpunit — shared context for Claude Code` → `# gpunit — shared context for coding agents`.
`**Read [docs/README.md](docs/README.md) first:** …` becomes:

```markdown
**Before work, read [the coding standards](CODING_STANDARDS.md) and [how a change lands](CONTRIBUTING.md): mandatory
shared context.** **Before designing, building or reviewing, also read [the architecture](ARCHITECTURE.md),
[the decisions in force](docs/decisions.md) and [the threat model](THREAT_MODEL.md).**
```

`## The quality gate — make gate` gains: `` `make e2e` runs the tests that need a real loopback socket, out of the gate
(decision D54). `` `## How a change is cut here` and `## The rules for a change` leave for `CONTRIBUTING.md`.
MinionsFactory's template's `## Tests` section follows `## The run's lines`, word for word. The guardrail
`**Never weaken the gate to pass.**` gains the template's line: `A test deleted or merged as the change's ## Tests
table names it is not a weakening.`

**`CODING_STANDARDS.md`** — MinionsFactory's template with `<name>` → `gpunit`. `## Project rules` reads:
`The rules the code follows, each with the test that holds it, are in [principles](docs/principles.md); a rule there
that names a C rule replaces it.`

**`CONTRIBUTING.md`** — MinionsFactory's template with `<name>` → `gpunit`, then:

- `## How a change lands` keeps the template's flow, and takes *How a change is cut here*'s text: the OpenSpec CLI
  `@fission-ai/openspec@1.11.0`, recorded and resolved on `PATH`; the version in `gpunit/version.py`.
- `## The rules for a change`, new, holds `AGENTS.md`'s list word for word, but `docs/threat-model.md` →
  `THREAT_MODEL.md`.
- `## The evidence a change carries` is the template's.

## Tests

| layer | adds | removes |
|---|---|---|
| unit | none — `fixed_port` and `no_proxy` are fixtures | none |
| end-to-end | none new; the tests in [The tests moved](#the-tests-moved) run in `make e2e` | none |

The suite stands at 567 tests, by `uv run pytest --collect-only -q` at the base. `make gate` keeps 539 and `make e2e`
runs 28: `tests/test_library.py` 9, `tests/test_run.py` 5, `tests/test_serve_chat.py` 8, `tests/test_tool_call.py` 5
and `tests/test_serve_session.py` 1, each by `uv run pytest --collect-only -q <file> -k <names>`. This change deletes
and merges no test.

## Dependencies

None.

## Risks / Trade-offs

- **A test faked past its bind may meet the sandbox next** (a connect, the proxy) → phase 1's HALT CHECK runs the
  faked files under the build's own worker before anything else moves.
- **The gate no longer proves the tunnel and the stream on the laptop** → CI runs `make e2e` on every push, and the
  operator runs it by hand.
- **The proxy is unconfirmed as the redirect tests' cause** → a HALT CHECK runs both with the variables unset first.
- **The ruleset blocks a force-push the operator might want** → it is reversible in GitHub's settings.

## Verdict

**feasible.** Every file and test named exists at `841ec7b`, and no verb, `gpunit.toml` key, message or exit code moves,
so the change is a patch (decision D8).
