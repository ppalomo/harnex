**Pillars:** 3 · Orchestration (the roster a project keeps, the `department` a role
declares, the renderer's generic agent and the `review`/`propose` fan-out reading the
roster) and 2 · Action & Tools (the `setup` and `update` skills and scripts, which record
and refresh it). No `control/` or `feedback/` change: every boundary this change touches
is held by the mechanisms `C10` already uses.

**Phase:** `docs/PLAN.md` has no slot for this; it is the first phase after `C10`. Call
it **`C11 · agent roster`**. Exit criterion: a harnessed project can name, in its own
choices file, which specialists it has — a `team` its phase skills start and a `bench`
it starts by name — independently of which stack profiles it chose; a specialist named
without a matching fragment is rendered in its generic form; a project that records no
roster behaves exactly as `C10` left it; `/harnex:review` and `/harnex:propose` start
the team and never the bench; every role declares a `department`, `engineering` or
`design`, which setup's offer groups the specialists by; and a profile dropped or
a roster edited takes effect on the next `setup` or `update` run — all tried by hand on
a scratch project, with every rule the plugin already enforces still holding.

## Why

`C10` gave a project a team, but the unit of choice is the profile: choosing `rails`
imports Penélope, Jame and Gideon together, a project that is not on a listed stack can
have none of them, and `/harnex:review` starts every reviewer the profile brought on
every diff. The person asked for the opposite shape — "in each repo I say which ones I
need, some always, some on demand" — and for the roles to be grouped by the department
they belong to, so that an engineering roster and, later, a design or a marketing one
can be told apart. The profile stays the right place for what a stack adds to a
specialist; it is the wrong place to decide who is on the team.

## What Changes

- **A project records a roster, in two flat lists.** `.harnex.yml` (and, under `local`
  visibility, `.harnex/config.yml`) may carry `team:` and `bench:`, each a list of
  specialist names. A name in `team` is rendered into the project and started by the
  skill of its role's phase; a name in `bench` is rendered the same way but started
  only by the person, by name. Both keys are present or both absent: present, the
  roster is exactly what they say and the chosen profiles add nobody; absent, the
  chosen profiles' fragments decide, as `C10` does today, every one of them on the
  team. A name in both lists, a name that is no `review`- or `propose`-phase role, and
  a name that already ships as a plugin agent are each refused before anything is
  written. The file stays flat: scalars and lists, read by the same reader.
- **A specialist without a fragment renders generically.** For each roster name, the
  renderer produces one agent per chosen profile holding a fragment for it, named
  `<profile>-<specialist>` as today, and — when no chosen profile holds one — a single
  `<specialist>` agent from the role alone: same frontmatter, same body, no stack
  section. Rendering stays a pure function of the choices, and every rendered agent
  stays read-only, since only `review`- and `propose`-phase roles can be named.
- **Every role declares its `department`.** A fifth frontmatter field, `engineering`
  or `design` in this change, dropped from the rendered agent like `phase` is. Setup's
  offer of specialists groups by it; the listing the skills use to start agents does
  not carry it, since starting an agent does not depend on its department. `designer` and
  `accessibility-reviewer` are `design`; every other role is `engineering`.
- **Setup asks for the roster once.** On a first setup, after the profiles, the
  command offers every specialist the harness holds — grouped by department, each as
  `<emoji> <name>` with its phase — and proposes the chosen profiles' specialists as the
  team with an empty bench; the person moves, drops or adds names. It records both
  lists. A project whose choices are already recorded is not asked: the person adds
  the keys to the project's own file and runs setup or update again, as for any other
  choice.
- **`review` and `propose` start the team, never the bench.** The listing a skill asks
  for takes the roster alongside the profiles and prints only team agents of the
  phase; a bench agent is on disk, for the person to start by name, and is not listed.
  A project without a roster lists what it lists today.
- **`update` refreshes the roster's agents asking nothing**, from the recorded keys:
  a name added renders, a name removed is removed when its file still matches its
  fingerprint, a profile dropped turns a prefixed agent into the generic one. The
  ownership, conflict and removal outcomes of `C10` apply unchanged.
- **Decisions 1, 4 and 11 of `docs/PLAN.md` are revised**, each openly. Decision 11:
  the answers file gains two optional keys, `team` and `bench`. Decision 4: the five
  specialists are rendered per project from the roster — prefixed by a chosen profile
  that holds a fragment for one, generic otherwise — rather than only "from a
  profile's team", and each role belongs to a department. Decision 1: a stack is still
  a profile and a profile still declares fragments, but its fragments are its team
  only for a project that records no roster; under a roster they are what that stack
  adds to a specialist the roster names.

## Non-Goals

- No `triggers`: which team reviewer reads a given diff is the next change, with its
  own question of where a stack's paths are declared. In this change every team
  reviewer of the phase runs, as `C10` does.
- No `/harnex:team` listing command, and no department in the renderer's `list`. The
  listing gains the roster, which the skills need; showing the team by department is
  that later command's job.
- No department beyond `engineering` and `design`, and no role added or removed. The
  ten roles are regrouped, not changed.
- No roster entry for a core agent: `builder`, `reviewer`, `verifier`, `test-engineer`
  and `debugger` ship with the plugin and are in every project; naming one is refused.
- No per-profile roster, no roster that names a profile, no `team` that varies by
  phase: one list of names, and each name's role says which phase starts it.
- No change to the manifest format, the guard, the floor, the decision questions, the
  persona shape or the fragment convention.
- No promotion of an existing project's absent roster into recorded keys: `update`
  never writes the choices file, and setup does not ask a project that has already
  answered.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-teams`: a project's roster, its two keys and their semantics; the generic
  rendering of a specialist without a fragment; the `department` field as the fifth of
  a role's frontmatter; the refusals on a roster name; the listing taking the roster;
  the placement and read-only requirements extended to the generic agent.
- `project-setup`: the choices file's two optional keys; the roster question on a
  first setup and the offer grouped by department, under either visibility, the local
  choices file included; the plan's agent lines following the
  roster rather than the profiles alone.
- `harness-update`: update refreshes the agents from the recorded roster and profiles.
- `review-command`: the fan-out starts the team's `review`-phase agents, not every
  rendered one.
- `architect-commands`: `propose` consults the team's `propose`-phase agents, not
  every rendered one.

## Impact

- `plugin/orchestration/roles/*.md` — `department` added to all ten; `README.md`.
- `plugin/scripts/render_agents.py` — five role fields; generic rendering; `render`,
  `list` and `agents_for` take `--team`/`--bench`; refusals list the specialists held.
- `plugin/scripts/setup.py` — `team` and `bench` as optional answer keys, both shapes;
  validation of roster names; `choices` lists every specialist with department, emoji
  and phase; `_render_agents` follows the roster; `_own_agents` unchanged in kind.
- `plugin/scripts/update.py` — reads the optional keys.
- `plugin/skills/setup/SKILL.md`, `update/SKILL.md`, `review/SKILL.md`,
  `propose/SKILL.md`; `plugin/context/templates/harnex.yml` and
  `local-config.yml` if they enumerate keys.
- `tests/` — `test_render_agents.py`, `test_agent_and_skill_frontmatter.py`,
  `test_setup_answers.py`, `test_setup_survey.py`, `test_setup_write.py`,
  `test_setup_local.py`, `test_update_reader.py`, `test_update_run.py`,
  `test_review_skill.py`, `test_propose_skill.py`, `test_setup_and_update_skills.py`.
- `docs/PLAN.md` — §4 roles table gains a department column, §6 the two keys, §12
  decisions 1, 4 and 11, a `C11` entry; `docs/diagrams/` regenerated where the team is
  drawn; `README.md` where it says a profile brings its team; `docs/smoke.md` — an
  `agent-roster (C11)` section.
