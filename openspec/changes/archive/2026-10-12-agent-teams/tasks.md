## 1. Roles with a frontmatter

- [x] 1.1 Paths: `plugin/orchestration/roles/`, `plugin/agents/`, `tests/test_agent_and_skill_frontmatter.py`. Add the four-field frontmatter (`name`, `description`, `tools`, `phase`) to
  `plugin/orchestration/roles/builder.md`, `reviewer.md` and `verifier.md`, copying
  `name`, `description` and `tools` from their adapters under `plugin/agents/`
  (`phase: apply` for the builder, `review` for the reviewer, `verify` for the
  verifier). Verify with `tests/test_agent_and_skill_frontmatter.py` extended to parse
  the role's frontmatter, assert exactly those four fields, `name` equal to the file
  name, `phase` among `apply`, `propose`, `review` and `verify`, and the adapter's
  `name`/`description`/`tools` equal to the role's, with the body comparison now
  against the role's body alone.
- [x] 1.2 Paths: `plugin/orchestration/roles/`, `tests/test_agent_and_skill_frontmatter.py`. Write the seven new role prompts to the existing skeleton, each ending with a
  sentence that the stack section follows: `test-engineer` (`apply`; `Read, Grep, Glob,
  Edit, Write, Bash`; tests-only boundary stated as instruction; says the person
  starts it by name in this version), `debugger` (`review`; `Read, Grep, Glob`; same
  note), `security-reviewer`, `migration-reviewer`, `accessibility-reviewer`
  (`review`; `Read, Grep, Glob`), `api-designer`, `designer` (`propose`; `Read, Grep,
  Glob`). No technology named in any of them. Verify with the frontmatter test, the
  read-only test extended to every `review`/`propose`/`verify`-phase role, and
  `tests/test_private_names.py`.
- [x] 1.3 Paths: `plugin/agents/`, `plugin/orchestration/README.md`, `tests/test_agent_and_skill_frontmatter.py`. Add `plugin/agents/test-engineer.md` and `plugin/agents/debugger.md` binding
  their roles, and update `plugin/orchestration/README.md`'s "What is here". Verify with
  the adapter correspondence test and `claude plugin validate plugin --strict`.
- [x] 1.4 Paths: `plugin/orchestration/roles/`, `plugin/agents/`, `tests/test_agent_and_skill_frontmatter.py`. Give each of the ten roles its persona, per design D7: keep the opening paragraph
  under the title and insert `## Who you are` as the first `##` section after it — a
  single paragraph of at most five physical lines, opening with one emoji (a single
  code point of Unicode category `So`), exactly one space, and a bold given name, then
  up to three traits
  each drawn from that role's own "What you must not do" or "How to report" and stated
  as how it shows in the work — never confidence, seniority, speed or breadth, nothing
  about voice, mood or memory; every `review`- and `verify`-phase role's traits include
  saying when it is unsure. The same code point opens the role's `description`. Names
  and emojis unique across roles; no famous person's, colleague's or project's name.
  Mirror the body and the description into the five adapters under `plugin/agents/`.
  Verify with the frontmatter test extended to read the shape (first `##` heading,
  paragraph length, first code point's category and equality with the description's,
  exactly one space after the emoji in both places, uniqueness, adapters still exact
  copies) and `claude plugin validate plugin --strict`.

- [x] 1.5 Paths: `plugin/orchestration/roles/`, `plugin/agents/`, `plugin/skills/propose/SKILL.md`, `plugin/skills/review/SKILL.md`, `docs/smoke.md`, `tests/`. Replace the placeholder names and emojis of task 1.4 with the ones the person
  chose, keeping every trait as written: builder 💻 Savo, reviewer 🔍 Almira, verifier
  👀 Natalia, test-engineer 🧪 Raul, debugger 🐛 Dani, security-reviewer 🔐 Penélope,
  migration-reviewer 🧮 Jame, accessibility-reviewer 🦽 Ana, api-designer 🔌 Gideon,
  designer 🎨 Ines — every emoji a single code point that Unicode marks as emoji
  presentation by default, so it renders at full width. In each role: the `description`'s first code point and the
  `## Who you are` line's first code point become the new emoji, followed by exactly
  one space; the bold name becomes the new name; nothing else moves. Regenerate the
  adapters with `render_agents.py sync`. Update any skill text or test that spells a
  role's old emoji or name (the `propose` and `review` skills' example lines, the
  shipped-team tests in `tests/test_render_agents.py`, the `agent-teams (C10)` section
  of `docs/smoke.md`). Verify with the persona-shape tests (single `So`
  code point, one space, unique names and emojis), `sync --check` clean, and the full
  suite.

## 2. The renderer

- [x] 2.1 Paths: `plugin/scripts/render_agents.py`, `tests/test_render_agents.py`. Write `plugin/scripts/render_agents.py` (standard library only): read a role's
  frontmatter and body; list a profile directory's fragments; refuse a fragment with no
  role, naming it and the roles held, and refuse one for an `apply`- or `verify`-phase
  role, saying only `review`/`propose` roles take a fragment; render `{path: bytes}`
  for the chosen profiles,
  sorted, with `name: <profile>-<specialist>`, the description suffixed with the profile,
  the role's `tools`, and the body followed by `## For this stack: <profile>` and the
  fragment. Verify with `tests/test_render_agents.py`: byte-identical output for two
  orders, a single-file profile renders nothing, both refusals, and a rendered agent
  whose frontmatter has exactly the minimum agent fields and no writing tool.
- [x] 2.2 Paths: `plugin/scripts/render_agents.py`, `tests/test_render_agents.py`. Add `phase_of(role)` and `agents_for(profiles, phase)` helpers the skills can
  call from the command line (`render_agents.py list --profiles … --phase review`),
  printing, per agent a project should have, its `name` and the first code point of its
  rendered `description` (the role's emoji, per D7). Verify with a test per phase.

- [x] 2.3 Paths: `plugin/scripts/render_agents.py`, `plugin/agents/`, `plugin/orchestration/README.md`, `tests/test_render_agents.py`, `tests/test_agent_and_skill_frontmatter.py`. Add `render_agents.py sync [--plugin-root P] [--check]` per design D8: for every
  `plugin/agents/<name>.md` present, render the role `orchestration/roles/<name>.md`
  without a profile (`name`, `description`, `tools`; no `phase`; the body whole) and
  write it; `--check` writes nothing and exits non-zero naming each adapter that
  differs; an adapter with no role is refused by name. Run it once so the five adapters
  are its output. Replace the hand-written correspondence tests in
  `tests/test_agent_and_skill_frontmatter.py` with one that asserts `sync --check` is
  clean (keep the minimum-frontmatter and read-only tests), and test `sync` itself in
  `tests/test_render_agents.py` against a fixture plugin root (rewrite, check clean,
  check dirty names the adapter, missing role refused, empty adapter file filled).
  `plugin/orchestration/README.md`'s "What does not" paragraph on the adapter says it
  is generated by `sync`, never edited by hand.

## 3. Setup and update plan the agents

- [x] 3.1 Paths: `plugin/scripts/setup.py`, `tests/test_setup_write.py`, `tests/test_setup_local.py`, `tests/test_setup_survey.py`, `tests/test_guard.py`, `tests/conftest.py`, `tests/fixtures/`, `tests/snapshots/`. In `plugin/scripts/setup.py`, add the rendered agents to `desired` in both the
  shared and the local plan builders, with a `why` line naming the profile; under
  `local`, add each agent path to the exclude entries; extend `_harness_own` so each
  rendered agent path — from the answers' profiles and from the record's listed paths
  — is exempt from the clean-tree precondition while `.claude/agents/` itself is not.
  Verify in `tests/test_setup_survey.py` (a shared rerun with uncommitted rendered
  agents plans nothing to do; an untracked `.claude/agents/own.md` still conflicts; a
  recorded stale agent does not block the rerun that removes it) and in
  `tests/test_setup_write.py` and `tests/test_setup_local.py`: three agents written and
  recorded for a fixture profile directory with three fragments; none for a flat
  profile; local exclude holds each path and not the directory; a tracked
  `.claude/agents/own.md` untouched; a hand-written agent at a rendered path is a
  conflict; adoption replaces it.
- [x] 3.2 Paths: `plugin/scripts/setup.py`, `tests/test_setup_write.py`, `tests/test_setup_local.py`, `tests/test_setup_survey.py`, `tests/conftest.py`, `tests/fixtures/`, `tests/snapshots/`. Add removal to the plan: a recorded `.claude/agents/` path not in `desired` is
  a `REMOVE` step when the file matches its fingerprint, a conflict otherwise, never
  touched when unrecorded; `apply_plan` deletes it and `_plan_record` drops it. Verify
  with tests: dropping the profile removes the three and leaves `own.md`; an edited
  stale agent conflicts; `nothing_to_do` counts a removal as work.
- [x] 3.3 Paths: `plugin/scripts/setup.py`, `tests/test_setup_survey.py`, `tests/snapshots/`. Make the setup plan's profile offer say which specialists each profile brings
  (`choices_on_offer` gains a per-profile team list). Verify in
  `tests/test_setup_survey.py`.
- [x] 3.4 Paths: `tests/test_update_run.py`, `tests/conftest.py`, `tests/fixtures/`, `plugin/scripts/update.py`. `tests/test_update_run.py`: a changed fragment rewrites the agent on update; a
  fresh clone of a shared project with agents plans them unchanged; a dropped profile
  removes them on update without asking.

## 4. The profiles

- [x] 4.1 Paths: `plugin/tools/profiles/`, `tests/test_render_agents.py`, `tests/test_setup_answers.py`. Move `plugin/tools/profiles/fastapi.md` to `fastapi/profile.md` and add
  `security-reviewer.md`, `migration-reviewer.md` and `api-designer.md` fragments for
  it. Verify `available_profiles()` still reports `fastapi` and the renderer produces
  three agents for it.
- [x] 4.2 Paths: `plugin/tools/profiles/rails/`, `tests/test_render_agents.py`, `tests/test_setup_answers.py`. Add `plugin/tools/profiles/rails/` with `profile.md` and the same three
  fragments. Verify with the renderer test and `tests/test_private_names.py`.
- [x] 4.3 Paths: `plugin/tools/profiles/flutter/`, `tests/test_render_agents.py`, `tests/test_setup_answers.py`. Add `plugin/tools/profiles/flutter/` with `profile.md` (stating that the
  browser step does not apply and what evidence `verify` reads instead), and
  `designer.md`, `accessibility-reviewer.md`, `security-reviewer.md` fragments; leave
  `ui.json` unchanged. Verify with the renderer test and a test that `flutter` is not a
  UI profile.
- [x] 4.4 Paths: `plugin/tools/README.md`. Update `plugin/tools/README.md`'s "What is here" for the three directories and
  the fragment convention.

## 5. The skills

- [x] 5.1 Paths: `plugin/skills/review/SKILL.md`, `tests/`. `plugin/skills/review/SKILL.md`: after the core reviewer, list the project's
  `review`-phase agents (`render_agents.py list`), start each once with the same diff,
  show each review as returned under the emoji and `name` the list printed, report a missing one with `/harnex:update`
  as the remedy, never merge. Verify with the skill-content tests.
- [x] 5.2 Paths: `plugin/skills/propose/SKILL.md`, `tests/`. `plugin/skills/propose/SKILL.md`: between the proposal and `design.md`, list the
  `propose`-phase agents, start each once with the proposal, fold their briefs into
  `design.md` naming the advisor; the verifier still runs once at the end. Verify with
  the skill-content tests.
- [x] 5.3 Paths: `plugin/skills/setup/SKILL.md`, `plugin/skills/update/SKILL.md`, `tests/`. `plugin/skills/setup/SKILL.md` step 4 says what a profile's team brings when
  offering profiles, and the report names the agents written; `update/SKILL.md` names
  the agents among what it refreshes and removes. Verify with the skill-content tests.

## 6. Docs and the check

- [x] 6.1 Paths: `docs/PLAN.md`, `README.md`, `docs/diagrams/`. `docs/PLAN.md`: §4's roles table gains the new roles with their holding
  mechanism (`test-engineer` instruction only; `debugger` and `test-engineer` started
  by the person in this version) and each role's emoji and name, and its skeleton
  description names the `## Who you are` section; §5's layout shows the profile directories and
  `render_agents.py`; §12 extends decision 1 and revises decision 4 as the proposal
  states; a `C10 · agent teams` entry with its exit criterion; `README.md` where it
  lists what a project receives; regenerate `03-workflow` and `07-layout` with
  `python3 docs/diagrams/build.py`.
- [x] 6.2 Paths: `docs/smoke.md`. Add an `agent-teams (C10)` section to `docs/smoke.md` in its existing format:
  a scratch project that chooses `rails` — setup shows and writes three agents, a rerun
  before committing plans nothing to do, each rendered agent's `## Who you are` is its
  role's own, `review` shows three reviews (the core reviewer, then the security and
  migration reviewers, each labelled with its emoji and `name`), `propose` consults
  the API designer, dropping the profile removes the agents on `update`, and a
  hand-written agent at a rendered path is a conflict. Verify the section is present
  and each step names what to observe.
- [x] 6.3 Paths: `docs/PLAN.md`. Run `uv run --with pytest pytest`, `claude plugin validate plugin --strict`,
  `claude plugin validate . --strict` and `openspec validate --all`; then walk the
  `docs/smoke.md` section by hand on a scratch project and record the outcome in
  `docs/PLAN.md`'s `C10` entry.
