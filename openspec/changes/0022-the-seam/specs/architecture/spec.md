## MODIFIED Requirements

### Requirement: The modules import down the layers

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

#### Scenario: the provider is built in two places alone
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
