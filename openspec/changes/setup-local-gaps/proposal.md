**Pillar:** 1 · Context (the `setup` skill and `plugin/scripts/setup.py`) and 3 ·
Orchestration (the `apply` skill's Codex binding step) — no `control/` or `feedback/`
change.

**Phase:** `docs/PLAN.md` has no slot for this; it is a follow-up to
`C7 · a personal, local-only setup`, found by running `/harnex:setup` with `local`
visibility on a real project. Call it **`C9 · setup's local-visibility gaps`**. Exit
criterion: on a fresh git-less project, `local` setup asks where the OpenSpec store
lives, shows `git init` and the store registration in its plan, excludes `.env` from the
repository when `jev` is chosen, and a Codex-routed `apply` task is handed the rules.

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
  and passes the answer to `openspec store setup --path`. The answer is recorded as a
  new `store_path` answer so the plan can show it.
- **Store registration and `git init` move into the plan.** The plan lists both as
  steps; the skill runs each only after the person's yes to the plan, then writes.
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
- `shared` visibility changes in exactly one way: `.env` is excluded when `jev` is
  chosen. No change to its pointer-line mechanism, and no `.gitignore` edit
  under either visibility.
- No promotion path from `local` to `shared`.

## Capabilities

### Modified Capabilities
- `project-setup`: the `.env` notice requirement, the Codex disclosure, the store
  registration and the plan-before-side-effects behaviour change.
- `apply-command`: the Codex binding step is handed the rules under `local` visibility.

## Impact

- `plugin/scripts/setup.py` — `store_path` answer, `.env` in the exclude plan, plan steps
  for `git init` and store registration, updated Codex and `.env` notices.
- `plugin/skills/setup/SKILL.md` — store question, ordering of registration and
  `git init`, report of the global setting.
- `plugin/skills/apply/SKILL.md` — the Codex prompt prefix.
- `tests/test_setup_local.py`, `tests/test_setup_answers.py`, `tests/test_setup_write.py`.
- `docs/PLAN.md` — `C7`'s table and a new `C9` entry; `README.md` if it states the Codex
  limitation.
