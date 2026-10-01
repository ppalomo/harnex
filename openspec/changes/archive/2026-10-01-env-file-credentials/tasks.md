## 1. `decide.py` reads a project-local `.env` as a fallback

- [x] 1.1 In `plugin/scripts/decide.py`, add `resolve_api_key(project: Path) -> str | None`: return `os.environ.get("OPENROUTER_API_KEY")` if set, otherwise parse `project / ".env"` for a line `OPENROUTER_API_KEY=<value>` (first `=` splits it, blank lines and `#` comments skipped, one matching pair of surrounding quotes stripped from `<value>`), returning `None` if the file is absent, unreadable, or does not declare the key. Wire `main()`'s existing `api_key=os.environ.get("OPENROUTER_API_KEY")` call to `api_key=resolve_api_key(project)` instead. Verify with `uv run --with pytest pytest tests/test_decide.py -k resolve_api_key` covering: environment set and `.env` absent; environment unset and `.env` declares the key; both set (environment wins, `.env` value never used); `.env` absent entirely; `.env` present but without the key; a quoted value; a malformed line (no `=`).
- [x] 1.2 Confirm the decision journal never carries the key's value regardless of source, by extending the existing journal test in `tests/test_decide.py` with a case where the key came from `.env`.

## 2. `setup.py` shows the `.env` notice for `jev`, and touches nothing

- [x] 2.1 In `plugin/scripts/setup.py`, add a notice to `plan.notices` inside `build_plan` (or `_plan_project_files`) naming `.env` at the project root, the key `OPENROUTER_API_KEY=` it must declare, and that the person keeps it out of version control — shown only when `answers.decision_model == "jev"`. Verify with a new case in `tests/test_setup_survey.py`: `plan` output (both `render_plan` text and `plan_as_json`) includes the notice when `decision_model` is `jev` and omits it when `mock`.
- [x] 2.2 Add a test in `tests/test_setup_write.py` asserting a `write` run with `decision_model: jev` never creates, reads, or modifies `.env` or `.gitignore` in the project — the write's file set is unchanged from a `mock` run except for `.harnex.yml`'s own recorded `decision_model` value.

## 3. Update the plan

- [x] 3.1 Update `docs/PLAN.md`'s `C2 · explore and propose` entry to note that `decide.py`'s `jev` backend now falls back to a project-local `.env` for `OPENROUTER_API_KEY` when the environment does not carry it.
- [x] 3.2 Update `docs/PLAN.md`'s `C1c · setup writes a project` entry to note that its plan shows an informational `.env` notice when `decision_model` is `jev`, touching neither `.env` nor `.gitignore` — consistent with the "runtime state ... without touching the project's rules" decision already recorded there.
