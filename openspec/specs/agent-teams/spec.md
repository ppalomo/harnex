# agent-teams Specification

## Purpose
A team is the set of specialist agents a project's roster names — or, for a project that
records none, the specialists its chosen stack profiles hold fragments for: stack-agnostic
role prompts, each completed by what a chosen stack adds or rendered generically when none
does, written into the project as concrete agent files the project can read, run and own.

## Requirements

### Requirement: A profile declares its team by its files

A profile SHALL be either a single file `<profile>.md` or a directory `<profile>/`
holding `profile.md` and zero or more `<specialist>.md` fragments. Each fragment SHALL
be what that stack adds to the role of the same name, available to a project that
chose the profile and names the specialist on its roster. The set of fragments SHALL be
the profile's team only for a project that records no roster; a fragment matching no
role, matching a role whose `phase` is `apply` or `verify`, or matching a role that
ships as a plugin agent, SHALL be refused rather
than skipped. A single-file profile SHALL have no fragments and SHALL remain valid.

#### Scenario: A directory profile with three fragments

- **WHEN** a profile directory holds `profile.md`, `security-reviewer.md`,
  `migration-reviewer.md` and `api-designer.md`, the harness holds those three roles,
  and the project records no roster
- **THEN** the profile's team is those three specialists and nothing else

#### Scenario: A directory profile with three fragments, under a roster

- **WHEN** the same profile is chosen by a project whose `team` names only
  `security-reviewer`
- **THEN** only `<profile>-security-reviewer` is rendered, and the other two fragments
  add nobody

#### Scenario: A fragment for a role that ships as a plugin agent

- **WHEN** a profile directory holds `debugger.md`
- **THEN** rendering refuses, naming the fragment and saying the role ships with the
  plugin, whether or not the project records a roster

#### Scenario: An invalid fragment under a roster

- **WHEN** a chosen profile holds a fragment naming no role, and the project's roster
  does not name that fragment's specialist
- **THEN** rendering still refuses, naming the fragment, and writes nothing

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
- **THEN** it is offered and chosen exactly as before and renders no agent on its own

### Requirement: A role states its name, description, tools and phase once

Every role prompt SHALL open with a frontmatter of exactly five fields — `name`,
`description`, `tools`, `phase` and `department` — followed by its body, and `name`
SHALL equal the file's own name. `phase` SHALL be one of `apply`, `propose`, `review`
or `verify`, naming the phase the role serves: for a `review`- or `propose`-phase
role, the phase whose skill starts every agent rendered from it; for every role, the
phase of the workflow its work belongs to, whether or not a skill starts it in a given
version. `department` SHALL be one of the departments the harness names. A core role
shipped as a plugin agent SHALL carry both too (`builder` `apply`, `reviewer`
`review`, `verifier` `verify`, `test-engineer` `apply`, `debugger` `review`, all
`engineering`). A plugin agent that binds a role SHALL be the rendering of that role
without a profile — the role's `name`, `description` and `tools`, no `phase` and no
`department`, and the role's body whole — as `render_agents.py sync` writes it, so
that a role is edited once and its adapter is regenerated rather than maintained.

#### Scenario: A role file is inspected

- **WHEN** a role prompt's frontmatter is read
- **THEN** it holds exactly `name`, `description`, `tools`, `phase` and `department`,
  `name` matches the file, `phase` is one of the four and `department` one of the
  departments named

#### Scenario: A plugin agent and its role

- **WHEN** a plugin agent's frontmatter and body are compared with the role it binds
- **THEN** `name`, `description` and `tools` are identical, the agent carries neither
  `phase` nor `department`, and the bodies are identical

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
what the diff or the proposal they read says. Every rendered agent is read-only: only
`review`- and `propose`-phase roles take a fragment, so every prefixed agent is; and
only `review`- and `propose`-phase roles can be named on a roster, so every generic
agent is.

#### Scenario: A review-phase role is inspected

- **WHEN** the `tools` list of a role with `phase: review`, `phase: propose` or
  `phase: verify` is read
- **THEN** it names no editing, writing or command-execution tool

#### Scenario: A generic agent is inspected

- **WHEN** a generic agent rendered for a roster name is read
- **THEN** its `tools` are its role's, and its role's phase is `review` or `propose`

### Requirement: Rendering is a pure function of the chosen profiles

Given a project's roster and the profiles it chose, rendering SHALL produce, for every
specialist on the roster, one agent per chosen profile holding a fragment for it —
frontmatter the role's `name` prefixed with `<profile>-`, the role's `description`
followed by the profile's name, the role's `tools` unchanged; body the role's body, a
heading naming the profile, the fragment's text — and, for a specialist no chosen
profile holds a fragment for, one generic agent as the generic-rendering requirement
states. Two renderings from the same roster, the same profiles and the same harness
content SHALL be byte-identical, whatever order the names or the profiles were given
in, and SHALL carry no timestamp or version stamp.

#### Scenario: Rendering the same choices twice

- **WHEN** the same roster and profiles are rendered twice, listed in a different
  order the second time
- **THEN** every agent produced is byte-identical between the two runs

#### Scenario: A rendered agent is read

- **WHEN** the agent rendered for profile `p` and specialist `s` is read
- **THEN** its `name` is `p-s`, its `tools` are the role's, its body opens with the
  role's body and ends with the profile's fragment under a heading naming `p`

#### Scenario: A generic agent is read

- **WHEN** the agent rendered for a roster specialist `s` with no fragment is read
- **THEN** its `name` is `s`, its `description` and `tools` are the role's unchanged,
  and its body is the role's body and nothing after it

### Requirement: Rendered agents are placed where the host reads project agents

Every rendered agent SHALL be written under `.claude/agents/` in the project — at
`<profile>-<specialist>.md` when a chosen profile holds a fragment for it, at
`<specialist>.md` when it is generic — SHALL be owned by the harness by hash and listed
in the generation record, and SHALL follow the same create, unchanged, update, conflict
and adopt outcomes as every other harness-owned file. Under `local` visibility each
rendered agent SHALL be excluded from version control by its own path, never by its
directory, so that the project's own agents beside it stay tracked.

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

- **WHEN** `.claude/agents/<profile>-<specialist>.md` or a generic
  `.claude/agents/<specialist>.md` the roster renders exists, matches no recorded
  fingerprint and is not what the harness would write now
- **THEN** it is a conflict, named with the adoption path, and nothing is written

#### Scenario: A rerun before the agents are committed

- **WHEN** a `shared` setup has written its agents and runs again before they are
  committed
- **THEN** the rendered agent paths count as the harness's own under the clean-tree
  precondition, and the rerun plans nothing to do

### Requirement: An agent the harness no longer renders is removed

When a rendered agent is listed in the generation record but the recorded roster and
profiles no longer produce it, the plan SHALL remove it, provided its content still
matches its recorded fingerprint; one that was edited since SHALL be a conflict instead.
A file under `.claude/agents/` that the record never listed SHALL never be removed.

#### Scenario: A profile is dropped

- **WHEN** a profile with fragments is removed from the project's choices and setup or
  update runs again
- **THEN** every agent that profile rendered, still matching its fingerprint, is removed
  and dropped from the record — replaced by the generic agent for any roster name it
  was the only fragment for — and no other file under `.claude/agents/` changes

#### Scenario: A name is dropped from the roster

- **WHEN** a specialist is removed from both `team` and `bench` and setup or update
  runs again
- **THEN** every agent rendered for that specialist, still matching its fingerprint, is
  removed and dropped from the record

#### Scenario: A stale agent was edited

- **WHEN** an agent the record lists is no longer rendered and its content no longer
  matches its recorded fingerprint
- **THEN** the plan reports a conflict naming it, and nothing is removed or written

### Requirement: A project records its roster in two flat lists

A project's recorded choices MAY carry `team` and `bench`, each a flat list of
specialist names, in the same flat shape as every other list the choices file holds.
The two keys SHALL be present together or absent together; one without the other SHALL
be refused, naming the missing key. When both are present, the project's roster SHALL be exactly
the names they hold: a name in `team` is rendered into the project and started by the
skill of its role's phase; a name in `bench` is rendered the same way and never started
by a skill; the chosen profiles SHALL add no specialist the roster does not
name. When both are absent, the roster SHALL be every specialist the chosen profiles
hold a fragment for, all of them on the team, exactly as before the roster existed. A
name SHALL be refused, before anything is written, when it appears in both lists, when
it names no role the harness holds, when it names a role whose phase is `apply` or
`verify`, or when it names a role that ships as a plugin agent — those are in every
project already.

#### Scenario: Both lists recorded

- **WHEN** a project's choices record `team` naming `security-reviewer` and `bench`
  naming `migration-reviewer`, and its profiles hold a fragment for `api-designer` too
- **THEN** the roster is those two names, the API designer is not rendered, the
  security reviewer is started by `review`, and the migration reviewer is rendered but
  never started by a skill

#### Scenario: Neither list recorded

- **WHEN** a project's choices carry neither key and its chosen profile holds three
  fragments
- **THEN** the roster is those three specialists, all on the team, and the project
  behaves exactly as it did before this requirement

#### Scenario: One list without the other

- **WHEN** a project's choices carry `team` and not `bench`, or the reverse
- **THEN** reading the choices refuses, naming the missing key, and nothing is
  rendered or written; setup and update name the file too, and a skill names the file
  it read alongside the listing's refusal

#### Scenario: A name in both lists

- **WHEN** the same specialist is named in `team` and in `bench`
- **THEN** reading the choices refuses, naming the specialist and listing the
  specialists the harness holds

#### Scenario: A name the roster cannot hold

- **WHEN** a list names a role the harness does not hold, an `apply`- or `verify`-phase
  role, or a role that ships as a plugin agent
- **THEN** reading the choices refuses, names the entry, says why, and lists the
  specialists the harness does hold — with the same message whether the roster reaches
  the harness through setup, through update, or through the listing a skill asks for

### Requirement: A specialist without a fragment renders generically

For every name on the roster, rendering SHALL produce one agent per chosen profile
holding a fragment for that specialist, named `<profile>-<specialist>`, and — when no
chosen profile holds one — exactly one agent named `<specialist>`, at
`.claude/agents/<specialist>.md`, whose frontmatter is the role's `name`,
`description` and `tools` unchanged and whose body is the role's body with no stack
section. A generic agent SHALL be owned, placed, excluded under `local` visibility,
refreshed and removed exactly as a prefixed one.

#### Scenario: A specialist with no fragment among the chosen profiles

- **WHEN** a project's `team` names `security-reviewer` and none of its chosen profiles
  holds a `security-reviewer.md` fragment
- **THEN** `.claude/agents/security-reviewer.md` is rendered from the role alone, with
  the role's own `name`, `description` and `tools`, and no `## For this stack` section

#### Scenario: A specialist with a fragment in one chosen profile

- **WHEN** a project's `team` names `security-reviewer` and exactly one chosen profile
  holds a fragment for it
- **THEN** only the prefixed agent is rendered, and no generic one

#### Scenario: A profile is dropped under a roster

- **WHEN** the only chosen profile holding a fragment for a roster name is dropped and
  setup or update runs
- **THEN** the prefixed agent is removed and the generic agent takes its place

### Requirement: A role declares its department

Every role prompt's frontmatter SHALL carry a `department` field naming the group the
role belongs to, `engineering` or `design` in this version, and a value outside that
set SHALL be refused by name. The field SHALL be dropped from every rendered agent and
every plugin adapter, like `phase`. Setup's offer of the specialists a roster may
name SHALL group them by department and show each as the role's emoji, one space, and
its name. The listing the skills use to start agents SHALL NOT carry the department,
since which agents a phase starts does not depend on it.

#### Scenario: A role file is inspected

- **WHEN** a role prompt's frontmatter is read
- **THEN** `department` is present and is one of the departments the harness names

#### Scenario: A rendered agent is read

- **WHEN** an agent rendered from a role, generic or prefixed, or a plugin adapter is
  read
- **THEN** its frontmatter carries no `department` field

#### Scenario: The specialists are offered

- **WHEN** setup offers the specialists a project may put on its roster
- **THEN** they are grouped by department, `designer` and `accessibility-reviewer`
  under `design` and every other specialist under `engineering`, each as
  `<emoji> <name>` with its phase

### Requirement: The listing names a phase's team and never its bench

The renderer's listing, given the project's roster and profiles and a phase, SHALL
print one line per agent on the team whose role serves that phase — the agent's emoji,
one space, and its `name` — and SHALL NOT print an agent on the bench, whatever its
phase. For a project without a roster it SHALL print what it printed before the roster
existed: every rendered agent of that phase.

#### Scenario: A team and a bench

- **WHEN** the listing is asked for `review` in a project whose `team` names
  `security-reviewer` and whose `bench` names `migration-reviewer`
- **THEN** it prints the security reviewer's line and no line for the migration
  reviewer

#### Scenario: No roster

- **WHEN** the listing is asked for a phase in a project whose choices carry no roster
- **THEN** it prints every agent of that phase the chosen profiles render
