# Docs revisit — design

Reads the root documents and `docs/` against the code at the cut, fixes what is stale, gives each rule one home and rewrites the pages for a reader. Verdict: ready to build, in the phases of [tasks](tasks.md).

## Context

The seam ([provider](../../../gpunit/provider.py), [providers](../../../gpunit/providers.py)), the gone pod and readiness each moved code and left prose behind.
`tests/test_docs.py` holds every relative link and anchor, every `decision Dn`, no archived design citation and the front page's length. It holds backticked paths, `path::symbol` citations and line citations in `docs/*.md` alone, so the root documents drifted.

Code cites decisions as `decision Dn` and principles link them by title anchor. An id and a title are therefore frozen, and moving a section is free.

## Goals / Non-Goals

- **Goal:** each page is true of the code at the cut, says a rule once, and puts what a reader needs first.
- **Goal:** a test keeps the root documents' citations true after this version.
- **Non-Goal:** any behaviour, message, exit code or `gpunit.toml` key ([D2](#d2)); no decision added or overturned.
- **Non-Goal:** a live proof, a new page, or Vast.ai's F9, F10, F14 and `provider` key.

## Decisions

| id | decision | because | rejected |
|---|---|---|---|
| [D1](#d1) | Scope: the root documents and `docs/`, prose; besides, `pod_gone`'s comment cites D57, and the architecture spec's stale scenario title is fixed — wording only | the version is the docs; both exceptions say a thing wrongly and change no behaviour | — |
| [D2](#d2) | A patch, `v0.12.4` | no verb, key or exit code (D8) | — |
| [D3](#d3) | Every stale claim in the facts fixed, each read again against the code at the cut | the version's first job | — |
| [D4](#d4) | `test_docs.py`'s path and `path::symbol` check reads the root documents as well as `docs/*.md` | what keeps "current with the code" true after this version; a test, which a patch may hold | — |
| [D5](#d5) | One home a rule, the others link it: the gone rule in D57, the change rules in `CONTRIBUTING.md`, the key's exposure once in `docs/usage.md` | duplicates drift, and these already have | — |
| [D6](#d6) | `docs/usage.md` stays one page, reordered: quickstart, the verbs and exit codes, serve, the window, the spend rules, security last as links into `THREAT_MODEL.md` | a consumer needs the contract first; one page keeps the README's link and its test | — |
| [D7](#d7) | `docs/decisions.md` keeps every id and title; D55–D57 move out of "The guide" to their sections; D57 points to D55 rather than restating it; the D7 and D8 headings say what their bodies say, with every anchor to them | code and anchors cite ids and titles; the links test catches a missed anchor | — |
| [D8](#d8) | `THREAT_MODEL.md` drops its version stamps for "holds at the commit it is read at"; a row is the threat, its mitigation, its status and its citations, its residual analysis in its decision; §5 keeps the open gaps, a closed one a line | a stamp goes stale each release; a T9-sized cell cannot be read | — |
| [D9](#d9) | The install pin lives in `docs/usage.md` alone; `README.md` links it and `THREAT_MODEL.md` drops it | one place to bump at a release, not three nothing checks | — |
| [D10](#d10) | `CODING_STANDARDS.md` keeps its pointer to mf-build's rules and gains a short paragraph of gpunit's own: stdlib only, `boot/boot.py` on Python 3.10 at full coverage, names not counts | a reader outside MF has no baseline | — |
| [D11](#d11) | `CONTRIBUTING.md` gains a human's path — `make gate`, `make e2e`, a pull request under `main`'s ruleset — and tells the pipeline (integrate, simplify) and the `Change:` trailer truly | it describes the MF line only, and two of its claims are false | — |
| [D12](#d12) | No live proof re-run here; `docs/proofs.md` keeps its last runs; a live re-proof goes on the roadmap before v1.0, where `0020·S1` and the live images' `boot.py` are checked | a re-proof is metered and a person's, not a docs change | — |
| [D13](#d13) | `README.md`: "Built so" becomes a plain heading, a rule a row and at most one link a row; a `gpunit.session()` example and a line on `serve`; within the 60-line test | the front page hides two of its three uses | — |
| [D14](#d14) | `AGENTS.md` drops its repeated lines, moves the test-placement policy to `CONTRIBUTING.md`, keeps `Worktrees:` and `Workspace setup:` for the conductor, and says how to run one test and the `e2e` mark | what is true of the repo for an agent, once | — |
| [D15](#d15) | `ARCHITECTURE.md` redraws its diagram with the seam — `providers.build`, `Provider`, `runpod`, `hostkey` — says what each layer holds, and gives "the guide" back to `docs/` | the seam is now the core fact and the page lacks it | — |
| [D16](#d16) | `docs/principles.md`'s "the seam names no provider noun" is reworded to claim what its holder checks; no test added | the true parts are held already; the noun rule cannot be held well by a test | — |
| [D17](#d17) | Three phases: currency (Q1, Q3, Q4) first, so the test holds the rewrites; one home (Q5, Q7, Q8, Q9); the readers' pages (Q6, Q10, Q11, Q13–Q15) | the test first, then the facts' homes, then the pages that link them | — |
| [D18](#d18) | Build on Opus 5.5 high; cut Sonnet 5.5 high; release and fix Sonnet 5.5 medium; converge kept, its checkers Codex `gpt-6.1-sol` high; `decide: recommended` | "read well" is a writing job; the version's claim is currency, which a checker reads against the code, and a hand read would stall the run | — |

The brief numbers its decisions `Q1`…`Q18`; `D<n>` here is `Q<n>`. D16 is held by phase 1 beside the other stale claims, as the brief's phase list leaves it out.

### D1

The one code line changes in a comment, in `gpunit/lifecycle.py`'s `pod_gone`:

```
before:  # A wrong key gets a 404 too, but fails the listing: decision D55.
after:   # A wrong key gets a 404 too, but fails the listing: decision D57.
```

The same line in `gone`, the volume's check, stays D55.

The architecture spec's scenario `architecture:layers:provider-built` is retitled in this change's delta, "the RunPod module is imported by `providers` alone". The delta folds into the spec at the release. Its key and steps do not move, so no test does.

`openspec validate --strict` refuses a MODIFIED requirement that drops a scenario title. So the delta renames the requirement: ADDED under *The modules import down the layers, and RunPod only through providers*, REMOVED under the old title. Nothing else cites that title.

### D2

A patch, per [D8 of the decisions](../../../docs/decisions.md). The acceptance check is `git diff --stat main -- gpunit boot serve live`, which lists `gpunit/lifecycle.py` alone.

### D3

Each row is read again against the code at the cut; the code is right and the prose moves.

| claim | page | after |
|---|---|---|
| a diagram with no `Provider` and no `providers.build` | `ARCHITECTURE.md` | redrawn per [D15](#d15), in phase 1 |
| `TeardownFailed` exits `1` | `docs/usage.md` | `1`, or `3` when its `__cause__` is `Lost`; the exit table's `1` row agrees |
| RunPod's HTTP codes, and no `.gpunit/lock` | `docs/data-flow.md` | outcomes of the seam (`Unplaceable`, `Deleted.kind`), and a `lock` bullet |
| `_command` drops `RUNPOD_API_KEY`; stamps; no `providers`; archive list stops early | `THREAT_MODEL.md` | `_command` drops `provider.key_names`; `providers` listed; the archive list reaches the changes its rows cite; stamps go in [D8](#d8) |
| the decisions D2, D23 and D33 predate `providers.build`, `Deleted(kind, code)` and `key_names` | `docs/decisions.md` | D2 names `providers.build`; D23 names `kind` and `code`; D33 names `Provider.key_names` |
| "the seam names no provider noun" | `docs/principles.md` | per [D16](#d16) |
| the provider recipe names F14 only | `docs/extending.md` | also the price prompt and card filter (F9, F10), no `provider` key yet, and `Provider.stop` called by nothing |
| three layer rules; `runpod` only "REST v2" | `docs/modules.md` | a fourth rule, `providers` alone imports `runpod` (`tests/test_layers.py::BUILDERS`); `runpod` is the one `Provider` implementation |
| every commit but the bootstrap carries `Change:`; the pipeline omits integrate and simplify | `CONTRIBUTING.md` | the trailer is on each commit of a change, not on the bootstrap, the merge commits of the first line or the chores that set the repo files up; the pipeline names integrate, and simplify closes build |
| `pod_gone` cites D55 | `gpunit/lifecycle.py` | [D1](#d1) |
| remove `.gpunit/waiting` after a crash | `docs/usage.md` | a dead process's mark is removed by the next `up` or `volume up`; only a refusal naming a pid that no longer waits asks for the file's removal (`gpunit/lifecycle.py::refuse_waiting`) |
| `make live-serve granite-4.0-micro` | `docs/proofs.md` | `make live-serve MODEL=granite-4.0-micro` |

### D4

- `tests/test_docs.py::unresolved` walks `guide(root)`, the `docs/*.md` pages and the root documents, and skips a page that does not exist.
- `test_a_missing_symbol_or_a_line_citation_is_caught` gains a `README.md` in its tree, holding a missing symbol, and the expected faults gain its line. That is one step in an existing test, no new test ([T2](../../../CODING_STANDARDS.md)).
- The real tree's test then names each root-document citation that does not resolve. Phase 1 fixes each by the code's current name, and drops none to pass.

### D5

| rule | home | the others |
|---|---|---|
| a pod or volume is gone only when its read and the account's listing both lack it | [D57](../../../docs/decisions.md) | link it: `docs/usage.md` *The spend rules*, `docs/data-flow.md`, `README.md`, `docs/principles.md`, `THREAT_MODEL.md` rows |
| the rules for a change | `CONTRIBUTING.md` *The rules for a change* | `docs/principles.md` drops its *The process* table for a link; `docs/extending.md` already links |
| the account key's exposure | `docs/usage.md` *The account key* | step 3 and *Accepted risks* link it |

A page that links a home keeps at most the clause its own sentence needs.

### D6

The page keeps its headings, so every anchor to it stands. The order after:

```
Use it from a project · Use it from Python          the quickstart
The verbs · The lines a caller reads                the contract, exit codes in it
Serve a model                                        its subsections go with it
Working window
What it cost · The spend rules
Security and privacy                                 last
```

The security section keeps its subsections *Where your data lands*, *Secrets*, *The account key* and *Accepted risks*, which other pages link. Each of its bullets is one line that ends in a link into [the threat model](../../../THREAT_MODEL.md). The key's exposure is said once, in *The account key* ([D5](#d5)).

### D7

The sections of `docs/decisions.md` after the move:

| moved decision | section |
|---|---|
| the volume's rule, D55 | *The window volume*, after D43 |
| the stock wait, D56 | *A session*, after D21 |
| the pod's rule, D57 | *A session*, after D23 |

D57 states the rule once. For a volume it links D55 and does not repeat D55's reason, and D55 links D57 for the pod. A decision's id never changes.

The headings of the archive rule and the patch rule change, and every anchor to them with them (`git grep` finds each):

| decision | new heading | new anchor |
|---|---|---|
| the archive rule, D7 | An archived change is a record; a finding against it is fixed in a new change | `d7--an-archived-change-is-a-record-a-finding-against-it-is-fixed-in-a-new-change` |
| the patch rule, D8 | A patch fixes what is there; it adds no verb, `gpunit.toml` key or exit code | `d8--a-patch-fixes-what-is-there-it-adds-no-verb-gpunittoml-key-or-exit-code` |

### D8

A row of *4. Threats* is the threat, its mitigation, its status and its citations.

- Residual analysis moves into the decision the row cites; a row that cites none sends it to a gap of §5.
- T9's goes to D31, T47's and T48's to D57 and D55, which hold most of it, T21's to D33, and T13's and T55's, the same unpinned draft model, to D34. T20's stays in G17.
- A value is named by its constant, never restated ([D50 of the decisions](../../../docs/decisions.md)).

The stamps `v0.11`, `v0.10` and each `closed in v0.N` go; the header says the model holds at the commit it is read at.
§5 keeps G4, G7 and G14 to G17 in full, the open gaps. Each closed gap is a short row with no version.

### D9

The pin is in `docs/usage.md`, at the boot.py URL and at the `uv add` line, both on one tag; a release bumps that page. `README.md` links *Use it from a project* in its place, and `THREAT_MODEL.md` T15 says "a release tag, mutable" and links the same step.

### D10

`CODING_STANDARDS.md` keeps its baseline pointer and its link to principles. It gains one paragraph of gpunit's own, in `## Project rules`:

- the package, `boot/boot.py` and `serve/launch.py` use the standard library alone;
- `boot/boot.py` runs on Python 3.10, and the gate holds it at full line and branch coverage;
- prose names the things it means and counts none.

### D11

`CONTRIBUTING.md` after:

```
How a change lands      the MF pipeline, integrate and simplify named, the Change: trailer told truly
By hand                 make gate · make e2e · a pull request under main's ruleset
The rules for a change  the home of the change rules (D5), with the test-placement policy from AGENTS.md
The evidence            what a change carries
```

The openspec pin `@fission-ai/openspec@1.11.0` stays, as `tests/test_ci.py` reads it.

### D12

No live run. `docs/proofs.md` keeps its runs and gets one fix, the `MODEL=` form. The roadmap entry, a re-proof before v1.0 that checks `0020·S1` and the live images' `boot/boot.py`, is the person's and lives outside this repo; the cut notes it.

### D13

`README.md` after: title, badges, tagline, diagram, *Why*, *What holds* for the claims table, *Try it*, a `gpunit.session()` example, a line on `serve`, *Read more*.

- The claims table has a rule a row and at most one decision link a row; the gone rule is claimed once, linking D57.
- The install pin is replaced by a link, and `[the guide](ARCHITECTURE.md)` reads `[architecture](ARCHITECTURE.md)`.
- The page stays within the 60-line test.

```python
import gpunit

with gpunit.session("gpunit.toml") as s:
    print(s.host, s.port(8188))
```

### D14

`AGENTS.md` keeps: the mandatory-context line, the gate, the `Worktrees:` and `Workspace setup:` lines exactly, where things live, the guardrails. It loses *What holds* (its links are in the first line) and *Tests*, which `CONTRIBUTING.md` takes. It gains how to run one test, `uv run pytest tests/test_docs.py::test_the_front_page_fits_one_screen`, and that `make gate` skips the `e2e` mark, which `make e2e` runs.

### D15

The diagram draws, in place of `RunPod REST v2` under `lifecycle · volume · spend`: `Provider` (the seam), `providers.build` choosing it, `runpod` implementing it and calling RunPod's REST v2, and `hostkey` beside `lifecycle`.
Below it, a table `layer | holds` for the layers in the diagram's order. The map's `modules` row says "where RunPod is built" and stays.

"The guide" names `docs/` alone: any link text that called `ARCHITECTURE.md` the guide calls it architecture.

### D16

In `docs/principles.md` *The code*, the row "The seam names no provider noun" is replaced by "Only `providers` imports `runpod`", from D2, held by `architecture:layers:provider-built`. No test is added: that scenario holds who imports `runpod`, and the noun rule cannot be held well.

### D17

Phase 1 ends with the test green over fixed prose. Phase 2 moves rules to their homes. Phase 3 writes the pages that link those homes.

A page touched in a later phase is edited for that phase's own reason alone: phase 1 fixes a false line, phase 3 reshapes.

### D18

The brief's models line stands: build on Opus 5.5 high, converge's checkers on Codex `gpt-6.1-sol` high. The cut rates currency and one home `moderate`, and the readers' pages `hard`: that phase writes `AGENTS.md`, a file the conductor reads.

## Tests

The change adds no test, extends one and removes none. It adds no end-to-end run.

| measure | before | after | command |
|---|---|---|---|
| tests in `tests/test_docs.py` | 10 | 10 | `git grep -c "^def test_" -- tests/test_docs.py` |
| end-to-end runs added | — | 0 | none: no test binds a socket ([D54 of the decisions](../../../docs/decisions.md)) |
| rows of `THREAT_MODEL.md` of 1000 characters or more | 4 | 0 | `git grep -cE "^\| T[0-9]+ (.{250}){4}" -- THREAT_MODEL.md` |
| rows of `THREAT_MODEL.md` holding `Residual` | 7 | 0 | `git grep -cE "^\| T[0-9]+ .*Residual" -- THREAT_MODEL.md` |

The test `test_a_missing_symbol_or_a_line_citation_is_caught` is the extended one, at the lowest layer: a unit test on a tmp tree ([T1](../../../CODING_STANDARDS.md)). It removes no test, so no `I16` table is owed.

## Dependencies

None.

## Risks / Trade-offs

- **The widened test names every root-document citation that fails at once.** Phase 1 fixes each by the code's current name; a citation that names a deleted symbol is rewritten, never dropped to pass.
- **A trimmed threat row loses an analysis.** It moves into a decision ([D8](#d8)); the check is that no row holds `Residual` and each analysis is found where D8 sends it.
- **Reordering `docs/usage.md` breaks an anchor.** It keeps every heading, and the links test names a miss.
- **A decision's heading changes for D7 and D8.** Every anchor to the old slug is found by `git grep` and moved in the same task.
- **Prose a reader finds better is a judgment.** The checks hold what a command can: citations, anchors, length, and the absence of what is said twice.

## Verdict

Ready to build. The cut read every fact at `HEAD` and wrote the shapes above from the code; no decision of the brief is changed.
