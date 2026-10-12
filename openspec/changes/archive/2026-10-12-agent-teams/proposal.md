**Pillars:** 3 · Orchestration (the specialist roles, their phase, and the rendering
that turns a profile's team into a project's own agents; the `review` and `propose`
skills' fan-out) and 2 · Action & Tools (the `rails`, `fastapi` and `flutter` profiles,
which now carry what each stack adds to a specialist; the `setup` and `update` skills).
No `control/` or `feedback/` change: every new boundary is held by the mechanisms that
already exist.

**Phase:** `docs/PLAN.md` has no slot for this; it is the first phase after `C9`. Call it
**`C10 · agent teams`**. Exit criterion: a project that chose the `rails`, `fastapi` or
`flutter` profile finds, after `/harnex:setup`, one Claude Code agent per specialist of
that profile's team under `.claude/agents/`, named `<profile>-<specialist>`, owned by the
harness by hash; `/harnex:review` starts every reviewer of the project's teams alongside
the core `reviewer` and shows each review as returned, labelled with the agent's emoji
and `name`; `/harnex:propose` consults every
advisor of the project's teams before `design.md` is written; `/harnex:update` refreshes
the agents when the harness's own content changes; and a profile dropped from
`.harnex.yml` takes its agents with it on the next run — all tried by hand on a scratch
project, with every rule the plugin already enforces still holding.

## Why

What a project receives from harnex today is a rules file, five commands and three
agents, the same three for every project whatever its stack. The agents are installed
once per machine, so a project cannot choose them, and nothing in the harness knows
what a security review of a Rails app or a migration review of an Alembic history
actually looks at. The collections people do import — hundreds of named personas,
organised like a company — give breadth at the cost of everything harnex is for: no
write boundary, no enforcement, a technology named in every file.

Three things justify an agent of its own, and only three: a context of its own, a
restricted tool list, and knowledge worth loading only when it applies. A stack-aware
specialist passes all three. A persona passes none: it is never the reason for an agent.
It can still be a property of a role. A name, an emoji and a few traits let ten
reviewers be told apart in a listing and in a report, and a trait chosen from the role's
own constraints — "says when unsure", for a reviewer — reinforces the prompt instead of
fighting it. What the imported collections get wrong is not the persona but what they
put in it: an "Identity & Memory" backstory, a decided personality that presents a hunch
as a certainty, and a hundred lines that cost tokens at every start without changing the
result.

## What Changes

- **A profile declares a team.** A profile may be a directory: `profile.md` is what
  today's flat file holds, and each further `<specialist>.md` in it is what that stack
  adds to one specialist role. The set of such files is the profile's roster. A flat
  profile (`react.md` today) stays valid and simply has no team. Choosing a profile in
  `.harnex.yml` imports its team; there is no new answer key.
- **Specialist roles, stack-agnostic, in `orchestration/roles/`.** Seven new role prompts
  written to the existing skeleton, each with a stack slot its fragment fills and a
  frontmatter stating `name`, `description`, `tools` and the `phase` the role serves
  (`apply`, `propose`, `review` or `verify`): `test-engineer` (`apply`) and `debugger`
  (`review`) join the core team, shipped as plugin agents like `builder`, `reviewer`
  and `verifier`, and in this change are started by the person directly — no skill
  calls either; `security-reviewer`, `migration-reviewer`, `accessibility-reviewer`
  (phase `review`, read-only); `api-designer` and `designer` (phase `propose`,
  read-only advisors whose brief the architect folds into `design.md`). Only a
  `review`- or `propose`-phase role may receive a profile fragment, so every rendered
  agent is read-only; a fragment for an `apply`- or `verify`-phase role is refused.
  The three existing roles gain the same frontmatter (`builder` `apply`, `reviewer`
  `review`, `verifier` `verify`); their adapters' bodies stay exact copies.
- **The plugin's own adapters are generated, not written.** The host gives an agent's
  body no import syntax (verified again against the current docs: `@path` imports exist
  for `CLAUDE.md` and `AGENTS.md` only, and neither the subagent page nor the skills
  page offers an include), so `plugin/agents/<role>.md` has to hold the role's text. It
  holds it as a build artifact: `render_agents.py sync` writes every adapter under
  `plugin/agents/` from the role of the same name — the role's `name`, `description`
  and `tools`, `phase` dropped, the body whole — and the correspondence test becomes
  "sync would change nothing". A role is edited once; the adapter is regenerated, never
  hand-edited. Which roles ship as plugin agents is still the set of files under
  `plugin/agents/`: a new core agent is an empty file there, filled by `sync`.
- **Every role has a persona that serves its constraints.** The skeleton's opening
  paragraph (the role's defining constraint) stays where it is; the first `##` section
  after it is `## Who you are`, a single paragraph of at most five lines: one emoji, one
  given name in bold, and up to three traits, each stated as how it shows in the work
  and each drawn from the role's own "What you must not do" or "How to report". A trait
  never claims confidence, seniority, speed or breadth; every `review`- and
  `verify`-phase role's traits include saying when it is unsure. The same emoji opens
  the role's `description`, so a listing shows it. Names and emojis are unique across
  roles, and a name is not a famous person's, a colleague's or a project's. A rendered
  agent carries the persona unchanged: the stack changes the section that follows the
  body, never the character, so `rails-security-reviewer` and
  `fastapi-security-reviewer` are the same reviewer on a different stack. The shape is
  tested; whether a trait makes sense is the verifier's to judge, against the design.
- **Three profiles with teams.** `rails` (new) and `fastapi` (moved into a directory)
  each carry `security-reviewer`, `migration-reviewer` and `api-designer`; `flutter`
  (new) carries `designer`, `accessibility-reviewer` and `security-reviewer`. `flutter`
  is not added to `ui.json`: the browser step `verify` runs for a UI profile does not
  apply to it, and the profile says so.
- **Rendering, as a pure function of the chosen profiles.** A new
  `plugin/scripts/render_agents.py` composes, for every chosen profile with a team and
  every fragment in it, one agent file: the role's frontmatter with the name prefixed
  by the profile, and the role's body followed by the fragment. `setup.py` plans these
  files under `.claude/agents/` as harness-owned paths, recorded by hash in the
  manifest, with the same create, update, conflict and adopt outcomes `.harnex/rules.md`
  already has; an agent the harness wrote and no longer renders is removed by the plan,
  one it did not write is a conflict. The rendered agent paths join the harness's own
  paths that the clean-tree precondition exempts, so a rerun before the first commit
  still plans. Under `local` visibility each agent file is
  excluded through `.git/info/exclude` by its own path, so the project's own agents in
  the same directory are untouched.
- **`review` fans out.** After the core `reviewer`, the skill starts every agent of the
  project's teams whose phase is `review`, each once, and presents each review as
  returned, labelled by agent. Nothing merges, nothing blocks.
- **`propose` consults the advisors.** Before `design.md` is written, the skill starts
  every agent of the project's teams whose phase is `propose`, each once, with the
  proposal to read; their briefs are the architect's input to `design.md`, and the
  verifier still runs once at the end.
- **`setup` and `update`** show the team's agents in the plan, one line per path, and
  `update` refreshes them without asking, like every other harness-owned file. When
  `setup` offers profiles, it says which specialists each profile's team brings.
- **Decision 4 of `docs/PLAN.md` is revised**, the way `C5` already revised it once: the
  three write boundaries (writes source, writes artifacts, reads only) stay fixed; the
  number of roles does not. Decision 1 is extended: a stack is a profile, and a profile
  may declare a team. Decision 11 is untouched.

## Non-Goals

- No `react`, `nextjs`, `vue`, `django`, `go`, `node`, `swift` or `kotlin` team: the
  mechanism is proven on three stacks the owner runs; a further team is a profile
  directory and its fragments, no code.
- No specialist in `verify` or `apply`: `accessibility-reviewer` reads the diff in
  `review`; running it against a live app, and pairing `test-engineer` with the builder
  inside the apply loop, each wait for a change of their own. `test-engineer` is held by
  instruction alone in this change, like the builder is outside the loop, and its
  frontmatter and design say so. The core `debugger` and `test-engineer` have no caller
  among the skills in this change: the person starts them by name. A profile may carry a
  `debugger` fragment, since it is a `review`-phase role; none of the three here does.
- No lead agent: a subagent cannot start subagents, so the playbook (who runs in which
  phase) is the role's declared `phase`, read by the skills, not a prompt that delegates.
- No per-specialist opt-out: a team is rendered whole, as a pure function of the profile.
- No Codex binding for any specialist: like `reviewer` and `verifier`, they are Claude
  subagents only.
- No native Claude Code agent-teams (teammates) mode.
- No "Identity & Memory", backstory, voice or mood for a role: the persona is five lines
  of disposition, and nothing in it says how the agent talks or how sure it sounds.
- No model pin for a stack reviewer: `reviewer`'s fixed `opus` stays its own; a stack
  reviewer starts without a model override. For the same reason no profile carries a
  `reviewer` fragment — a rendered `<profile>-reviewer` would state a fixed model it is
  not started with — and the renderer does not yet refuse one: that refusal waits for a
  profile that wants it.
- No rerun guarantee between an agent's removal and the commit that records it: once
  `update` or `setup` has removed a dropped profile's agents, the deletions are
  uncommitted and no longer in the record, so a `setup` rerun before that commit sees a
  dirty tree and refuses, as it would for any uncommitted deletion. `docs/smoke.md`
  commits first; closing the gap is its own change.

## Capabilities

### New Capabilities
- `agent-teams`: what a team is (a profile's roster), the role file format with its
  frontmatter, persona and stack slot, the rendering as a pure function of the chosen profiles,
  the rendered agent's name, tools and placement by visibility, and removal when a
  profile is dropped.

### Modified Capabilities
- `project-setup`: the plan includes the chosen profiles' agents under `.claude/agents/`
  with the ownership outcomes, removal of agents no longer rendered, and the local
  exclude entries; a profile directory is offered the same as a flat profile; the
  clean-tree precondition exempts the rendered agent paths.
- `harness-update`: update refreshes the rendered agents and removes stale ones, from
  the recorded profiles, asking nothing.
- `review-command`: after the core reviewer, every `review`-phase agent of the
  project's teams runs once and its review is shown as returned.
- `architect-commands`: `propose` consults every `propose`-phase agent of the project's
  teams before writing `design.md`, and still calls the verifier once.
- `reviewer-role`: the read-only guarantee extends to every agent rendered from a
  `review`-phase role, through the same `tools` mechanism, with no model override. The
  `propose`-phase read-only guarantee is stated in `agent-teams`.

## Impact

- `plugin/orchestration/roles/` — seven new role files; frontmatter added to the three
  existing ones; a persona section in all ten; `README.md` updated.
- `plugin/agents/` — `test-engineer.md`, `debugger.md`; all five adapters are the
  output of `render_agents.py sync`.
- `plugin/tools/profiles/` — `rails/`, `fastapi/` (moved from `fastapi.md`), `flutter/`,
  each `profile.md` plus three fragments; `README.md` updated.
- `plugin/scripts/render_agents.py` — new, with `sync` for the plugin's own adapters;
  `plugin/scripts/setup.py` plans the rendered
  agents, their removal and their local exclusion; `plugin/scripts/update.py` gains
  one `Removed:` line in its report and nothing else beyond what the shared plan builder
  gives it.
- `plugin/skills/setup/SKILL.md`, `update/SKILL.md`, `review/SKILL.md`,
  `propose/SKILL.md`.
- `tests/` — `test_render_agents.py` (new), `test_agent_and_skill_frontmatter.py` (role
  frontmatter, read-only roles, persona shape), `test_setup_write.py`, `test_setup_local.py`,
  `test_update_run.py`, skill-content tests, `test_layout.py` unchanged.
- `docs/PLAN.md` — §4 roles table (with each role's emoji and name), §5 layout, §12
  decisions 1 and 4, a `C10` entry;
  `docs/diagrams/` regenerated (`01-overview`, `02-architecture`, `03-workflow`,
  `06-roadmap`, `07-layout`); `README.md` where it lists
  what a project receives; `docs/smoke.md` — an `agent-teams (C10)` section recording
  the manual try.
