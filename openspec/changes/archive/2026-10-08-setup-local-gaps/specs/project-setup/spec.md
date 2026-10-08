## MODIFIED Requirements

### Requirement: Setup notices the `.env` convention only when `jev` is chosen

When the project's answer for `decision_model` is `jev`, setup's plan SHALL show a
notice naming the `.env` file the `jev` backend reads (`decision-model`'s `.env`
fallback) and the key it expects (`OPENROUTER_API_KEY=`), and, when the project is a git
repository, SHALL add `.env` to the repository's own local exclude list
(`.git/info/exclude`, resolved through git so a worktree or a subdirectory uses its own
repository's list), under either visibility. Setup SHALL NOT read, write or create
`.env` or the project's `.gitignore`. Under `shared` visibility the notice SHALL also say
that the exclusion protects this clone only. When `decision_model` is not `jev`, setup
SHALL NOT show the notice or add the entry.

#### Scenario: `jev` is chosen

- **WHEN** setup runs in a git repository whose answer for `decision_model` is `jev`
- **THEN** the plan shows the notice and an `.git/info/exclude` step adding `.env`, and
  after writing, `git check-ignore .env` succeeds while `.env` and `.gitignore` are
  byte-identical to before

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
and where the OpenSpec store lives — the latter only when no store id is recorded and no
store is already registered under the id setup would use. When Codex is among the tools, the command SHALL
state, as part of asking, that the apply loop hands the rules to Codex, and that Codex
run outside the loop does not have them, since `AGENTS.md` is never written under
`local` visibility.

#### Scenario: Asking under local visibility

- **WHEN** the command asks its questions for a project with `visibility: local`
- **THEN** every question asked under `shared` visibility is asked here too, in the same
  fixed list, plus the roles/tools question and, unless a store is already recorded or
  registered for the project, the store location question

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
it; a store path answered for a project that already records a store id SHALL be refused
rather than planned as a second registration. A store already registered under the id
setup would use (left behind by a run interrupted after registering and before writing)
SHALL be reused, not registered again, and no path asked for it: the answers then carry
the id, no path and a flag that the store is already registered, and the plan shows a
reuse line in place of a registration. A store path inside the project's own directory
SHALL be refused, since registering there would create an `openspec/` directory in the
project.

#### Scenario: First setup under local visibility

- **WHEN** setup runs for the first time on a project choosing `visibility: local`
- **THEN** the person is asked where the store lives, the plan lists the registration
  with that path, a store is registered at that path only after the yes, its id is
  recorded, and no `openspec/` directory is created in the project

#### Scenario: Setup run again

- **WHEN** setup runs again on a project with `visibility: local` and an already
  recorded store id
- **THEN** the existing store is reused, no path is asked and no second store is
  registered; an answers document that still carries a store path is refused

#### Scenario: A store registered by an interrupted run

- **WHEN** a previous run registered the store and was interrupted before writing, so no
  store id is recorded yet, and the store is found registered under the id setup would use
- **THEN** no path is asked, the plan shows that store reused rather than registered, and
  writing records its id

#### Scenario: A store path inside the project

- **WHEN** the person answers a store path that is, or resolves to, the project's own
  directory or a path under it
- **THEN** setup refuses it before anything is registered or written

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
  identical to a run of the command before this choice existed, except for two
  deliberate additions: the `.env` exclusion when `jev` is chosen, and the clean
  working tree requirement below

### Requirement: One command sets a project up, and asks before it acts

The harness SHALL provide a single command that brings a project to a harnessed state.
That command SHALL gather the project's choices, SHALL show what it intends to do, and
SHALL make no change to the project until the person has approved that intention. The
project SHALL be inside a git repository with its own work committed (see "Setup runs
only on a clean git working tree").

#### Scenario: An empty project

- **WHEN** the command is run in a project that has never been harnessed — an empty or
  already working one, inside a git repository with nothing of its own left to commit —
  and the person approves the plan
- **THEN** the project ends with the files the harness needs, the rules of the sets chosen,
  the project's recorded answers, the permission entries of the floor and the record of what
  was generated, and the command reports each path it wrote

#### Scenario: Approval withheld

- **WHEN** the plan is shown and the person does not approve it
- **THEN** no path is created, modified or removed, and the command says that nothing was
  written

### Requirement: Running setup again changes nothing

Run a second time on a project whose choices and harness content have not changed, the
command SHALL report that there is nothing to do and SHALL leave every path byte-identical,
including the record of what was generated.

#### Scenario: A second run

- **WHEN** the command is run twice in succession with no change in between
- **THEN** the second run plans nothing to do and no byte of the project changes

#### Scenario: A fresh clone of a harnessed project

- **WHEN** a project that was set up is cloned fresh and the command is run in the clone
- **THEN** it recognises the project as already harnessed from the committed record, asks
  nothing, and plans to restore only what is deliberately not committed — the runtime
  state location and, for a `jev` project, the `.env` entry in the clone's own exclude
  list; every committed path is reported unchanged

## ADDED Requirements

### Requirement: Every side effect of setup appears in the plan before the person's yes

Setup SHALL show, as lines of its plan, every effect it will cause beyond writing
project files: registering an OpenSpec store and changing the person's global settings, the last with the exact key and value. It SHALL
perform none of them before the person's yes to that plan, and its final report SHALL
name each one it performed. The global setting keeps its own explicit yes (see the
requirement that offers it): the plan line shows it, the plan's yes alone does not
approve it.

#### Scenario: A first local setup

- **WHEN** setup plans for a `local` project with no recorded store
- **THEN** the plan lists the store registration with its id and path, and no store is
  registered until the person has said yes

#### Scenario: The global setting is written

- **WHEN** the person approved the global setting and setup wrote it
- **THEN** the final report names the file, the key and the value it set

#### Scenario: The global setting is shown in the plan but not yet approved

- **WHEN** the plan contains the global setting line and the person has not given its
  own yes
- **THEN** the setting is not written, the line stays in the plan as a notice, and the
  rest of setup proceeds on the plan's yes

### Requirement: Setup runs only on a clean git working tree

Under either visibility, `setup` SHALL require the project to sit inside a git repository
— its own `.git` directory, a worktree's `.git` file, or a parent directory's repository
— whose working tree, within the project's own directory, is clean apart from the
harness's own paths: `git status --porcelain` scoped to the project's directory
(untracked files included, ignored files excluded; uncommitted paths elsewhere in a
parent repository do not count) SHALL report no path other than one
setup itself writes or owns (`AGENTS.md`, `CLAUDE.md`, `.harnex.yml`, anything under
`.harnex/`, `openspec/config.yaml`, `.claude/settings.json`, `.mcp.json`,
`CLAUDE.local.md`, `.claude/settings.local.json`). No repository, a failing `git status`,
or any other listed path SHALL be a conflict, reported alongside the rest of the plan like
any other conflict — every path still appears in the plan — and stopping the run before
any write. The conflict SHALL name what to do — create the repository and commit, or
commit or stash the changes — and list the offending paths. Setup SHALL NOT run
`git init`, commit, stash or otherwise change the history or the index to get past it.
`update` SHALL NOT apply this check: it refreshes harness-owned paths only and asks
nothing. The guided command MAY check the same rule before its first question and stop
there, so the person is not asked anything the plan would refuse; the script's own
conflict, reported alongside its full plan, remains the enforcement.

#### Scenario: Not a git repository

- **WHEN** setup runs in a directory that is not inside any git repository
- **THEN** the plan shows a conflict saying to run `git init` and commit first, nothing is
  written and no repository is created

#### Scenario: Uncommitted or untracked project changes

- **WHEN** setup runs in a git repository where `git status --porcelain` reports at least
  one path that is not one of the harness's own
- **THEN** the plan shows a conflict listing those paths, every other path is still
  planned, and nothing is written

#### Scenario: A clean repository

- **WHEN** setup runs in a git repository with nothing to commit
- **THEN** the precondition holds and setup plans as usual

#### Scenario: A shared rerun before the person commits

- **WHEN** a `shared` setup has written and is run again before its own files are
  committed
- **THEN** the only uncommitted paths are the harness's own, the precondition holds, and
  the rerun plans nothing to do

#### Scenario: An interrupted setup

- **WHEN** setup was interrupted after some of its writes and is run again
- **THEN** the partially written paths are the harness's own, the precondition holds, and
  the rerun completes without the person committing or stashing anything

#### Scenario: A worktree or a subdirectory

- **WHEN** the project is a git worktree, or a subdirectory of a repository
- **THEN** the precondition is checked against the project's own directory within that
  repository, and the `.env` exclusion is written to that repository's own exclude list

#### Scenario: `update` on an uncommitted tree

- **WHEN** `update` runs on a project with uncommitted changes
- **THEN** it is not refused on that account
