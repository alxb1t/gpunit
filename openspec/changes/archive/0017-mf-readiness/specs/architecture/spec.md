## MODIFIED Requirements

### Requirement: The guide's citations resolve

The gate SHALL fail when a relative link in `docs/`, `README.md`, `AGENTS.md`, `ARCHITECTURE.md`, `THREAT_MODEL.md`,
`CODING_STANDARDS.md` or `CONTRIBUTING.md` names a file that does not exist, or an anchor its target does not hold.
Every decision id the guide links, and every `decision Dn` cited in the code, configuration and guide, SHALL name a
decision in `docs/decisions.md`. No file the gate scans SHALL cite an archived change's design by its decision id. A
backticked repository path in the guide SHALL name a file that exists, a `path::symbol` citation SHALL name a file
that defines that symbol, and the guide SHALL cite no source line by number.

#### Scenario: the guide's links resolve
- **Key:** `architecture:docs:links-resolve`
- **WHEN** the gate reads every relative link in `docs/`, `README.md`, `AGENTS.md`, `ARCHITECTURE.md`,
  `THREAT_MODEL.md`, `CODING_STANDARDS.md` and `CONTRIBUTING.md`
- **THEN** each names a file that exists, and each anchor names a heading of that file

#### Scenario: a broken link is caught
- **Key:** `architecture:docs:link-caught`
- **WHEN** a page links a file that does not exist, or an anchor its target lacks
- **THEN** the check names the page and the link

#### Scenario: every decision cited is in force
- **Key:** `architecture:docs:decisions-resolve`
- **WHEN** the gate reads every `decision Dn` in the scanned files and every decision link in the guide
- **THEN** each names a `### Dn ·` heading of `docs/decisions.md`, and an unknown id is named with its file

#### Scenario: an archived citation is caught
- **Key:** `architecture:docs:archive-caught`
- **WHEN** a scanned file cites `0010 design D10`
- **THEN** the check names the file and the citation

#### Scenario: a symbol citation resolves
- **Key:** `architecture:docs:symbols-resolve`
- **WHEN** the guide cites `gpunit/lifecycle.py::up`, or a file by line as `gpunit/lifecycle.py:75`
- **THEN** the symbol citation passes while the file defines `up`, a missing symbol is named, and the line citation
  is named

### Requirement: Every push runs the gate

The repository SHALL hold a workflow that runs `make gate` and then `make e2e` on every push and every pull request, with the
OpenSpec CLI at the version `CONTRIBUTING.md` records. Every workflow SHALL name each action it uses by a full commit hash.

#### Scenario: the gate workflow runs the gate
- **Key:** `architecture:ci:runs-the-gate`
- **WHEN** the gate reads `.github/workflows/gate.yml`
- **THEN** its triggers are `push` and `pull_request`, a step runs `make gate`, a later step runs `make e2e`, and a step
  installs the OpenSpec CLI at the version `CONTRIBUTING.md` records

#### Scenario: every workflow pins its actions
- **Key:** `architecture:ci:actions-pinned`
- **WHEN** the gate reads every file under `.github/workflows/`
- **THEN** each `uses:` names an action by a 40-hex commit, and an action named by a tag is caught
