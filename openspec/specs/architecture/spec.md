## Purpose

The repository's shape and its guide hold each other: the package's imports follow the layers the guide states, and
the guide's links, decision ids and code citations resolve, all checked by the gate on every change.

## Requirements

### Requirement: The modules import down the layers

The gate SHALL fail when a module of the package imports a module of a higher layer, lazy imports inside functions
included. The layers, lowest first: foundation, model, cloud, lifecycle, session, serve, interface. A module MAY import
its own layer, without a cycle. No module SHALL import the package `gpunit` itself. Only the session layer's
`library` and the interface's `cli` SHALL import the RunPod module. The package SHALL import the standard library and
the package alone, and nothing in the package SHALL import `boot`, `live` or `tests`. The serve image's launch script
SHALL import the standard library alone. Only `cli` SHALL call `sys.exit`. The guide's modules page SHALL name every
module of the package in the layer the gate holds it to.

#### Scenario: the package holds its layers
- **Key:** `architecture:layers:hold`
- **WHEN** the gate reads every import of the package, lazy ones included
- **THEN** no import names a higher layer, no layer holds a cycle, and no module imports `gpunit` itself

#### Scenario: an upward import is caught
- **Key:** `architecture:layers:upward-caught`
- **WHEN** a model-layer module imports a lifecycle-layer module, at the top of the file or inside a function
- **THEN** the check names that importer and that module

#### Scenario: a cycle is caught
- **Key:** `architecture:layers:cycle-caught`
- **WHEN** two model-layer modules import each other
- **THEN** the check names the cycle

#### Scenario: the provider is built in two places alone
- **Key:** `architecture:layers:provider-built`
- **WHEN** the gate reads every import of the RunPod module
- **THEN** its importers are `library` and `cli` alone, and a third importer is named

#### Scenario: the standard library alone
- **Key:** `architecture:layers:stdlib-only`
- **WHEN** the gate reads the imports of the package and of the serve image's launch script
- **THEN** the package's imports name the standard library or the package, the launch script's the standard library
  alone, none names `boot`, `live` or `tests`, and a third-party import, or the package in the launch script, is named

#### Scenario: only the CLI exits
- **Key:** `architecture:layers:exit-in-cli`
- **WHEN** the gate reads every call in the package
- **THEN** `sys.exit` is called in `cli` alone, and a call elsewhere is named

#### Scenario: the modules page names every module
- **Key:** `architecture:layers:modules-named`
- **WHEN** the gate reads `docs/modules.md`
- **THEN** it names every module of the package in the layer the gate holds it to, and a module missing or in another
  layer is named

### Requirement: The guide's citations resolve

The gate SHALL fail when a relative link in `docs/`, `README.md` or `CLAUDE.md` names a file that does not exist, or an
anchor its target does not hold. Every decision id the guide links, and every `decision Dn` cited in the code,
configuration and guide, SHALL name a decision in `docs/decisions.md`. No file the gate scans SHALL cite an archived
change's design by its decision id. A backticked repository path in the guide SHALL name a file that exists, a
`path::symbol` citation SHALL name a file that defines that symbol, and the guide SHALL cite no source line by number.

#### Scenario: the guide's links resolve
- **Key:** `architecture:docs:links-resolve`
- **WHEN** the gate reads every relative link in `docs/`, `README.md` and `CLAUDE.md`
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

### Requirement: The front page fits one screen

The gate SHALL fail when `README.md` holds more than 60 lines. The user's guide SHALL live in `docs/usage.md`, and the
front page SHALL link it.

#### Scenario: the front page fits one screen
- **Key:** `architecture:readme:one-screen`
- **WHEN** the gate reads `README.md`
- **THEN** it holds at most 60 lines and links `docs/usage.md`, and a page of 61 lines is named with its length

### Requirement: Every push runs the gate

The repository SHALL hold a workflow that runs `make gate` on every push and every pull request, with the OpenSpec CLI
at the version `CLAUDE.md` records. Every workflow SHALL name each action it uses by a full commit hash.

#### Scenario: the gate workflow runs the gate
- **Key:** `architecture:ci:runs-the-gate`
- **WHEN** the gate reads `.github/workflows/gate.yml`
- **THEN** its triggers are `push` and `pull_request`, a step runs `make gate`, and a step installs the OpenSpec CLI at
  the version `CLAUDE.md` records

#### Scenario: every workflow pins its actions
- **Key:** `architecture:ci:actions-pinned`
- **WHEN** the gate reads every file under `.github/workflows/`
- **THEN** each `uses:` names an action by a 40-hex commit, and an action named by a tag is caught
