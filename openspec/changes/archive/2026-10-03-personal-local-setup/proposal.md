## Why

Today `/harnex:setup` always leaves a committed trace: it creates or edits `AGENTS.md`
and `CLAUDE.md`, and writes `.harnex.yml`, `.harnex/rules.md`, `.harnex/manifest.json`,
entries in `.claude/settings.json`, entries in `.mcp.json` and `openspec/config.yaml` —
all meant to be shared with a team, via source control. That is the right default for a
project the harness is being adopted into. It is the wrong default for a person using
harnex on their own — a repository they do not own, a team repository under a review
policy they are not the one to change, or simply trying harnex before proposing it to
anyone. There, every one of those writes is a change nobody asked to review, in a history
nobody asked to carry.

## What Changes

- `/harnex:setup` gains a `visibility` choice: `shared` (today's behaviour, unchanged,
  still the default) or `local`.
- In `local` visibility, setup never creates or edits `AGENTS.md` or `CLAUDE.md`, whether
  or not the project already has them. Instead it writes `CLAUDE.local.md` at the project
  root — one `@.harnex/rules.md` import — and keeps it untracked through
  `.git/info/exclude`, never through the project's own `.gitignore`.
- In `local` visibility, the project's recorded choices live at `.harnex/config.yml` — a
  new path this change introduces, not a rename of `.harnex.yml` — and the directory's
  existing self-ignoring `.gitignore` (today scoped to `.harnex/state/` only) widens, for
  `local` visibility only, to the whole directory, so every harness-owned path there is
  untracked from the moment it is written. `shared` visibility keeps `.harnex.yml` at the
  project root exactly as it is today — decision 11 of `docs/PLAN.md` §12 is not
  reopened.
- The permission floor is written to `.claude/settings.local.json` instead of
  `.claude/settings.json`; an MCP entry (e.g. Playwright for a UI profile) is registered
  with `claude mcp add --scope local` instead of being written into the project's
  `.mcp.json`; nothing is written to `openspec/config.yaml`.
- In `local` visibility the project gets no `openspec/` directory of its own: setup
  registers a local OpenSpec store (`openspec store setup`) and `propose`, `apply`,
  `verify` and `ship` — the ones that touch `openspec` at all — resolve `--store` (or,
  where a script reads `openspec/changes/<name>/` directly, `--changes-root`) from the
  project's own `.harnex/config.yml` instead of the nearest `openspec/` root, so the
  proposal/design/spec/task trail for work done there stays off the project's history
  too. `explore` and `review` resolve nothing — neither calls `openspec` under either
  visibility.
- Setup, in `local` visibility, is explicitly guided: a fixed, stated list of questions
  (profiles, rule sets, canary, decision backend — as today — plus which roles/tools the
  person wants active). That list surfaces, rather than silently deciding, that the Codex
  builder binding cannot see harnex's rules under `local` visibility, since it depends on
  reading `AGENTS.md`, which this mode never touches.
- Setup offers, once per machine and only with the person's explicit yes (never silently,
  never per project), the one global settings change that keeps a project's
  `CLAUDE.local.md` from suppressing that project's own `AGENTS.md`
  (`instructionFiles: claude-md-and-agents-md` in the person's own
  `~/.claude/settings.json`).
- `harness-ownership`'s "the record is committed" contract gains the local case: the
  manifest still exists, and `update` still reads it, but under `local` visibility it is
  never part of what the project commits — consistent with everything else local
  visibility touches.

## Capabilities

### New Capabilities
- `local-visibility`: what `local` visibility means across the harness — which path
  moves where, how each stays untracked without ever touching a project-owned ignore
  file or instruction file, and how `propose`, `apply`, `verify` and `ship` resolve a
  local OpenSpec store instead of a project's own `openspec/` (`explore` and `review`
  never touch `openspec` at all, under either visibility).

### Modified Capabilities
- `project-setup`: the new `visibility` choice, the guided question list `local`
  visibility asks (including the roles/tools question), and the survey/plan/write
  behaviour for every path that moves under local visibility.
- `harness-ownership`: the commit contract for the generation record gains the local
  case — recorded, but never committed.

## Impact

- `plugin/scripts/setup.py`: a new `visibility` input, new survey classes for
  `CLAUDE.local.md`, `.git/info/exclude`, `.claude/settings.local.json` and the local
  OpenSpec store registration; the existing `shared` path is untouched.
- `plugin/skills/setup/`: the guided question list for `local` visibility.
- `plugin/skills/propose/`, `apply/`, `verify/`, `ship/`: each gains a small step
  resolving `--store` from `.harnex/config.yml` when visibility is `local`; unchanged
  under `shared`. `plugin/skills/explore/` and `review/` gain nothing here — neither
  calls `openspec` under either visibility, so there is nothing for either to resolve.
- `docs/PLAN.md`: a new §11 phase entry (`C7`), and §6's ownership table gains the local
  column.
- Nothing about the `shared` path — today's setup, ownership contract, or any of the five
  commands — changes.

## Non-goals

- Promoting an existing `local` setup to `shared` (committing the `CLAUDE.local.md`
  line for real, moving floor entries into `.claude/settings.json`, and so on). A real
  future need, not this change.
- Giving Codex a way to read harnex's rules without touching `AGENTS.md`. Under `local`
  visibility the Codex builder binding is left exactly as capable as it is today —
  neither specially enabled nor blocked — and the guided setup question says so.
- Changing anything about the `shared` path this repository itself uses, or about C1c's
  settled setup/update contract for it.
- A command that performs the one-time `~/.claude/settings.json` tweak automatically,
  without the person's explicit yes at the moment it is offered.

## Pillar

Primarily pillar 2 (Action & Tools: `setup.py`, the setup skill's guided questions, the
MCP registration). Pillar 3 (Orchestration) for `propose`/`apply`/`verify`/`ship`'s store
resolution, and
pillar 1 (Context & Memory) for `.harnex/config.yml`, `local` visibility's own answers
file, and for `harness-ownership`'s extended contract.

## Phase

`C7 · a personal, local-only setup`, the next phase after C1–C6 in `docs/PLAN.md` §11
(not a reopening of C1c, which stays the `shared` default, unchanged).

**Exit criterion:** running `/harnex:setup` with `local` visibility, on both an empty
project and an existing project with its own committed `AGENTS.md`, leaves `git status`
clean throughout and after — rules, the guard, the canary, and all five commands work —
and running it again changes nothing.
