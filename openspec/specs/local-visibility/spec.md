# local-visibility Specification

## Purpose
What it means for a harnessed project to have `local` visibility: a per-project choice,
read by every harness operation, that nothing the harness writes for that project ever
reaches the project's own version-control history.

## Requirements

### Requirement: Visibility is a per-project choice, read by every harness operation

The project's recorded choices SHALL include a `visibility` value of either `shared` or
`local`, defaulting to `shared`. Every harness operation that decides where to write a
path, which file to share a permission entry with, or where to run an OpenSpec command
SHALL read this value rather than infer it from what it finds on disk.

#### Scenario: The default

- **WHEN** a project's recorded choices do not set `visibility`
- **THEN** every harness operation treats it as `shared`, matching behaviour before this
  value existed apart from the deliberate additions `shared` itself later received (the
  `.env` exclusion and setup's clean working tree requirement, in `project-setup`)

#### Scenario: Local visibility recorded

- **WHEN** a project's recorded choices set `visibility` to `local`
- **THEN** every harness operation that would otherwise write a project-shared path
  writes its local-visibility equivalent instead

### Requirement: A harness-owned path stays untracked without touching a project-owned ignore file

Under `local` visibility, every path the harness writes SHALL be excluded from version
control either by living inside a directory that ignores itself, or, for a path that
cannot live inside such a directory, by an entry in the repository's own local exclude
list (`.git/info/exclude`). Neither case SHALL add, remove or otherwise modify a
project-owned ignore file.

#### Scenario: A path inside a self-ignoring directory

- **WHEN** a harness-owned path under `local` visibility lives inside `.harnex/`
- **THEN** it is excluded by that directory's own ignore file, and the project's own
  ignore file, if any, is byte-identical to before the write

#### Scenario: A path that cannot live inside one

- **WHEN** a harness-owned path under `local` visibility must live at the project root
  (for example `CLAUDE.local.md`)
- **THEN** it is excluded through an entry the harness adds to `.git/info/exclude`, and
  the project's own ignore file is untouched

### Requirement: Every harness command that touches OpenSpec resolves a local store under local visibility

Under `local` visibility, every harness command that invokes the `openspec` CLI or reads
or writes a path under `openspec/changes/<name>/` directly — `propose`, `apply`, `verify`
and `ship` — SHALL resolve the OpenSpec store to use from the project's recorded choices,
and SHALL use it in place of the nearest `openspec/` directory in the project. A command
that never touches OpenSpec at all — `explore` and `review`, neither of which calls
`openspec` or reads a change's own directory under either visibility — SHALL NOT be
asked to resolve anything, since there is nothing for it to resolve.

#### Scenario: A command that touches OpenSpec, under local visibility

- **WHEN** `propose`, `apply`, `verify` or `ship` runs in a project with `local`
  visibility
- **THEN** it resolves the store id recorded in the project's choices and uses it in
  place of the project's own `openspec/`, and no `openspec/` directory is created in the
  project as a result

#### Scenario: A command that touches OpenSpec, under shared visibility

- **WHEN** `propose`, `apply`, `verify` or `ship` runs in a project with `shared`
  visibility (or no recorded visibility)
- **THEN** it operates on the project's own `openspec/` directory exactly as before this
  capability existed

#### Scenario: A command that never touches OpenSpec

- **WHEN** `explore` or `review` runs, under either visibility
- **THEN** neither resolves a store nor reads a change's own directory, since neither
  calls `openspec` or depends on one existing in the first place
