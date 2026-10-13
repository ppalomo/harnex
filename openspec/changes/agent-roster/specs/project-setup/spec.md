## ADDED Requirements

### Requirement: Setup asks for the roster on a first setup

On a first setup — a project whose choices are not yet recorded — after the profiles
are chosen, the command SHALL offer every specialist the harness holds, grouped by
department and each shown as its emoji, one space and its name, with the phase that
starts it; SHALL propose as the team every specialist the chosen profiles hold a
fragment for, and an empty bench; and SHALL record the person's answer as the two
lists, `team` and `bench`, in the project's choices. A project whose choices are
already recorded SHALL NOT be asked: the person edits the project's own choices file
and runs setup or update again.

#### Scenario: A first setup choosing a profile with fragments

- **WHEN** setup runs for the first time and the person chooses a profile holding three
  fragments
- **THEN** the roster question proposes those three specialists as the team and nobody
  on the bench, lists every other specialist the harness holds under its department,
  and the answer is recorded as `team` and `bench`

#### Scenario: A specialist outside the chosen profiles

- **WHEN** the person puts on the team a specialist no chosen profile holds a fragment
  for
- **THEN** the plan shows a generic agent for it under `.claude/agents/`, and the write
  renders it

#### Scenario: Choices already recorded, no roster

- **WHEN** setup runs on a project whose choices are recorded without `team` or `bench`
- **THEN** no roster question is asked, the choices file is left unchanged, and the
  chosen profiles' fragments decide the agents as before

## MODIFIED Requirements

### Requirement: The project's choices are recorded where both sides read them

The command SHALL record the project's answers — its name, the profiles and rule sets and
features chosen, the canary word, the decision backend, the command that checks the
project and, from this version on a first setup, the roster's two lists, `team` and
`bench` — in one file that belongs to the project. `team` and `bench` SHALL be optional
when the file is read, present together or absent together, so that a project recorded
before they existed is read unchanged and is read as having no roster. That file SHALL be
created only when absent, and SHALL be read as the input of every later harness operation
rather than being rewritten by one. Under `local` visibility the same two optional keys
SHALL be read from, and written to, the local choices file.

#### Scenario: Reading the choices back

- **WHEN** any harness component needs to know what the project chose
- **THEN** it reads that one file, and every choice the command asked for is present in it

#### Scenario: The choices already recorded

- **WHEN** the command runs in a project whose answers are already recorded
- **THEN** it takes them as its input, does not ask again, and leaves the file unchanged

#### Scenario: A choices file from before the roster existed

- **WHEN** a harness component reads a choices file that carries neither `team` nor
  `bench`
- **THEN** it reads it without refusing and treats the project as having no roster

#### Scenario: The local choices file

- **WHEN** a `local` visibility project's choices carry `team` and `bench`
- **THEN** every harness operation reads them from `.harnex/config.yml` the same way a
  `shared` project's are read from `.harnex.yml`

### Requirement: The plan includes the chosen profiles' agents

For every specialist the project's roster renders — the `team` and `bench` lists when
recorded, the chosen profiles' fragments otherwise — setup's plan SHALL include one
line per rendered agent under `.claude/agents/`, prefixed or generic, with the same
outcomes as any other harness-owned path — create, unchanged, update, conflict or adopt
— and one line per agent the record lists but the choices no longer produce, marked for
removal or as a conflict. The choices setup offers SHALL say, for each profile, which
specialists it holds a fragment for, and SHALL list every specialist the harness holds
with its department, emoji and phase, so the person knows what a roster may name.

#### Scenario: A profile with a team is chosen

- **WHEN** setup plans for a project that chose a profile with three fragments and
  records no roster
- **THEN** three `.claude/agents/` lines appear in the plan, one per agent, each with
  its action, and the write produces those three files and records them

#### Scenario: A roster naming a specialist without a fragment

- **WHEN** setup plans for a project whose `team` names a specialist no chosen profile
  holds a fragment for
- **THEN** one `.claude/agents/<specialist>.md` line appears, and the write produces the
  generic agent and records it

#### Scenario: A profile without a team is chosen

- **WHEN** setup plans for a project whose only chosen profile is a single-file profile
  and whose choices record no roster
- **THEN** no `.claude/agents/` line appears and nothing is written there

#### Scenario: Under local visibility

- **WHEN** setup plans for a `local` visibility project whose roster renders agents
- **THEN** each rendered agent, prefixed or generic, is planned under `.claude/agents/`
  and its own path is planned into `.git/info/exclude`, with no entry for the directory
  itself

### Requirement: Local visibility asks a fixed, guided list of questions

Under `local` visibility, the command SHALL ask the same choices it asks under `shared`
visibility (profiles, the roster on a first setup, rule sets, features, canary word,
decision backend, check command), from the same fixed, stated list, plus two further
choices: which roles or tools — the builder's two bindings included — the person wants
active for this project, and where the OpenSpec store lives — the latter only when no
store id is recorded and no store is already registered under the id setup would use.
When Codex is among the tools, the command SHALL state, as part of asking, that the
apply loop hands the rules to Codex, and that Codex run outside the loop does not have
them, since `AGENTS.md` is never written under `local` visibility.

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

#### Scenario: The roster under local visibility

- **WHEN** a first setup runs with `visibility: local`
- **THEN** the roster question is asked after the profiles, as under `shared`, and the
  answer is recorded in `.harnex/config.yml`

### Requirement: Setup runs only on a clean git working tree

Under either visibility, `setup` SHALL require the project to sit inside a git repository
— its own `.git` directory, a worktree's `.git` file, or a parent directory's repository
— whose working tree, within the project's own directory, is clean apart from the
harness's own paths: `git status --porcelain` scoped to the project's directory
(untracked files included, ignored files excluded; uncommitted paths elsewhere in a
parent repository do not count) SHALL report no path other than one
setup itself writes or owns (`AGENTS.md`, `CLAUDE.md`, `.harnex.yml`, anything under
`.harnex/`, `openspec/config.yaml`, `.claude/settings.json`, `.mcp.json`,
`CLAUDE.local.md`, `.claude/settings.local.json`, and every rendered agent path
under `.claude/agents/` — `<profile>-<specialist>.md` or the generic
`<specialist>.md` — that the recorded roster and profiles produce or that the
generation record lists — so a stale agent awaiting removal never blocks the run that
removes it — but not the directory `.claude/agents/` itself, since the project's own
agents in it are the project's). No repository, a failing `git status`,
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

#### Scenario: A shared rerun with rendered agents uncommitted

- **WHEN** a `shared` setup whose roster renders agents, prefixed or generic, has
  written them under `.claude/agents/` and is run again before they are committed
- **THEN** those agent paths count as the harness's own, the precondition holds, and
  the rerun plans nothing to do

#### Scenario: A stale agent before the run that removes it

- **WHEN** a specialist was dropped from the roster or its profile from the choices,
  its agents are listed in the record and still uncommitted, and setup runs again
- **THEN** those paths count as the harness's own, the precondition holds, and the plan
  removes them

#### Scenario: The project's own agent is uncommitted

- **WHEN** setup runs with an untracked `.claude/agents/own.md` that neither the roster
  nor a profile renders
- **THEN** that path is reported as a conflict like any other project path

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
