# Docs revisit — tasks

The phases: the root documents held by the test and every stale claim fixed, each rule moved to its one home, then the readers' pages written. Shapes and before → after text are in [design](design.md).

## Progress

- [x] 1 — Currency · moderate
- [ ] 2 — One home · moderate
- [ ] 3 — The readers' pages · hard

## 1 — Currency

- [x] 1.1 In `tests/test_docs.py`, make `unresolved` walk `guide(root)` and skip a page that does not exist ([D4](design.md#d4)).
  Extend `test_a_missing_symbol_or_a_line_citation_is_caught` with a `README.md` citing `gpunit/x.py::lost`, and its expected faults.
  Verify: `uv run pytest tests/test_docs.py -k missing_symbol` exits 0.
- [x] 1.2 Redraw `ARCHITECTURE.md`'s diagram with `Provider`, `providers.build`, `runpod` and `hostkey` ([D15](design.md#d15)); the diagram alone.
  Verify: `git grep -n "providers.build" -- ARCHITECTURE.md` prints a line.
- [x] 1.3 In `docs/usage.md`, make the `gpunit.TeardownFailed` row's exit `1`, or `3` when its `__cause__` is `Lost`; the exit table's `1` row agrees ([D3](design.md#d3)).
  Verify: `git grep -nE "TeardownFailed.*[^0-9]3[^0-9]" -- docs/usage.md` prints the row.
- [x] 1.4 In `docs/usage.md`'s *The spend rules*, replace "when no gpunit waits there, after a crash, remove that file" with: the next `up` removes a dead process's mark, and a refusal naming a pid that no longer waits asks for the file's removal ([D3](design.md#d3)).
  Verify: `git grep -n "remove that file" -- docs/usage.md` prints nothing.
- [x] 1.5 In `docs/data-flow.md`, say the seam's outcomes where it says RunPod's HTTP codes: *Place and create*, the `pod` diagram line, the `pod` bullet. Add a `.gpunit/lock` bullet to *The state files*.
  Verify: `git grep -nE "a 400 moves on|204 /|404 on delete" -- docs/data-flow.md` prints nothing, and `git grep -n "gpunit/lock" -- docs/data-flow.md` prints a line.
- [x] 1.6 In `THREAT_MODEL.md`, make F12 and T21 say `_command` drops `provider.key_names`, not `RUNPOD_API_KEY` ([D3](design.md#d3)).
  Verify: `git grep -nE "(without|drops) .RUNPOD_API_KEY" -- THREAT_MODEL.md` prints nothing.
- [x] 1.7 In `THREAT_MODEL.md` §6, list the module `providers`, and the archived changes `0021-gone-pod` and `0022-the-seam` by directory and `design.md`, with no decision id; add each other change from 0014 to 0020 that a row rests on.
  Verify: `git grep -nE "gpunit/\{[a-z,]*providers" -- THREAT_MODEL.md` prints a line, and `git grep -nE "(0021-gone-pod|0022-the-seam)/design.md" -- THREAT_MODEL.md` prints a line.
- [x] 1.8 In `docs/decisions.md`, say what the seam made of [D2](../../../docs/decisions.md), [D23](../../../docs/decisions.md) and [D33](../../../docs/decisions.md): `gpunit/providers.py::build`; `Deleted`'s `kind` and `code`; `Provider.key_names` ([D3](design.md#d3)).
  Verify: `git grep -nE "key_names|kind. and .code" -- docs/decisions.md` prints a line for D23 and for D33.
- [x] 1.9 In `docs/principles.md` *The code*, replace the row "The seam names no provider noun" with "Only `providers` imports `runpod`", from [D2](../../../docs/decisions.md), held by `architecture:layers:provider-built` ([D16](design.md#d16)).
  Verify: `git grep -n "names no provider noun" -- docs/principles.md` prints nothing.
- [x] 1.10 In `docs/extending.md`'s *A provider*, add what a second provider meets: the price prompt and card filter, no `provider` key yet, and `Provider.stop` called by nothing, beside F14.
  Verify: `git grep -n "Provider.stop" -- docs/extending.md` prints a line.
- [x] 1.11 In `docs/modules.md`, leave the layer table, which the layers test reads, add the fourth rule beside the layers, only `providers` imports `runpod`, and describe `gpunit.runpod` as the one `Provider` implementation, not "REST v2 behind the seam".
  Verify: `git grep -n "REST v2 behind the seam" -- docs/modules.md` prints nothing.
- [x] 1.12 In `CONTRIBUTING.md`, tell the pipeline with integrate, say simplify closes build, and drop "but the bootstrap's" by telling the `Change:` trailer truly ([D3](design.md#d3)).
  Verify: `git grep -n "but the bootstrap's" -- CONTRIBUTING.md` prints nothing.
- [x] 1.13 In `gpunit/lifecycle.py`, change `pod_gone`'s comment to cite `decision D57` ([D1](design.md#d1)); `gone` keeps D55.
  Verify: `git grep -n "decision D57" -- gpunit/lifecycle.py` prints a line.
- [x] 1.14 In `docs/proofs.md`, quote the serve target as `make live-serve MODEL=granite-4.0-micro` ([D3](design.md#d3)).
  Verify: `git grep -n "live-serve granite" -- docs/proofs.md` prints nothing.
- [x] 1.15 Run the widened test and fix each root-document citation it names by the code's current name; drop none to pass.
  Verify: `uv run pytest tests/test_docs.py` exits 0.

## 2 — One home

- [ ] 2.1 In `docs/decisions.md`, move D55 to *The window volume* after D43, D56 to *A session* after D21 and D57 to *A session* after D23 ([D7](design.md#d7)); each id and title stands.
  Verify: `git grep -nE "^(## |### D5[567] )" -- docs/decisions.md` prints `## The guide` with none of D55, D56, D57 under it.
- [ ] 2.2 In `docs/decisions.md`, keep D57 as the one statement of the gone rule (the read's 404, the listing, the lock and the pending mark); the shared reason ("a key that fails the listing cannot pass for gone") stays in D55, which D57 links; D55 links D57 for the pod ([D5](design.md#d5)).
  Verify: `git grep -n "cannot pass for gone" -- docs/decisions.md` prints the D55 line alone, and `git grep -nE "\(#d5[57]--" -- docs/decisions.md` prints a link in D55 and in D57.
- [ ] 2.3 Retitle [D7](../../../docs/decisions.md) and [D8](../../../docs/decisions.md) as [design](design.md#d7) says, and move each anchor off the old slugs in `docs/extending.md` and `docs/principles.md`.
  Verify: `git grep -nE "closes-wont-fix|a-patch-closes-cards" -- docs` prints nothing.
- [ ] 2.4 In `docs/principles.md`, replace *The process* with a link to `CONTRIBUTING.md`'s *The rules for a change* ([D5](design.md#d5)).
  Verify: `git grep -n "^### The process" -- docs/principles.md` prints nothing.
- [ ] 2.5 In `docs/usage.md` *The spend rules* and `docs/data-flow.md`'s `pod` bullet, link D57 and drop the restated gone rule.
  Verify: `git grep -nE "wrong key gets a 404|404 on delete" -- docs/usage.md docs/data-flow.md` prints nothing.
- [ ] 2.6 In `docs/usage.md`, move step 3's laptop-command `/proc` text into *The account key*, and its pod-command `/proc` text into *Accepted risks*' pod-key bullet; step 3 links both ([D5](design.md#d5)).
  Verify: `git grep -n "/proc" -- docs/usage.md` prints a line in *The account key* and a line in *Accepted risks*, none in step 3.
- [ ] 2.7 In `THREAT_MODEL.md`, drop each stamp from `v0.8` to `v0.11`, each `closed in v0.N`, and the `v0.11` of the §5 and §6 lead lines, for "holds at the commit it is read at" ([D8](design.md#d8)).
  Verify: `git grep -nE "v0\.(8|9|10|11)([^0-9]|$)" -- THREAT_MODEL.md` prints nothing.
- [ ] 2.8 Drop the install pin: in `README.md`, link `docs/usage.md#use-it-from-a-project` for the install; in `THREAT_MODEL.md` T15, say "a release tag, mutable" ([D9](design.md#d9)).
  Verify: `git grep -n "@v0\." -- README.md THREAT_MODEL.md` prints nothing.
- [ ] 2.9 In `THREAT_MODEL.md` §4, move each row's `Residual:` analysis out of the row ([D8](design.md#d8)): T9 to D31, T21 to D33, T47 to D57, T48 to D55, T13 and T55 to D34; T20's stays in G17. The row links its decision; a value is named by its constant.
  Verify: `git grep -n "Residual" -- THREAT_MODEL.md` prints nothing.
- [ ] 2.10 Trim each §4 row to the threat, its mitigation, its status and its citations; a row of 1000 characters goes to its decision or to §3's flow.
  Verify: `git grep -nE "^\| T[0-9]+ (.{250}){4}" -- THREAT_MODEL.md` prints nothing.
- [ ] 2.11 In `THREAT_MODEL.md` §5, keep G4, G7 and G14 to G17 in full and cut each closed gap to one row of 300 characters or fewer.
  Verify: `git grep -nE "^\| G(1|2|3|5|6|8|9|10|11|12|13) (.{150}){2}" -- THREAT_MODEL.md` prints nothing.
- [ ] 2.12 Run the test and fix each link, anchor or decision citation the moves and trims broke.
  Verify: `uv run pytest tests/test_docs.py` exits 0.

## 3 — The readers' pages

- [ ] 3.1 Reorder `docs/usage.md` as [D6](design.md#d6) lists, moving whole sections; no heading changes.
  Verify: `git grep -n "^## " -- docs/usage.md` prints the headings in [design](design.md#d6)'s order, *Security and privacy* last.
- [ ] 3.2 Thin `docs/usage.md`'s *Security and privacy*: keep its subsection headings, make each bullet one line ending in a link into `THREAT_MODEL.md`.
  Verify: `git grep -n "THREAT_MODEL.md#" -- docs/usage.md` prints a link on each bullet of the section.
- [ ] 3.3 In `README.md`, rename `## Built so` to `## What holds` and make the table a rule a row with at most one link a row; the gone rule links D57 alone ([D13](design.md#d13)). Rename `[the guide](ARCHITECTURE.md)` to `[architecture](ARCHITECTURE.md)`.
  Verify: `git grep -nE "Built so|the guide.\(ARCHITECTURE" -- README.md` prints nothing.
- [ ] 3.4 In `README.md`, add the `gpunit.session()` example of [D13](design.md#d13) and a line on `serve` linking `docs/usage.md#serve-a-model`. To stay within the front-page test, cut in this order until it fits: the `uv add` line, the `## Read more` heading (its links stay), the license badge line, the row on the layers and the docs.
  Verify: `uv run pytest tests/test_docs.py -k front_page` exits 0, and `git grep -n "gpunit.session" -- README.md` prints a line.
- [ ] 3.5 In `ARCHITECTURE.md`, add the table `layer | holds` of [D15](design.md#d15) below the diagram.
  Verify: `git grep -n "^| layer | holds |" -- ARCHITECTURE.md` prints a line.
- [ ] 3.6 Rewrite `AGENTS.md` per [D14](design.md#d14): drop *What holds* and *Tests*, keep the `Worktrees:` and `Workspace setup:` lines word for word, add how to run one test and the `e2e` mark.
  Verify: `git grep -n "^## Tests" -- AGENTS.md` prints nothing, and `git grep -n "pytest tests/" -- AGENTS.md` prints a line.
- [ ] 3.7 In `CONTRIBUTING.md`, add the human's path and the test-placement policy from `AGENTS.md` ("the lowest layer that can fail for it", [D11](design.md#d11)); keep the `@fission-ai/openspec@1.11.0` pin, which the CI test reads.
  Verify: `git grep -n "make e2e" -- CONTRIBUTING.md` prints a line, and `git grep -n "lowest layer" -- CONTRIBUTING.md` prints a line.
- [ ] 3.8 In `CODING_STANDARDS.md` *Project rules*, add the paragraph of [D10](design.md#d10): standard library alone, the pod's entrypoint on Python 3.10 at full coverage, names not counts.
  Verify: `git grep -n "Python 3.10" -- CODING_STANDARDS.md` prints a line.
- [ ] 3.9 Run the test and fix each link, anchor, citation or length it names.
  Verify: `uv run pytest tests/test_docs.py` exits 0.
