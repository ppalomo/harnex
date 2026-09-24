## Why

harnex is a plan and seven diagrams: there is nothing a machine can install. Every later
capability — rules, setup, the commands, the guard, the canary — is delivered through a
Claude Code plugin, so the plugin has to exist and install before any of them can be
tried. This change builds the delivery vehicle and nothing else, so that the first thing
that works is the thing everything else rides on.

It also fixes the layout while it is still free to fix: the five pillar directories are
created here, each stating what belongs in it, so no later change has to guess where a
component goes.

Phase: **C1a** of `docs/PLAN.md` §10. Exit criterion: the plugin installs from a local
checkout and validates strict on a machine that has never seen harnex.

Pillar: this change is the plugin's own skeleton and touches all five pillar directories
by creating them empty. It delivers no component, so it belongs to no single pillar; the
`README.md` in each directory is the statement of what that pillar holds.

## What Changes

- Add `.claude-plugin/marketplace.json` at the repository root: a catalogue with one
  entry, the harnex plugin, pointing at `plugin/`.
- Add `plugin/.claude-plugin/plugin.json` declaring the plugin's name (`harnex`), its
  version (`0.1.0`) and its description.
- Create the five pillar directories — `plugin/context/`, `plugin/tools/`,
  `plugin/orchestration/`, `plugin/control/`, `plugin/feedback/` — each with a
  `README.md` stating what belongs in it, what does not, and which later phase fills it.
- Add `docs/smoke.md`: the manual checks, one section per change, in the format every
  later change appends to. It starts with this change's own check.
- Add the repository's test entry point and its first three checks: `claude plugin
  validate plugin --strict`, a structural test over the plugin's directories, and a grep
  denylist for private names.

## Capabilities

### New Capabilities

- `plugin-delivery`: how the harness reaches a machine — the catalogue, the plugin
  manifest, the layout the plugin must keep, and what must never appear inside it.

### Modified Capabilities

<!-- None: this is the first change in the repository. -->

## Impact

- New: `.claude-plugin/`, `plugin/`, `docs/smoke.md`, and the test entry point with its
  fixtures.
- Unchanged: `docs/PLAN.md` (except its last task, which records what landed), the
  diagrams, `README.md`, `AGENTS.md`, `openspec/`.
- Dependencies: Claude Code's `plugin validate` for the strict check; Python with `uv`
  for the structural and denylist tests, as decision 9 settles.
- Downstream: `C1b` adds rule files under `plugin/context/`, `C1c` adds `/harnex:setup`
  under `plugin/skills/`, and `C1d` adds the canary hook — each lands inside the skeleton
  this change fixes.

## Non-goals

- No commands, skills, agents, hooks, scripts or MCP declarations. The plugin installs
  and does nothing, deliberately.
- No rule content: the pillar directories are created, not filled.
- No `/harnex:setup` and no generated project files; that is `C1c`.
- No publishing, versioning policy or tags; that is `C6`.
- No CI: the tests are runnable by hand here and wired into CI in `C6`.
