**Pillar:** 1 · Context (the `setup` skill and `plugin/scripts/setup.py`) and 3 ·
Orchestration (the `apply` skill's Codex binding step) — no `control/` or `feedback/`
change.

**Phase:** `docs/PLAN.md` has no slot for this; it is a follow-up to
`C7 · a personal, local-only setup`, found by running `/harnex:setup` with `local`
visibility on a real project. Call it **`C9 · setup's local-visibility gaps`**. Exit
criterion: setup (the script's plan, which the guided command checks before its first
question) reports a conflict and writes nothing on a
project that is not inside a git repository or has uncommitted changes outside the
harness's own paths; on a clean one, `local` setup asks where the OpenSpec store lives, shows
the store registration in its plan, excludes `.env` from the repository when `jev` is
chosen, and a Codex-routed `apply` task is handed the rules.

## Why

The first real `local` run surfaced four gaps, all of the same kind — setup decided
something that was the person's to decide, or left something unprotected:

1. **The OpenSpec store path was chosen by the tool.** `openspec store setup` refuses to
   run without `--path`, so setup accepted the tool's suggestion (`~/openspec/<id>`).
   The person wanted it under `~/Developer`. Setup never asked.
2. **Codex builds without the rules.** `local` visibility writes no `AGENTS.md`, and
   `CLAUDE.local.md` is read by Claude only. Setup discloses this, but disclosure leaves
   the gap: the rules the project chose do not bind its second builder.
3. **`.env` is unprotected.** Setup ran `git init` itself and then only printed a notice
   that keeping `.env` out of version control was the person's job. The repository is
   brand new, so the first `git add .` commits the API key. Setup was already editing
   `.git/info/exclude`; the entry belonged there.
4. **Setup's side effects were not all in the plan.** `git init` and the store
   registration ran before the person had seen a plan, and the global
   `~/.claude/settings.json` change was reported afterwards without naming the key.

## What Changes

- `local` setup **asks where the store lives**, proposing nothing the person did not see,
  and passes the answer to `openspec store setup --path`. The answer travels as a new
  `store_path` answer so the plan can show it; only the store id is recorded among the
  project's choices, never the path.
- **Setup requires a clean git working tree apart from the harness's own paths**, under
  either visibility (worktrees and subdirectories included; `update` exempt): no `.git`, or
  anything `git status --porcelain` reports (untracked files included), is a conflict
  that stops the run before any write. Setup never runs `git init` itself; the person
  creates the repository and commits first. A clean start means the person's own
  work outside the files the harness writes or edits is committed before the harness
  touches anything, so setup's writes are easy to tell apart; uncommitted edits to those
  files (`AGENTS.md`, `CLAUDE.md`, `.claude/settings.json`, `.mcp.json` and the like)
  are allowed, since a rerun and an interrupted run must still complete; it also guarantees `.env` is
  excluded before any commit that could include it. The harness's own paths do not
  count, so a rerun or an interrupted run still completes.
- **Store registration moves into the plan.** The plan lists it as a step; the skill
  runs it only after the person's yes to the plan, then writes.
- The **`apply` skill hands Codex the rules** under `local` visibility: the prompt it
  passes to `/codex:rescue` starts with an instruction to read `.harnex/rules.md` in the
  project and follow it. The Codex disclosure in setup changes from "will not have read
  the rules" to what is now true: the apply loop hands them over; Codex run outside the
  loop still will not have them.
- **`.env` is added to `.git/info/exclude`** when `decision_model` is `jev` and the
  project is a git repository, under either visibility. The project's `.gitignore` and
  `.env` itself are still never touched. The notice says the file is excluded and, under
  `shared` visibility, that other clones are not protected by it.
- The skill's final report **names the global setting it wrote** (key and value).

## Non-Goals

- No `AGENTS.override.md`, no write to `~/.codex/`: the first would shadow the project's
  own `AGENTS.md`, the second is machine-wide.
- No credential file other than `.env`: it is the only one a harness backend reads.
- `shared` visibility changes in exactly two ways: `.env` is excluded when `jev` is
  chosen, and setup requires a git repository with no uncommitted project changes. No
  change to its pointer-line mechanism, and no `.gitignore` edit
  under either visibility.
- No promotion path from `local` to `shared`.

## Capabilities

### Modified Capabilities
- `project-setup`: the `.env` notice requirement, the Codex disclosure, the store
  registration and the plan-before-side-effects behaviour change.
- `apply-command`: the Codex binding step is handed the rules under `local` visibility.
- `local-visibility`: the default scenario names `shared`'s later deliberate additions.
- `harness-update`: a fresh clone's update also restores the `.env` exclude entry for a
  `jev` project, since the exclude list is per clone.

## Impact

- `plugin/scripts/setup.py` — `store_path` answer, `.env` in the exclude plan, plan steps
  for store registration, the clean-tree conflict, updated Codex and `.env` notices.
- `plugin/skills/setup/SKILL.md` — store question, ordering of registration and
  the clean-tree precondition, report of the global setting.
- `plugin/skills/apply/SKILL.md` — the Codex prompt prefix.
- `tests/conftest.py`, `tests/test_setup_local.py`, `tests/test_setup_answers.py`,
  `tests/test_setup_write.py`, `tests/test_setup_survey.py`, `tests/test_private_names.py`.
- `docs/PLAN.md` — `C7`'s table and a new `C9` entry; `docs/smoke.md`, whose walkthroughs
  start from a committed repository; `README.md`, which states every setup step a
  newcomer needs and so must state the clean-tree precondition.
