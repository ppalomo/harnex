## Purpose

A team is the set of specialist agents a stack profile brings to a project: stack-agnostic
role prompts, each completed by what that stack adds, rendered into the project as
concrete agent files the project can read, run and own.

## ADDED Requirements

### Requirement: A profile declares its team by its files

A profile SHALL be either a single file `<profile>.md` or a directory `<profile>/`
holding `profile.md` and zero or more `<specialist>.md` fragments. The profile's team
SHALL be exactly the set of fragments whose name matches a role the harness holds whose
`phase` is `review` or `propose`; a fragment matching no role, or matching a role whose
`phase` is `apply` or `verify`, SHALL be refused rather than skipped. A single-file
profile SHALL have no team and SHALL remain valid.

#### Scenario: A directory profile with three fragments

- **WHEN** a profile directory holds `profile.md`, `security-reviewer.md`,
  `migration-reviewer.md` and `api-designer.md`, and the harness holds those three roles
- **THEN** the profile's team is those three specialists and nothing else

#### Scenario: A fragment names no role

- **WHEN** a profile directory holds a fragment whose name matches no role the harness
  holds
- **THEN** rendering refuses with the fragment's path and the roles held, and writes
  nothing

#### Scenario: A fragment names a writing or verifying role

- **WHEN** a profile directory holds `test-engineer.md`, `builder.md` or `verifier.md`
- **THEN** rendering refuses, naming the fragment and saying that only a `review`- or
  `propose`-phase role takes a fragment, and writes nothing

#### Scenario: A single-file profile

- **WHEN** a profile is a single `<profile>.md` file
- **THEN** it is offered and chosen exactly as before and renders no agent

### Requirement: A role states its name, description, tools and phase once

Every role prompt SHALL open with a frontmatter of exactly four fields — `name`,
`description`, `tools` and `phase` — followed by its body, and `name` SHALL equal the
file's own name. `phase` SHALL be one of `apply`, `propose`, `review` or `verify`,
naming the phase the role serves: for a `review`- or `propose`-phase role, the phase
whose skill starts every agent rendered from it; for every role, the phase of the
workflow its work belongs to, whether or not a skill starts it in a given version. A
core role shipped as a plugin agent SHALL carry it too (`builder` `apply`, `reviewer`
`review`, `verifier` `verify`, `test-engineer` `apply`, `debugger` `review`). A plugin
agent that binds a role SHALL be the rendering of that role without a profile — the
role's `name`, `description` and `tools`, no `phase`, and the role's body whole — as
`render_agents.py sync` writes it, so that a role is edited once and its adapter is
regenerated rather than maintained.

#### Scenario: A role file is inspected

- **WHEN** a role prompt's frontmatter is read
- **THEN** it holds exactly `name`, `description`, `tools` and `phase`, `name` matches
  the file, and `phase` is one of the four

#### Scenario: A plugin agent and its role

- **WHEN** a plugin agent's frontmatter and body are compared with the role it binds
- **THEN** `name`, `description` and `tools` are identical, the agent carries no `phase`
  field, and the bodies are identical

#### Scenario: Syncing the adapters

- **WHEN** `render_agents.py sync --check` runs against the plugin
- **THEN** it exits zero when every adapter under `plugin/agents/` equals the rendering
  of its role, and otherwise exits non-zero naming each adapter that differs; without
  `--check` it rewrites each differing adapter and names it; an adapter with no role of
  its name is refused by name

### Requirement: A role carries a persona that serves its constraints

Every role prompt's body SHALL keep its opening paragraph under the title, and its first
`##` section SHALL be `## Who you are`: a single paragraph of at most five physical
lines (heading and blank lines not counted), whose first line begins with one emoji — a
single code point of Unicode category `So` — then exactly one space, then a given name
in bold, and which
states up to three traits, each as how it shows in the work and each drawn from the
role's own "What you must not do" or "How to report". The role's `description` SHALL
begin with that same code point followed by exactly one space. Wherever the harness
prints an agent's emoji and name together — the `list` output, a review's label — the
two SHALL be separated by exactly one space. No two roles SHALL share a name or an emoji, and a name
SHALL NOT be a famous person's, a colleague's or a project's. A trait SHALL NOT claim
confidence, seniority, speed or breadth, and SHALL NOT describe voice, mood or memory;
every role whose `phase` is `review` or `verify` SHALL list saying when it is unsure
among its traits. A rendered agent and a plugin adapter SHALL carry the section exactly
as the role states it.

#### Scenario: A role's persona is inspected

- **WHEN** a role prompt's body is read
- **THEN** its first `##` heading is `## Who you are`, the paragraph under it is at most
  five lines, its first code point is of category `So` and equals the first code point
  of the role's `description`, exactly one space then a bold name follow it (and exactly
  one space follows it in the `description`), and no other role uses that name or that
  code point

#### Scenario: A rendered agent is read

- **WHEN** an agent rendered from a role and a fragment is read
- **THEN** its `## Who you are` section is identical to the role's, and the fragment
  adds nothing to it

#### Scenario: A trait is reviewed

- **WHEN** the verifier reads a role's traits against the role's own "What you must not
  do" and "How to report"
- **THEN** a trait that claims certainty, seniority, speed or breadth, describes voice,
  mood or memory, or cannot be traced to one of those lines is reported as a finding

### Requirement: A role that only reads declares no writing tool

Every role whose `phase` is `review`, `propose` or `verify` SHALL declare a `tools`
list with no file-editing, file-writing or command-execution capability, so that the
agents rendered from it — and the core agents bound to it — cannot write regardless of
what the diff or the proposal they read says. Since only `review`- and `propose`-phase
roles take a fragment, every rendered agent is read-only.

#### Scenario: A review-phase role is inspected

- **WHEN** the `tools` list of a role with `phase: review`, `phase: propose` or
  `phase: verify` is read
- **THEN** it names no editing, writing or command-execution tool

### Requirement: Rendering is a pure function of the chosen profiles

Given the profiles a project chose, rendering SHALL produce, for every chosen profile
with a team and every specialist in it, one agent whose frontmatter is the role's
`name` prefixed with `<profile>-`, the role's `description` followed by the profile's
name, and the role's `tools` unchanged; and whose body is the role's body followed by a
heading naming the profile and the fragment's text. Two renderings from the same
profiles and the same harness content SHALL be byte-identical, whatever order the
profiles were given in, and SHALL carry no timestamp or version stamp.

#### Scenario: Rendering the same choices twice

- **WHEN** the same profiles are rendered twice, listed in a different order the second
  time
- **THEN** every agent produced is byte-identical between the two runs

#### Scenario: A rendered agent is read

- **WHEN** the agent rendered for profile `p` and specialist `s` is read
- **THEN** its `name` is `p-s`, its `tools` are the role's, its body opens with the
  role's body and ends with the profile's fragment under a heading naming `p`

### Requirement: Rendered agents are placed where the host reads project agents

Every rendered agent SHALL be written at `.claude/agents/<profile>-<specialist>.md` in
the project, SHALL be owned by the harness by hash and listed in the generation record,
and SHALL follow the same create, unchanged, update, conflict and adopt outcomes as
every other harness-owned file. Under `local` visibility each rendered agent SHALL be
excluded from version control by its own path, never by its directory, so that the
project's own agents beside it stay tracked.

#### Scenario: Shared visibility

- **WHEN** a project under `shared` visibility is set up with a profile that has a team
- **THEN** each of its agents is written under `.claude/agents/`, listed in the record,
  and is part of what the project commits

#### Scenario: Local visibility beside the project's own agents

- **WHEN** a project under `local` visibility already tracks `.claude/agents/own.md` and
  is set up with a profile that has a team
- **THEN** each rendered agent is excluded through its own entry in `.git/info/exclude`,
  and `own.md` is neither excluded nor touched

#### Scenario: A present agent the harness did not write

- **WHEN** `.claude/agents/<profile>-<specialist>.md` exists, matches no recorded
  fingerprint and is not what the harness would write now
- **THEN** it is a conflict, named with the adoption path, and nothing is written

#### Scenario: A rerun before the agents are committed

- **WHEN** a `shared` setup has written its agents and runs again before they are
  committed
- **THEN** the rendered agent paths count as the harness's own under the clean-tree
  precondition, and the rerun plans nothing to do

### Requirement: An agent the harness no longer renders is removed

When a rendered agent is listed in the generation record but the chosen profiles no
longer produce it, the plan SHALL remove it, provided its content still matches its
recorded fingerprint; one that was edited since SHALL be a conflict instead. A file under
`.claude/agents/` that the record never listed SHALL never be removed.

#### Scenario: A profile is dropped

- **WHEN** a profile with a team is removed from the project's choices and setup or
  update runs again
- **THEN** every agent that profile rendered, still matching its fingerprint, is removed
  and dropped from the record, and no other file under `.claude/agents/` changes

#### Scenario: A stale agent was edited

- **WHEN** an agent the record lists is no longer rendered and its content no longer
  matches its recorded fingerprint
- **THEN** the plan reports a conflict naming it, and nothing is removed or written
