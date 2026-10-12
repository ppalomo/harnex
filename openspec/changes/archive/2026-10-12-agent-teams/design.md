## Context

See `proposal.md` for why. What shapes the approach:

- `available_profiles()` already accepts a profile directory or a flat `.md`; `ui.json`
  already gates one MCP entry on a profile; `render_rules.py` already renders a
  profile-scoped rule only for a project that chose it. The profile is already the axis
  on which a project's behaviour varies by stack, so the team hangs from it.
- A plugin agent is installed once per machine and cannot be chosen per project; a
  project-level agent under `.claude/agents/` can, and the host reads it by its `name`.
  A harness-owned file in a project is a rendering, owned by hash, written by `setup`,
  refreshed by `update`, with conflict and adoption outcomes already specified
  (`harness-ownership`). `.claude/` is already a directory `setup` writes into
  (`.claude/settings.json`).
- A subagent cannot start a subagent (verified against the Claude Code docs). The main
  session, through the skills, is the only orchestrator — which is what `docs/PLAN.md`
  §4 already says.
- The host gives an agent's body no import syntax, so every agent file carries the
  whole body of what it binds; D8 makes the plugin's own adapters a rendering of their
  roles, and `tests/test_agent_and_skill_frontmatter.py` checks that rendering is current.
- The layout test admits only the five pillar directories and the host's own at the
  plugin root; a `teams/` directory would fail it, and would be a component in two
  pillars.

## Goals / Non-Goals

**Goals:**

- A project chooses a profile and gets that profile's team, as files it can read, as a
  pure function of its choices, with nothing new to answer.
- Adding a stack costs a profile directory and its fragments. Adding a specialist costs
  one role file, and reaches every profile that writes a fragment for it.
- Every rendered agent's write boundary is held by the same mechanism that holds the
  core reviewer: its declared `tools`.

**Non-Goals:**

- A team roster separate from the profile's own files; a team that spans profiles; a
  runtime notion of "team" at all. The word names what a profile directory renders.
- Any change to the manifest format, the answers keys, `render_rules.py`, the guard, the
  floor or the decision questions.
- A persona that varies by stack or by project, or that says anything about voice: the
  character belongs to the role file, and a fragment never restates or alters it.

## Decisions

### D1 · The team is the profile directory; there is no `teams/` and no `team.yml`

Options considered:

- **A `plugin/teams/<team>/team.yml` catalogue** naming a stack and a roster. Rejected:
  a new root directory (fails the layout test, and belongs to two pillars), a roster
  that can name a fragment that does not exist, and a new `.harnex.yml` key for the
  person to answer — reopening decision 11 for nothing the profile cannot already say.
- **Specialists composed at run time** by the skills, from role plus profile text, with
  no file in the project. Rejected: invisible to the project, impossible to inspect or
  pin, and the host needs a file to start an agent by name anyway.
- **The profile directory is the team.** `profile.md` is the stack; each
  `<specialist>.md` beside it is the stack's addition to that role, and its presence is
  the roster. Chosen. Roster and content cannot disagree, a profile is still one
  component in pillar 2, and `.harnex.yml` is unchanged: choosing `rails` is importing
  the rails team.

A fragment that matches no role is refused, not skipped, so a typo in a file name cannot
silently drop a specialist from every project that chose the profile.

### D2 · Roles gain a frontmatter; the rendered agent is role plus fragment

A rendered agent needs a `name`, a `description` and a `tools` list, and the skill that
starts it needs to know in which phase. Today those live only in the plugin agent's
frontmatter, which a stack-only role (`security-reviewer`) does not have. So every role
file opens with exactly `name`, `description`, `tools`, `phase`. The plugin adapter copies
the first three and the body, and drops `phase` — the adapter test keeps asserting the
minimum agent frontmatter, and now also asserts the copied fields match. The three
existing roles gain the frontmatter and, with D7, the persona section; their adapters
follow, since D8 regenerates them from the roles.

The body ends where the fragment begins: rendering appends `## For this stack: <profile>`
and the fragment's text. A role that needs stack knowledge in the middle of its procedure
says "the stack section below" — the slot is positional, not a template token, so a role
file is readable as prose and the renderer stays a concatenation.

`phase` takes four values, one per workflow phase that has a role: `apply` (`builder`,
`test-engineer`), `propose` (`designer`, `api-designer`), `review` (`reviewer`,
`debugger`, the three stack reviewers) and `verify` (`verifier`). For the two phases
that render stack agents it is the playbook: `review`-phase agents are started by
`/harnex:review`, `propose`-phase agents by `/harnex:propose`. For the others it says
where the role belongs, not who calls it: `apply` keeps starting the builder alone, and
`verify` and `propose` keep starting the verifier as today. Only a `review`- or
`propose`-phase role takes a fragment — the renderer refuses one for an `apply`- or
`verify`-phase role — so every rendered agent is read-only, and no `<profile>-builder`
or `<profile>-test-engineer` can ever appear with `Edit`, `Write` or `Bash`. The skills
read the phase from the role file in the plugin, not from the rendered agent, since the
plugin is where the harness's own content lives.

The two new core agents have no caller among the skills in this change: the person
starts `debugger` or `test-engineer` by name, the way any project agent is started. The
verifier's `phase: verify` is honest about where it belongs even though `propose` also
starts it for the design review; a role carries one phase, and `verify` is the one that
binds its result.

### D3 · Rendering, placement, ownership, removal

`plugin/scripts/render_agents.py` (pillar 3, kept in `scripts/` like every script) takes
the chosen profiles and the plugin root and returns `{path: bytes}` for every agent,
sorted by path; `setup.py` adds that map to `desired` next to `.harnex/rules.md`, so
every outcome `_plan_harness_files` already produces — create, unchanged, update,
conflict, adopt — applies unchanged, and `_plan_record` lists each agent by hash. Standard
library only (decision 15).

The clean-tree precondition (`C9`) exempts the harness's own paths through an enumerated
list, `HARNESS_OWN_PATHS`, plus the `.harnex/` prefix. The rendered agent paths join
that exemption — each path individually, computed from the answers' profiles for `setup`
and from the record's listed paths as well, so a stale agent awaiting removal does not
block the rerun that removes it. The directory `.claude/agents/` is not exempted: the
project's own agents are the project's, and an untracked one is a conflict like any
other project path. Without this, the first `shared` rerun before a commit would refuse
on the agents setup itself had just written, breaking "Running setup again changes
nothing" and "An interrupted setup completes on the next run".

Removal is new. A path in the record under `.claude/agents/` that is not in `desired` is
planned as `remove` when the file on disk still matches its recorded fingerprint, and as
a conflict otherwise; a path the record never listed is never touched. This is the one
place the harness deletes a file, and it is inside the plan the person approves — the
`safety` set's "ask before deleting" holds through that same yes, and under `update`
through setup's earlier yes, the same way every other update write does.

Under `local` visibility each agent path joins `GIT_EXCLUDE_PATHS` individually. The
alternative, excluding `.claude/agents/`, would hide the project's own agents from git.
A removed agent's exclude entry is left in place, like `.env`'s: the exclude list is the
clone's, and a stale entry matches nothing.

### D4 · `review` fans out and shows everything; `propose` consults and writes itself

`review` starts the core reviewer first, then every `review`-phase agent of the chosen
profiles, each once, each with the same diff. Reviews are shown as returned, labelled —
no merging, because merging is a judgement the skill is not allowed to make on a
reviewer's behalf (`review-command`'s existing "exactly as returned"). A duplicate
finding across two reviewers is information: two readers found it.

`propose`-phase agents are advisors, read-only, started with the proposal before
`design.md` is written. The architect — the main session — writes `design.md` from their
briefs, naming the advisor a section comes from. The alternative, letting `designer`
write `design.md` itself, would put two writers on one artifact and need an `Edit` tool
on a role that reads a proposal that may contain anything. Rejected.

### D5 · The core team grows by two, held differently

`debugger` is read-only (`Read, Grep, Glob`): prevention by `tools`, like the reviewer.
`test-engineer` writes (`Read, Grep, Glob, Edit, Write, Bash`): its "tests only" boundary
is instruction only in this change, exactly as the builder's is outside the apply loop.
Neither is started by a skill in this change — `review` fans out to rendered stack
agents only, `apply` routes to the builder only — so both are for the person to start by
name. Pairing `test-engineer` with the builder inside the loop, where `task_scope_check`
could hold it, and giving `debugger` a place in `apply`'s escalation, are later changes;
the role files and `docs/PLAN.md` §4 say so. `test-engineer` cannot be rendered per
profile (D2), so its writing tools never reach a stack agent. `debugger` can: it is a
`review`-phase role, so a profile that carries a `debugger.md` fragment renders
`<profile>-debugger` and `/harnex:review` starts it like any other stack reviewer. None
of the three profiles in this change does; the core `debugger` itself stays the
person's to start.

### D6 · `flutter` is a UI profile that is not in `ui.json`

`ui.json` means "Playwright applies". It does not for Flutter, so the profile is left out
and `profile.md` states what evidence `verify` can expect instead (the project's own
widget and integration tests, named in `AGENTS.md`). `accessibility-reviewer` reads the
diff only, in `review`; a step against a running app is a non-goal.

### D7 · A persona is five lines drawn from the role's own constraints

The imported collections give every agent a name, an emoji, an "Identity & Memory" and
character traits. Two of those are worth having: a name and an emoji make ten reviewers
distinguishable in a listing and in `review`'s labelled output, where `security-reviewer`
and `rails-security-reviewer` otherwise read as the same thing. The other two are where
results get worse: a backstory costs tokens at every start and changes nothing, and a
"decided" or "confident" personality makes a model present a hunch as a certainty —
the exact opposite of what every reviewing role here demands.

So the persona is a property of the role, never a reason for one, and it is bounded by
shape and by source:

- **Shape.** The skeleton's opening paragraph — "who you are, the one constraint that
  defines you" — stays under the title untouched; `## Who you are` is the first `##`
  heading after it, and the section is a single paragraph of at most five physical
  lines, the heading and blank lines not counted. Its first line opens with one emoji —
  a single code point of Unicode category `So`, so no joiner or variation-selector
  sequence — then exactly one space, then a bold given name. The same code point opens
  the `description`, again followed by exactly one space, since that is what a listing
  and the `Agent` tool show. One space, never two and never none, is the rule wherever
  emoji and name meet: here, in `list`'s output and in `review`'s labels. The test reads
  the shape with the standard library alone: the first `##` heading of the body, the
  paragraph's line count, the first code point's category and its equality with the
  description's first code point, and name and emoji unique across every role.
- **Source.** Up to three traits, each a disposition stated as how it shows in the work
  ("you say 'I am not sure' before you say 'this is wrong'"), and each traceable to a
  line of the role's own "What you must not do" or "How to report". A trait never claims
  confidence, seniority, speed or breadth. Every `review`- and `verify`-phase role lists
  saying when it is unsure among its traits, so the persona restates the uncertainty
  rule rather than competing with it; the test checks only that such a trait is present,
  by the words it uses ("not sure", "suspected", "unsure", "uncertain"). No test reads a
  trait's sense: the verifier does,
  against this decision — the reviewer judges code quality, never a design decision.
- **Names.** A given name that belongs to nobody — not a real or famous person, not a
  colleague, not a project — and no two roles share one. The body keeps addressing the
  agent as "you"; the name is how the person refers to it, not how it refers to itself.
- **Rendering.** The body is copied whole, so every rendered agent carries its role's
  persona unchanged and a profile cannot add, drop or alter it. The five plugin adapters
  carry it because `sync` (D8) renders them from the role.

`review` labels each returned review with the agent's emoji and its `name` field
(`🔍 rails-security-reviewer`), which is the one place the persona is used for anything
beyond reading. The emoji comes from `render_agents.py list`, which prints each agent's
`name` with the first code point of its rendered `description`; the skill never parses an
agent's body.

### D8 · The plugin's adapters are rendered by `sync`, so a role is written once

Checked against the current Claude Code docs: the `@path/to/file` import is a feature of
`CLAUDE.md` and `AGENTS.md` alone; a subagent's body and a `SKILL.md` body have no
include mechanism. The one documented way to put external text into an agent is the
`skills` frontmatter field, which preloads whole skills at start — rejected: it adds a
field beyond decision 9's minimum, turns a role into a skill, requires a project's
rendered agent to name a plugin skill, and loads the same text anyway.

So `plugin/agents/<role>.md` must hold the role's text, and the duplication to remove is
the maintenance, not the file. `render_agents.py sync [--plugin-root P] [--check]`
rewrites every adapter already present under `plugin/agents/` from the role of the same
name under `orchestration/roles/`, through the same code path that renders a project's
agents minus the profile: `name`, `description`, `tools` copied, `phase` dropped, the
body whole, byte-stable. `--check` writes nothing and exits non-zero naming each adapter
that differs; the correspondence test asserts exactly that, so an edited role with a
stale adapter fails the suite, and a hand-edited adapter fails it the same way. An
adapter whose role does not exist is refused by name. The set of core agents stays the
set of files under `plugin/agents/` — no list in the script — and a new one is added by
creating the empty file and running `sync`.

Rejected alternatives: ten adapters, one per role (would ship the stack specialists as
plugin agents, which D1 says they are not); a list of core roles in the script (a second
statement of what the directory already says).

## What setup and update write, and who owns each path

| Path | Owner | Written by | Visibility |
|---|---|---|---|
| `.claude/agents/<profile>-<specialist>.md`, one per fragment of each chosen profile | harness, by hash, listed in `.harnex/manifest.json` | setup (after the yes), update (asking nothing) | both; under `local` also excluded by its own path in `.git/info/exclude` |
| `.harnex/manifest.json` | harness | setup, update | both — gains one entry per agent |
| `.git/info/exclude` | local (this clone) | setup, update | `local` only — one entry per agent path |

Nothing else changes. `.harnex.yml` is not touched: `profiles` already holds the answer.
A project's own files under `.claude/agents/` are never read for content, never written
and never removed.

## Guarantees, by kind

| Guarantee | Kind | When the component fails |
|---|---|---|
| A stack reviewer or advisor cannot write | **P** — the role's `tools`, copied verbatim into the rendered agent; a test reads every `review`/`propose`-phase role's list | if the host ignored `tools`, the prompt still says so (I); nothing detects it after the fact |
| A plugin adapter is exactly its role minus `phase` | **D** — `render_agents.py sync --check`, run by the correspondence test | an edited role or a hand-edited adapter fails the suite before release, naming the adapter |
| A rendered agent is exactly role plus fragment, byte-stable | **D** — the record's hash; `update` rewrites on drift | if the renderer errs, the test comparing a rendered agent to its sources fails before release |
| A hand-edited agent is never overwritten | **P** — `_plan_harness_files` reports a conflict and `write` refuses, as today | a missing record is the existing "no record, never guessed" refusal |
| Only agents the harness wrote are removed | **P** — removal requires a recorded fingerprint that still matches | with no record, nothing is removed; a mismatch is a conflict, not a removal |
| `test-engineer` writes tests only | **I** only | nothing stops it in this change; stated in its role and in `docs/PLAN.md` §4 |
| `review` starts each stack reviewer once, shows each review whole | **I** — the skill's own steps | the skill-content tests assert the wording; a missed agent is reported, not silent (`review-command`) |
| A fragment with no matching role never silently vanishes | **P** — the renderer refuses, setup plans nothing | the refusal is an ordinary `SetupError`, shown like any other |
| No rendered agent can write | **P** — the renderer refuses a fragment for an `apply`- or `verify`-phase role, and every `review`/`propose`/`verify`-phase role's `tools` list is read-only, both tested | a role with a wrong `phase` or `tools` fails the tests before release; a stray fragment is a `SetupError` |
| A persona cannot make a role surer than its evidence | **I** — the section is five lines and its traits are drawn from the role's own report rules; shape and uniqueness are tested | a trait that claims certainty or contradicts the role is caught by the verifier reading against D7, not by a test |
| A rerun before the first commit still plans | **D** — the precondition's exemption lists each rendered agent path; a test reruns setup on an uncommitted tree | if the exemption misses a path, setup reports it as a conflict naming the path, writing nothing — loud, not silent |

## Risks / Trade-offs

- [A stack reviewer reading a hostile diff is prompt-injected] → it cannot write (P); its
  review is read by a person, and `review` blocks nothing.
- [Three stack reviewers per profile make `review` slow and costly] → each starts once,
  in parallel where the host allows; a project that wants fewer drops the profile or
  waits for a per-specialist opt-out (non-goal here).
- [A role prompt changes and every project's agents drift] → that is what `update` is
  for; the record detects it and the hash makes the rewrite safe.
- [Two advisors disagree in `propose`] → the architect decides, as for any input, and
  names both in `design.md`.
- [A persona drifts into a personality] → the shape test caps it at five lines and the
  review checks every trait against the role's own constraints; a line about voice, mood
  or memory is a finding, not a style choice.
- [`fastapi.md` becomes `fastapi/profile.md`] → `available_profiles()` reports the same
  name; a project that recorded `fastapi` sees only new `.claude/agents/` lines on its
  next `update`.

## Migration Plan

1. Land the roles' frontmatter and the renderer with no profile directory yet: every
   existing project updates to nothing new.
2. Move `fastapi.md` into `fastapi/profile.md` and add the three profile directories.
   A project that chose `fastapi` gains three agents on its next `/harnex:update`,
   shown in the plan; one that chose none gains nothing.
3. Rollback is removing the fragments: the next `update` plans the agents' removal,
   since they still match their fingerprints.

## Open Questions

- Which model the host picks for a rendered agent without a `model` field, and whether
  a stack reviewer should one day pin one the way `reviewer` does. Deferrable: it changes
  no spec, no path and no task here.
