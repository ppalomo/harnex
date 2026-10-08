## 1. The answers and the plan

- [x] 1.1 In `plugin/scripts/setup.py`, add a `store_path` answer (text, local
  visibility only, refused otherwise and refused empty under `local` when no recorded
  `store_id` exists), and plan a step "register store `<id>` at `<path>`". Verify with
  tests in `tests/test_setup_answers.py` and `tests/test_setup_local.py`.
- [x] 1.2 Add `.env` to the exclude plan when `decision_model` is `jev` and `.git`
  exists (since 5.1: when the project is inside a repository found by `git rev-parse`) (either visibility); extend `_maybe_jev_notice` to say it is excluded, and for
  `shared` that other clones are not protected. Verify with tests asserting
  `git check-ignore .env` after a real write, and `.env`/`.gitignore` unchanged.
- [x] 1.3 (Superseded by 4.1: the `git init` step was withdrawn.) Under `local` visibility with no `.git`, plan a `git init` step instead of a
  conflict, with the exclude entries pending on it. Verify with a test; `shared` still
  conflicts.
- [x] 1.4 Replace `CODEX_LOCAL_NOTICE` with the new wording from the spec. Verify with
  the existing notice test updated.
- [x] 1.5 Show the global setting as a plan line with the exact key and value (it
  already is a notice; make it a step line), approved only by its own yes as before.
  Verify with a test that an unapproved setting is shown and not written.
- [x] 1.6 Tests for the remaining scenarios: a rerun reuses the store and asks no path;
  `mock` adds no `.env` entry and a `jev`→`mock` change leaves an earlier entry in place;
  `shared` with `jev` adds only the `.env` exclude entry and nothing else differs from
  before; `jev` with `git init` pending shows one plan with both lines (that last
  clause superseded by 4.1).

## 2. The skills

- [x] 2.1 (Its `git init` parts superseded by 4.2.) `plugin/skills/setup/SKILL.md`: ask where the store lives (step 2 and 3), run
  `openspec store setup <id> --path <path>` and `git init` only after the yes to the
  plan, rewrite the Codex sentence in step 2.8, and name the global setting's key and
  value in the final report; show `git init` and the `.env` exclusion in the one plan
  (a single yes, no second plan). Verify with the skill-content tests that already assert
  this file.
- [x] 2.2 `plugin/skills/apply/SKILL.md` step 4.1: under `local` visibility, prefix the
  Codex prompt with the instruction to read `.harnex/rules.md`, and leave the prompt as
  the task's own text under `shared`. Verify with skill-content tests for both.

## 3. Docs

- [x] 3.1 Update `docs/PLAN.md` (`C7` table and Codex limitation, new `C9` entry) and
  `README.md` if it states the Codex limitation; regenerate diagrams only if the
  workflow changed.
- [x] 3.2 Run `uv run --with pytest pytest`, both `claude plugin validate --strict`
  calls and `openspec validate --all`.

## 4. Clean working tree precondition (revision)

- [x] 4.1 In `plugin/scripts/setup.py`, replace 1.3's `git init`/`pending` steps with a
  survey-time precondition for `setup` (not `update`), under either visibility: no
  `.git`, a failing `git status --porcelain=v1 --untracked-files=all`, or any output line
  is a conflict naming what to do and listing the paths; `write` refuses on it like any
  conflict. Update `tests/test_setup_local.py`, `tests/test_setup_write.py`,
  `tests/test_setup_survey.py` and any other test whose fixture project is not a clean
  git repository, so fixtures that expect a plan start from a committed repository.
  Verify with tests for no `.git`, a modified file, an untracked file, an ignored file
  (allowed), a clean repository, and a `local` rerun after a write.
- [x] 4.2 `plugin/skills/setup/SKILL.md`: remove running `git init`; state the clean-tree
  precondition before step 1's questions (check it first, and stop with the paths if it
  fails, rather than asking questions the plan will refuse); keep the store registration
  after the yes. Update the skill-content tests.
- [x] 4.3 `docs/PLAN.md` (C9 entry and the local table) and `docs/smoke.md` (both
  walkthroughs start from a committed repository): replace the `git init` step with the
  precondition.
- [x] 4.4 Run `uv run --with pytest pytest`, both `claude plugin validate --strict` calls
  and `openspec validate --all`.

## 5. Verify findings (revision)

- [x] 5.1 In `plugin/scripts/setup.py`: the clean-tree check ignores the harness's own
  paths (the list in the spec) and reports its conflict alongside the full plan instead
  of replacing it; find the repository with `git rev-parse` (worktree `.git` file and a
  parent repository both count) and resolve the exclude file with
  `git rev-parse --git-path info/exclude`, used by both the `.env` exclusion and the
  local exclusions; refuse a `store_path` when `.harnex/config.yml` already records a
  `store_id`; make `nothing_to_do` count a `register` step as work. Tests: a shared rerun
  before committing plans nothing to do; an interrupted setup (some harness files
  written) completes; a dirty non-harness path still conflicts and the rest of the plan
  is printed; a worktree and a subdirectory exclude `.env` in the right file; `update`
  on a dirty tree is not refused; `store_path` with a recorded `store_id` is refused.
- [x] 5.2 `plugin/skills/setup/SKILL.md` step 1, `docs/PLAN.md` and `docs/smoke.md`:
  state that the harness's own paths do not count, so a shared rerun before committing
  is allowed (remove the "refused" notes), and that worktrees and subdirectories work.
  Update the skill-content tests.
- [x] 5.3 Run `uv run --with pytest pytest`, both `claude plugin validate --strict` calls
  and `openspec validate --all`.

## 6. Second verify findings (revision)

- [x] 6.1 `plugin/scripts/setup.py`: drop "or choose `shared` visibility" from
  `_plan_git_exclude`'s no-repository message. Verify with the test asserting it, and a
  test that a fresh clone of a shared `jev` project plans only the runtime state
  location and the `.env` exclude entry.
- [x] 6.2 `plugin/skills/setup/SKILL.md`: step 1's pre-check strips the project's prefix
  (`git rev-parse --show-prefix`) from porcelain paths before matching the harness's own
  paths; step 3 checks `openspec store list --json` for the id it would use and, when
  one is registered, reuses it — no path asked, no `store_path` passed. Update the
  skill-content tests.
- [x] 6.3 `docs/PLAN.md`: C9's heading and Exit say delivered for everything but the
  manual try, matching how earlier phases with open live checks are marked; the fresh
  clone of a `jev` project restores the `.env` entry.
- [x] 6.4 Run `uv run --with pytest pytest`, both `claude plugin validate --strict` calls
  and `openspec validate --all`.

## 7. Third verify findings (revision)

- [x] 7.1 `plugin/scripts/setup.py`: accept a `store_registered` answer (boolean, local
  only, refused with a `store_path` or under shared); with it and no recorded id, plan a
  "reuse store `<id>`" line instead of refusing or registering, and record the id on
  `write`. Run every git call with `LC_ALL=C` in its environment. Label the `.env`
  exclude step's owner "this clone" under shared visibility. Tests: an interrupted
  registration completes through `store_registered`; `store_registered` with
  `store_path` is refused; a non-English `LANG` still reports "no repository"; the
  shared owner label; an update in a fresh clone of a `jev` project restores the `.env`
  entry.
- [x] 7.2 `plugin/skills/setup/SKILL.md` step 3 and its answers example pass
  `store_registered: true` when the store list holds the id; `docs/PLAN.md` C9 mentions
  it. Update the skill-content tests.
- [x] 7.3 Run `uv run --with pytest pytest`, both `claude plugin validate --strict` calls
  and `openspec validate --all`.

## 8. Fourth verify findings (revision)

- [x] 8.1 `plugin/scripts/setup.py`: refuse a `store_path` that resolves inside the
  project's own directory. `plugin/skills/setup/SKILL.md` step 1: run porcelain with
  `-z` (or say how to read quoted paths) so prefix stripping works for paths with
  spaces or non-ASCII characters; step 2's store question names its condition.
  `docs/PLAN.md`: the local table's `.git/info/exclude` owner is `local`; C9's Exit
  names the full manual walkthrough (clean-tree refusal, `jev`/`.env`, a Codex-routed
  `apply`) as owed. Tests for the refusal and the skill text.
- [x] 8.2 Run `uv run --with pytest pytest`, both `claude plugin validate --strict` calls
  and `openspec validate --all`.

## 9. Fifth verify findings (revision)

- [x] 9.1 `README.md`: where it introduces `/harnex:setup`, state that the project must
  be inside a git repository with nothing to commit outside the harness's own files
  (`git init` and a first commit for a new folder), and that setup stops otherwise.
- [x] 9.2 Run `uv run --with pytest pytest`, both `claude plugin validate --strict` calls
  and `openspec validate --all`.
