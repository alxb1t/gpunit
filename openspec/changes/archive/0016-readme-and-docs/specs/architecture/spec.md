## ADDED Requirements

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
