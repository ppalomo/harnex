## ADDED Requirements

### Requirement: The plan includes the chosen profiles' agents

For every chosen profile that has a team, setup's plan SHALL include one line per
rendered agent under `.claude/agents/`, with the same outcomes as any other
harness-owned path — create, unchanged, update, conflict or adopt — and one line per
agent the record lists but the choices no longer produce, marked for removal or as a
conflict. The choices setup offers SHALL say, for each profile, which specialists its team
brings, so the person knows what choosing it imports.

#### Scenario: A profile with a team is chosen

- **WHEN** setup plans for a project that chose a profile with three specialists
- **THEN** three `.claude/agents/` lines appear in the plan, one per agent, each with
  its action, and the write produces those three files and records them

#### Scenario: A profile without a team is chosen

- **WHEN** setup plans for a project whose only chosen profile is a single-file profile
- **THEN** no `.claude/agents/` line appears and nothing is written there

#### Scenario: Under local visibility

- **WHEN** setup plans for a `local` visibility project that chose a profile with a team
- **THEN** each rendered agent is planned under `.claude/agents/` and its own path is
  planned into `.git/info/exclude`, with no entry for the directory itself

## MODIFIED Requirements

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
`.claude/agents/<profile>-<specialist>.md` that the chosen profiles produce or that the
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

- **WHEN** a `shared` setup that chose a profile with a team has written its agents
  under `.claude/agents/` and is run again before they are committed
- **THEN** those agent paths count as the harness's own, the precondition holds, and
  the rerun plans nothing to do

#### Scenario: A stale agent before the run that removes it

- **WHEN** a profile with a team was dropped from the choices, its agents are listed in
  the record and still uncommitted, and setup runs again
- **THEN** those paths count as the harness's own, the precondition holds, and the plan
  removes them

#### Scenario: The project's own agent is uncommitted

- **WHEN** setup runs with an untracked `.claude/agents/own.md` that no profile renders
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
