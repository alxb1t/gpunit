## ADDED Requirements

### Requirement: The modules import down the layers, and RunPod only through providers

The gate SHALL fail when a module of the package imports a module of a higher layer, lazy imports inside functions
included. The layers, lowest first: foundation, model, cloud, lifecycle, session, serve, interface. A module MAY import
its own layer, without a cycle. No module SHALL import the package `gpunit` itself. Only the cloud layer's `providers`
SHALL import the RunPod module. The package SHALL import the standard library and
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

#### Scenario: the RunPod module is imported by providers alone
- **Key:** `architecture:layers:provider-built`
- **WHEN** the gate reads every import of the RunPod module
- **THEN** its importer is `providers` alone, and any other importer is named

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

## MODIFIED Requirements

### Requirement: The guide's citations resolve

The gate SHALL fail when a relative link in `docs/`, `README.md`, `AGENTS.md`, `ARCHITECTURE.md`, `THREAT_MODEL.md`,
`CODING_STANDARDS.md` or `CONTRIBUTING.md` names a file that does not exist, or an anchor its target does not hold.
Every decision id the guide links, and every `decision Dn` cited in the code, configuration and guide, SHALL name a
decision in `docs/decisions.md`. No file the gate scans SHALL cite an archived change's design by its decision id. A
backticked repository path in `docs/` or in a root document SHALL name a file that exists, a `path::symbol` citation
SHALL name a file that defines that symbol, and neither SHALL cite a source line by number.

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
- **WHEN** a page of `docs/` or a root document cites `gpunit/lifecycle.py::up`, or a file by line as
  `gpunit/lifecycle.py:75`
- **THEN** the symbol citation passes while the file defines `up`, a missing symbol is named with its page, and the
  line citation is named with its page

## REMOVED Requirements

### Requirement: The modules import down the layers

**Reason:** its scenario `architecture:layers:provider-built` was titled "the provider is built in two places alone",
and it checks who imports the RunPod module. A strict delta cannot retitle a scenario in place, so the requirement
is renamed.
**Migration:** the same rules and the same scenario keys, under *The modules import down the layers, and RunPod only
through providers*.
