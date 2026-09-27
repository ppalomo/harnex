## 1. Recorded payloads

- [x] 1.1 Add `tests/fixtures/hooks/2.1.267/` with `stop.json`, `subagent-stop-general-purpose.json` and `subagent-stop-explore.json`, recorded from a real Claude Code 2.1.267 session (re-record in a scratch project with a dumping `Stop`/`SubagentStop` hook if the raw recordings are gone), with paths replaced by `/project` and `/transcripts/…` and ids by fixed placeholders; verify the private-name check passes over them and each still parses as JSON with `last_assistant_message`.
- [x] 1.2 Add a fixture test asserting `stop.json` carries the answer text in `last_assistant_message` and fails naming the field and the host version when it does not; verify it passes, and fails when the field is renamed in a copy.

## 2. The canary check (pillar 5)

- [x] 2.1 Write `plugin/feedback/canary/canary.py` with the inline script metadata of `setup.py`: read the input from stdin, resolve the project root (D3), stay inert without `.harnex.yml` or without the `canary` set, read the file with setup's `parse_choices` (D4), compare per D5, and emit at most one `systemMessage` (D2), always exiting 0 and never emitting a block decision; verify with `uv run plugin/feedback/canary/canary.py < tests/fixtures/hooks/2.1.267/stop.json` in a scratch project.
- [x] 2.2 Handle failure per D7 — malformed stdin, unreadable `.harnex.yml`, set chosen without a word, unexpected error — each producing a "not checked" message with the reason, and a missing or empty answer producing nothing; verify with the unit tests of 2.3.
- [x] 2.3 Add `tests/test_canary.py` over the recorded `stop.json` and cases derived from it in code: word present, word in bold/italics/code, word missing, word mid-answer, word in another case, a project word other than the proposed one, `.harnex.yml` absent, set not chosen, set chosen without a word, unreadable `.harnex.yml`, field absent, field empty, malformed stdin; each asserts exit 0, no block decision, and the exact presence or absence of a warning; verify `uv run --with pytest pytest tests/test_canary.py` passes.
- [x] 2.4 Add `plugin/hooks/hooks.json` declaring the `Stop` hook of D6 and no `SubagentStop`; verify `claude plugin validate plugin --strict` passes and `claude plugin details harnex` (after reinstalling from the checkout) lists one hook.
- [x] 2.5 Add a test that starts the hook as a real process with the command declared in `hooks.json` (`${CLAUDE_PLUGIN_ROOT}` substituted, `CLAUDE_PROJECT_DIR` set to a temporary project), for word present, word missing and no `.harnex.yml`, asserting the output and that it returns well inside the declared timeout; skip with a reason when `uv` is absent; verify it passes.

## 3. The rule and the walk back (pillar 1)

- [x] 3.1 Revise `plugin/context/rules/canary/canary-ends-every-answer.md`: the reason says a missing word is a signal that this instruction was not followed and that the rules may no longer be in effect — not that they are gone — and the enforcer line names `feedback/canary/canary.py` and says it runs on the main session's answers only; verify the rule-format tests pass.
- [x] 3.2 Add the two-way walk of the modified `rule-sets` requirement: every `enforced_by: hook` rule names a script that exists and that a hook in `hooks.json` runs, and every hooked script is named by a rule; verify it passes, fails when the enforcer path in the rule is changed, and fails when a hook with an unclaimed script is added (seeded faults in the test).
- [x] 3.3 Regenerate the committed rendering snapshots that include the canary rule (`tests/snapshots/`), review the diff is the rule's text only, and verify the full suite passes.

## 4. Documents

- [x] 4.1 Record the `SubagentStop` finding in `docs/decisions/2026-09-27-the-canary-checks-the-main-session-only.md`: the question, the recording, the two subagent types, the decision and what would reopen it (C2's own agents); verify it links the fixtures.
- [x] 4.2 Update `plugin/feedback/README.md` (what `canary/` holds now, "Filled by" moved on) and append the `canary-enforces-itself (C1d)` section to `docs/smoke.md`: word present, word removed from `.harnex/rules.md` → warning, set removed → silence, project without setup → silence, a deliberate miss per host version; verify the steps by running them once in a scratch project in the desktop app and recording the version.
- [x] 4.3 Run the full pre-commit list of `AGENTS.md` — `uv run --with pytest pytest`, both `claude plugin validate --strict`, `openspec validate --all` — and verify all pass.
- [x] 4.4 Update `docs/PLAN.md` to match what landed: §3 and decision 7 (main session only), §5 layout (`hooks/hooks.json`), §11 C1d marked delivered with what it taught us, §13 (the answered question moved to "Answered since"), and regenerate the diagrams if the layout or workflow changed (`python3 docs/diagrams/build.py`); verify the plan describes the repository as it is.
