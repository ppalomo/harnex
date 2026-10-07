## 1. The answers and the plan

- [x] 1.1 In `plugin/scripts/setup.py`, add a `store_path` answer (text, local
  visibility only, refused otherwise and refused empty under `local` when no recorded
  `store_id` exists), and plan a step "register store `<id>` at `<path>`". Verify with
  tests in `tests/test_setup_answers.py` and `tests/test_setup_local.py`.
- [x] 1.2 Add `.env` to the exclude plan when `decision_model` is `jev` and `.git`
  exists (either visibility); extend `_maybe_jev_notice` to say it is excluded, and for
  `shared` that other clones are not protected. Verify with tests asserting
  `git check-ignore .env` after a real write, and `.env`/`.gitignore` unchanged.
- [x] 1.3 Under `local` visibility with no `.git`, plan a `git init` step instead of a
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
  before; `jev` with `git init` pending shows one plan with both lines.

## 2. The skills

- [x] 2.1 `plugin/skills/setup/SKILL.md`: ask where the store lives (step 2 and 3), run
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
