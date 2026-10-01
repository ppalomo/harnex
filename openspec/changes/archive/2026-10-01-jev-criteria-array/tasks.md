## 1. `decide.py`: the `score` request and response shapes

- [x] 1.1 In `_question_payload` (`plugin/scripts/decide.py`), build `criteria` for a
      `score` question as a JSON array of `question.options` keys, in declaration order
      (`list(question.options)`), instead of `dict(question.options)`; leave `choice` and
      `noul` untouched. Verify by running the corrected live request shape against
      `https://openrouter.ai/api/alpha/decisions` once by hand (not in the test suite) and
      confirming HTTP 200, the same way this proposal's own live checks were made.
- [x] 1.2 In `parse_response`'s `score` branch, read the response's `legend` field, build
      an index→option-name map from it, and translate `answer["probabilities"]` (keyed by
      stringified index) into a dict keyed by option name before any threshold check or
      return value — every `probabilities` dict this function returns or journals must be
      keyed by option name, never by index. Verify with `uv run --with pytest pytest
      tests/test_decide.py -k score -v`.
- [x] 1.3 Update `tests/test_decide.py`'s `score` fixtures to the corrected shapes:
      `test_score_build_request_includes_every_option_as_criteria` asserts `criteria ==
      ["destructive", "read_only", "reversible"]` (array, not object);
      `SCORE_RESPONSE` and the two response fixtures in
      `test_score_two_options_crossing_resolves_the_earliest_declared` and
      `test_score_with_no_option_crossing_is_unresolved` move `probabilities` to
      index-keyed (`{"0": ..., "1": ..., "2": ...}`) plus a matching `legend` field, and
      every assertion against `outcome["probabilities"]` expects the name-keyed result
      `parse_response` now produces, not an echo of the raw response. Verify with `uv run
      --with pytest pytest tests/test_decide.py -v`.
- [x] 1.4 Add one new test fixturing the exact live response shapes recorded in this
      proposal (`legend` and `probabilities` both present, index-keyed, summing to 1) to
      pin the contract going forward — name it so a future contract drift is obvious from
      the test name alone (for example
      `test_score_response_shape_matches_the_live_api_contract`). Verify it fails if
      `legend` is removed from the fixture (confirm by temporarily deleting it, observing
      the failure, then restoring it) before moving on.

## 2. `decision-model` spec: correct the `score` probability-distribution claim

- [x] 2.1 Confirm `openspec/changes/jev-criteria-array/specs/decision-model/spec.md`'s
      `MODIFIED` requirement already reflects the array `criteria`, the `legend` mapping,
      and the corrected "sums to 1" claim (it does, as written) — no code task here, just
      the gate before archiving: `openspec validate --change jev-criteria-array --strict`
      passes once section 4's tasks are done.

## 3. `guard.py`: inert default list without the project's own `safety` set

- [x] 3.1 In `plugin/control/guard/guard.py`, import `setup.py` by path the same way
      `canary.py` does (`sys.path.insert(0, str(Path(__file__).resolve().parents[2] /
      "scripts"))`, then `import setup as setup_script`), and add `_safety_enabled(project:
      Path) -> bool`: `False` when `project / setup_script.CHOICES` does not exist, `False`
      when it parses but `"safety"` is not in `choices.get("sets", [])`, `True` for every
      other case including a read or parse failure (`OSError`, `setup_script.SetupError`) —
      an error is never grounds to allow, matching "The guard never allows on its own
      error". Verify with a standalone call against a fixture directory in each of the
      four states (missing, `safety` absent, `safety` present, malformed).
- [x] 3.2 Give `classify_segments` a `safety_active: bool = True` keyword-only parameter;
      when `False`, skip `_classify_against_patterns` for the default list entirely and use
      `Classification("allow")` as `default` — leave the existing default/role combination
      logic (the rest of the function) untouched, since D4 depends on it still letting a
      role's own deny/ask override that forced allow. Give `classify_command` the same
      `safety_active: bool = True` parameter, threading it straight through to
      `classify_segments` (not computed internally — the caller decides). Verify the
      existing `tests/test_guard.py` tests that call `classify_segments`/`classify_command`
      directly without passing `safety_active` still pass unchanged (they default to
      `True`, so this task alone should not change their outcome).
- [x] 3.3 In `_classify_hook_payload`, compute `safety_active = _safety_enabled(cwd)` right
      after resolving `cwd`, and pass it into `classify_command`. Verify with `uv run
      --with pytest pytest tests/test_guard.py -k pretool_hook -v` (expect failures here
      until task 4 updates the affected fixtures — that is expected at this point, not a
      regression to chase down yet).

## 4. `guard.py` tests: the fixture ripple from gating on `.harnex.yml`

- [x] 4.1 The `project` fixture (`tests/conftest.py`) is an empty directory with no
      `.harnex.yml`, so every existing `test_pretool_hook_*` test in `tests/test_guard.py`
      that currently expects `deny`/`ask` (not the inertness being added) now needs that
      project to declare `sets: [safety]` before the hook runs, or it will get `allow`
      unconditionally and silently stop testing what its name says it tests. Add a small
      helper (for example `_write_harnex_yml(project, sets=["safety"])`, mirroring the
      inline write already at line ~421) and call it at the top of:
      `test_pretool_hook_asks_for_an_ask_pattern`,
      `test_pretool_hook_uses_guard_risk_outcomes` (both parametrize cases),
      `test_pretool_hook_asks_when_guard_risk_backend_is_unresolved`,
      `test_pretool_hook_asks_on_a_malformed_patterns_fixture`,
      `test_pretool_hook_with_a_missing_interpreter_cannot_produce_a_guard_decision`,
      `test_pretool_hook_crashing_before_main_emits_no_guard_decision`,
      `test_pretool_hook_bounds_a_real_hanging_decide_process`, and
      `test_pretool_hook_allows_a_read_only_command_from_payload_cwd` (so it keeps testing
      the allowlist, not inertness). Verify with `uv run --with pytest pytest
      tests/test_guard.py -k pretool_hook -v` — all green, each for the reason its name
      states.
- [x] 4.2 Add `test_pretool_hook_is_inert_without_harnex_yml`: no `.harnex.yml` in
      `project`, a command that would otherwise match an ask pattern (for example `git push
      origin main`) resolves to `allow`, and nothing is appended to
      `.harnex/state/guard/journal.jsonl`. Verify by running it and inspecting the journal
      file is absent or unchanged.
- [x] 4.3 Add `test_pretool_hook_is_inert_without_the_safety_set`: `.harnex.yml` present,
      `sets: [git]` (no `safety`), same ask-pattern command as 4.2 resolves to `allow`,
      nothing journalled. Verify the same way.
- [x] 4.4 Add `test_pretool_hook_stays_active_when_harnex_yml_is_malformed`: `.harnex.yml`
      present but not valid (reuse the malformed-fixture convention already in this file),
      same ask-pattern command resolves to `ask`, not `allow` — the failure must not look
      like a choice. Verify by running it.
- [x] 4.5 Add `test_pretool_hook_role_addition_applies_while_default_list_is_inert`: no
      `.harnex.yml`, a `builder`-scoped command that the role's own deny list restricts
      (reuse one of `builder-never-touches-protected-paths`' patterns, e.g. `rm -rf
      openspec/foo`) still resolves to `deny`, proving D4's "role additions stay active
      regardless" even though the default list is inert. Verify by running it.
- [x] 4.6 Run the full suite once, `uv run --with pytest pytest`, and fix anything the
      prior steps missed — in particular re-check every other `project`-fixture-based test
      elsewhere in the repository (`tests/test_decide.py`, `tests/test_setup.py`, etc.) for
      an assumption about the guard's own behavior with no `.harnex.yml`; only
      `tests/test_guard.py`'s `test_pretool_hook_*` family is expected to need changes,
      but confirm rather than assume.

## 5. This repository's own bootstrapping opt-out

- [x] 5.1 Comment out `- safety` in this repository's own `.harnex.yml`, now that the
      inertness fix (section 3) makes that opt-out behave correctly. Verify with
      `tests/test_guard.py -k is_inert` (already covers the mechanism) and by hand: a
      command that would otherwise ask (e.g. `rm -rf foo`) resolves to `allow` with
      nothing journalled, in this repository, with `safety` commented out.

## 6. Close out

- [x] 6.1 `uv run --with pytest pytest` passes in full.
- [x] 6.2 `claude plugin validate plugin --strict` and `claude plugin validate . --strict`
      pass, and `openspec validate --all` passes.
- [x] 6.3 Update `docs/PLAN.md`'s `C4` entry ("What it taught us") with one bullet
      recording both bugs found and fixed here — the `score` wire-format mismatch, never
      exercised live until now, and the guard's missing `.harnex.yml` gate — the same way
      every other phase's retrospective bullet is written, and confirm
      `docs/PLAN.md` still describes the repository as it is.
