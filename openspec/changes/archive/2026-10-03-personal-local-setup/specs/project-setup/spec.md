## ADDED Requirements

### Requirement: Setup offers a visibility choice

The command SHALL ask whether the project is harnessed for `shared` (the project's team,
via source control) or `local` (the person running it alone) use, defaulting to
`shared` when the person does not change it. The answer SHALL be recorded among the
project's choices and SHALL govern every other requirement in this capability that
distinguishes the two.

#### Scenario: Choosing local

- **WHEN** the person answers `local` to the visibility question
- **THEN** the project's recorded choices hold `visibility: local`, and the rest of this
  run follows the local-visibility requirements below

#### Scenario: Accepting the default

- **WHEN** the person does not change the visibility question
- **THEN** the project's recorded choices hold `visibility: shared`, and the run is
  identical to a run of the command before this choice existed

### Requirement: Local visibility asks a fixed, guided list of questions

Under `local` visibility, the command SHALL ask the same choices it asks under `shared`
visibility (profiles, rule sets, features, canary word, decision backend, check
command), from the same fixed, stated list, plus one further choice: which roles or
tools — the builder's two bindings included — the person wants active for this project.
When Codex is among them, the command SHALL state, as part of asking the question, that
the Codex builder binding cannot read the project's rules under `local` visibility,
since doing so depends on `AGENTS.md`, which local visibility never touches.

#### Scenario: Asking under local visibility

- **WHEN** the command asks its questions for a project with `visibility: local`
- **THEN** every question asked under `shared` visibility is asked here too, in the same
  fixed list, plus the roles/tools question

#### Scenario: Codex is chosen under local visibility

- **WHEN** the person includes Codex among the active roles/tools for a `local`
  visibility project
- **THEN** the command states, at the point of asking, that Codex will not see this
  project's rules under local visibility, before recording the choice

### Requirement: Local visibility writes the permission floor and any MCP entry to the person's own local configuration

Under `local` visibility, the command SHALL write the permission floor's entries to
`.claude/settings.local.json` instead of `.claude/settings.json`, and SHALL register any
MCP entry the project needs (for example Playwright, for a UI profile) with a
local-scoped registration instead of writing it into the project's `.mcp.json`. Neither
file SHALL be read for merging, and neither SHALL be modified.

#### Scenario: The floor, under local visibility

- **WHEN** setup writes the permission floor for a project with `visibility: local`
- **THEN** the entries land in `.claude/settings.local.json`, and `.claude/settings.json`
  is untouched

#### Scenario: A UI profile, under local visibility

- **WHEN** a project with `visibility: local` has a UI profile among its recorded
  profiles
- **THEN** the Playwright MCP entry is registered locally, and the project's `.mcp.json`
  is untouched

### Requirement: Local visibility registers a local OpenSpec store instead of a project `openspec/` directory

Under `local` visibility, the command SHALL register a local OpenSpec store and record
its id among the project's choices, instead of creating or writing to an `openspec/`
directory inside the project. Running the command again with an already-registered store
SHALL reuse it rather than registering a second one.

#### Scenario: First setup under local visibility

- **WHEN** setup runs for the first time on a project choosing `visibility: local`
- **THEN** a local OpenSpec store is registered, its id is recorded among the project's
  choices, and no `openspec/` directory is created in the project

#### Scenario: Setup run again

- **WHEN** setup runs again on a project with `visibility: local` and an already
  recorded store id
- **THEN** the existing store is reused and no second store is registered

### Requirement: Setup offers the one global setting local visibility depends on, once, with explicit yes

Under `local` visibility, when the person's own `~/.claude/settings.json` does not
already set the project-instructions behaviour that keeps a project's `CLAUDE.local.md`
from suppressing that project's own `AGENTS.md`, the command SHALL show the exact change
it would make there and SHALL make it only after an explicit yes. This offer SHALL be
made at most once needed per machine, never silently, and SHALL NOT be made under
`shared` visibility.

#### Scenario: The setting is missing

- **WHEN** setup runs under `local` visibility and the person's own settings do not yet
  set the project-instructions behaviour
- **THEN** the command shows the exact change and makes it only after an explicit yes

#### Scenario: The setting is already present

- **WHEN** the person's own settings already set it
- **THEN** the command makes no offer and no change

#### Scenario: The person declines

- **WHEN** the person declines the offer
- **THEN** the setting is left as it was, the command states that a project relying on
  `AGENTS.md` may stop being read once `CLAUDE.local.md` exists, and finishes the rest
  of its work

## MODIFIED Requirements

### Requirement: The project's own files are never rewritten

A file the project owns SHALL NOT be modified by the harness except by inserting a line
the person explicitly approved, and SHALL NOT be created when it already exists. When the
harness creates such a file, it SHALL be created from a template that names no particular
project. Under `local` visibility, `AGENTS.md` and `CLAUDE.md` SHALL NOT be created,
modified, or offered for insertion at all, whether or not they already exist: the command
writes `CLAUDE.local.md` instead, holding a single import of the project's rules file,
excluded from version control per the local-visibility capability's own requirement.

#### Scenario: An entry file without the harness's pointer line

- **WHEN** a file the project's tools read first exists but does not tell them where the
  rules are
- **THEN** the command shows the exact line it would insert and where it would go, and
  inserts it only after an explicit yes

#### Scenario: The insertion is declined

- **WHEN** the person declines the insertion
- **THEN** the command finishes the rest of its work, states which tool will not read the
  rules as a result, and repeats that notice on every later run

#### Scenario: A project file that already says what is needed

- **WHEN** an entry file already carries the pointer line
- **THEN** the file is left byte-identical and the plan says so

#### Scenario: Local visibility, no AGENTS.md or CLAUDE.md present

- **WHEN** setup runs under `local` visibility in a project with neither file
- **THEN** neither file is created, and `CLAUDE.local.md` is written instead

#### Scenario: Local visibility, AGENTS.md already present

- **WHEN** setup runs under `local` visibility in a project that already has a committed
  `AGENTS.md`
- **THEN** `AGENTS.md` is left byte-identical, no insertion is offered, and
  `CLAUDE.local.md` is written instead

### Requirement: Runtime state stays out of the project's history without touching the project's rules

The command SHALL place the runtime state the harness writes at task time in one location
that excludes itself from version control, and SHALL NOT modify the project's own
version-control exclusions to achieve it. Under `local` visibility, this extends to every
harness-owned path, not only runtime state: the whole of `.harnex/` SHALL exclude itself,
and any harness-owned path that cannot live inside a self-ignoring directory SHALL be
excluded as the local-visibility capability's own requirement describes, with the
project's own exclusions untouched either way.

#### Scenario: After setup

- **WHEN** setup has completed
- **THEN** the runtime state location excludes itself, and the project's own exclusion
  file is byte-identical or still absent

#### Scenario: After setup under local visibility

- **WHEN** setup has completed for a project with `visibility: local`
- **THEN** every harness-owned path, not only runtime state, is already excluded from
  version control, and the project's own exclusion file is byte-identical or still
  absent
