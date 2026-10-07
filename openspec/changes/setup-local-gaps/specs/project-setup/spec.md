## MODIFIED Requirements

### Requirement: Setup notices the `.env` convention only when `jev` is chosen

When the project's answer for `decision_model` is `jev`, setup's plan SHALL show a
notice naming the `.env` file the `jev` backend reads (`decision-model`'s `.env`
fallback) and the key it expects (`OPENROUTER_API_KEY=`), and, when the project is a git
repository, SHALL add `.env` to the repository's own local exclude list
(`.git/info/exclude`), under either visibility. Setup SHALL NOT read, write or create
`.env` or the project's `.gitignore`. Under `shared` visibility the notice SHALL also say
that the exclusion protects this clone only. When `decision_model` is not `jev`, setup
SHALL NOT show the notice or add the entry.

#### Scenario: `jev` is chosen

- **WHEN** setup runs in a git repository whose answer for `decision_model` is `jev`
- **THEN** the plan shows the notice and an `.git/info/exclude` step adding `.env`, and
  after writing, `git check-ignore .env` succeeds while `.env` and `.gitignore` are
  byte-identical to before

#### Scenario: `jev` is chosen and `git init` is part of the plan

- **WHEN** setup creates the repository in the same run (local visibility, no `.git`)
- **THEN** the one plan lists `git init` and the `.env` exclusion together, the person's
  single yes covers both, the repository is created first and `.env` is excluded in the
  same run's write, before any commit can exist; no second plan is shown or approved

#### Scenario: `mock` is chosen

- **WHEN** setup runs in a project whose answer for `decision_model` is `mock`
- **THEN** no `.env` notice is shown and `.env` is not added to the exclude list

#### Scenario: The choice changes from `jev` to `mock`

- **WHEN** a project's recorded `decision_model` changes from `jev` to `mock` and setup
  or update is run again
- **THEN** the notice is no longer shown and the entry is not added again; an entry an
  earlier run added is left in place, since the exclude list is the repository's own

### Requirement: Local visibility asks a fixed, guided list of questions

Under `local` visibility, the command SHALL ask the same choices it asks under `shared`
visibility (profiles, rule sets, features, canary word, decision backend, check
command), from the same fixed, stated list, plus two further choices: which roles or
tools — the builder's two bindings included — the person wants active for this project,
and where the OpenSpec store lives. When Codex is among the tools, the command SHALL
state, as part of asking, that the apply loop hands the rules to Codex, and that Codex
run outside the loop does not have them, since `AGENTS.md` is never written under
`local` visibility.

#### Scenario: Asking under local visibility

- **WHEN** the command asks its questions for a project with `visibility: local`
- **THEN** every question asked under `shared` visibility is asked here too, in the same
  fixed list, plus the roles/tools question and the store location question

#### Scenario: Codex is chosen under local visibility

- **WHEN** the person includes Codex among the active tools for a `local` visibility
  project
- **THEN** the command states, at the point of asking, that `apply` hands Codex the rules
  and that Codex used outside `apply` will not have them

### Requirement: Local visibility registers a local OpenSpec store instead of a project `openspec/` directory

Under `local` visibility, the command SHALL ask the person where the store lives, never
adopting a location the OpenSpec tool or the command itself suggests without the
person's answer. It SHALL show the registration in the plan — id and path — and run it
only after the person's yes to that plan, then record the id among the project's choices
instead of creating or writing to an `openspec/` directory inside the project. Running
the command again with an already-registered store SHALL reuse it and ask nothing about
it.

#### Scenario: First setup under local visibility

- **WHEN** setup runs for the first time on a project choosing `visibility: local`
- **THEN** the person is asked where the store lives, the plan lists the registration
  with that path, a store is registered at that path only after the yes, its id is
  recorded, and no `openspec/` directory is created in the project

#### Scenario: Setup run again

- **WHEN** setup runs again on a project with `visibility: local` and an already
  recorded store id
- **THEN** the existing store is reused, no path is asked and no second store is
  registered

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
  identical to a run of the command before this choice existed, except for the one
  deliberate addition the `.env` requirement above makes when `jev` is chosen

## ADDED Requirements

### Requirement: Every side effect of setup appears in the plan before the person's yes

Setup SHALL show, as lines of its plan, every effect it will cause beyond writing
project files: creating a git repository (`git init`), registering an OpenSpec store, and
changing the person's global settings, the last with the exact key and value. It SHALL
perform none of them before the person's yes to that plan, and its final report SHALL
name each one it performed. The global setting keeps its own explicit yes (see the
requirement that offers it): the plan line shows it, the plan's yes alone does not
approve it.

#### Scenario: A project with no repository under local visibility

- **WHEN** setup plans for a `local` project with no `.git`
- **THEN** the plan lists `git init` as a step, and no repository exists until the person
  has said yes

#### Scenario: The global setting is written

- **WHEN** the person approved the global setting and setup wrote it
- **THEN** the final report names the file, the key and the value it set

#### Scenario: The global setting is shown in the plan but not yet approved

- **WHEN** the plan contains the global setting line and the person has not given its
  own yes
- **THEN** the setting is not written, the line stays in the plan as a notice, and the
  rest of setup proceeds on the plan's yes
