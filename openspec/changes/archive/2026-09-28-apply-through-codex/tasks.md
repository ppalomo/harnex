## 1. Decision questions: `noul` support, `task.route`, `task.scope`, and `decide_many`

- [x] 1.1 Add `rule_threshold_low` to `decide.py`'s question format — required and
      range-checked exactly when `type: noul`, refused for any other type — and require a
      `noul` question's declared options to be exactly `true` and `false`. Verify with
      fixtures: a `noul` file missing `rule_threshold_low` fails to load; a `choice` file
      declaring it fails to load; a `noul` file with options other than `true`/`false`
      fails to load, each naming the file and the field.
- [x] 1.2 Implement `build_request` and `parse_response` for `type: noul`, per the shape
      read from OpenRouter's `jev-tutorial` docs (design.md D2): request criteria
      `{"true": ..., "false": ...}`, response `{"type": "noul", "noul": <float>}`,
      resolving to `true` at or above `rule_threshold`, to `false` at or below
      `rule_threshold_low`, else unresolved carrying `{"true": p, "false": 1 - p}` (the
      response has no second number; `false` is derived). Verify with fixtures for all
      three outcomes.
- [x] 1.3 Add `decide_many(questions: list[tuple[Question, dict]]) -> list[Decision]`,
      sending every distinct question in one request over one shared state object to the
      `jev` backend, and falling back per-question to the same unresolved shape `decide()`
      already returns for `mock` or any failure. Verify with a unit test against a stubbed
      multi-question OpenRouter response fixture, a stubbed hang (every question returns
      unresolved within the time budget), and the `mock` backend (each question gets its
      own prompt, not a merged one). `task.route` and `task.scope` are never batched
      together for one task (task 5.1's note); this task only builds the generic
      mechanism.
- [x] 1.4 Reimplement `decide()` as a one-question call through `decide_many()`. Verify
      every existing `decide()` test from C2 (`phase.route` resolved, below-threshold,
      `jev` unreachable, `mock`) still passes unchanged.
- [x] 1.5 Write `plugin/orchestration/decisions/task-route.yaml` (Choice: codex / claude /
      human; state `task_text`, `paths` — a newline-joined string, not a list; rule ≥
      0.70) and `task-scope.yaml` (Noul; state `task_text`, `changed_paths`, both strings;
      `rule_threshold` 0.85, `rule_threshold_low` 0.35), following the YAML-shaped format
      `phase-route.yaml` already uses. Verify with the existing parser test: both files
      parse with no second colon-free line and no duplicate key.

## 2. The builder role

- [x] 2.1 Write `plugin/orchestration/roles/builder.md` — the tool-agnostic prompt: what a
      task hands it, what it must produce, and the three things it must never do (tick
      `tasks.md`, write outside its scope, touch `openspec/` or `.harnex/`). Verify by
      reading it against `builder-role`'s spec: every ADDED requirement has a line in the
      prompt that states it.
- [x] 2.2 Write `plugin/agents/builder.md`, the Claude fallback binding — frontmatter
      `name: builder`, `tools: Read, Grep, Glob, Edit, Write, Bash`. Verify with the
      role-to-binding correspondence test (mirroring the verifier's C2 test): the prompt
      content matches `roles/builder.md`.
- [x] 2.3 Move the two builder profiles from their old, pre-harnex kit locations into
      `plugin/tools/profiles/`. Verify `claude plugin validate plugin --strict` still
      passes and no other file under `plugin/` names the technologies they name.

## 3. Path, protected-path, and scope checks

- [x] 3.1 Write `plugin/feedback/task_scope_check.py` with `check_declared(task_paths,
      before, after)` and `check_protected(before, after)`, reusing `scope_check.py`'s
      before/after `git status --porcelain=v1 --untracked-files=all` technique. Verify
      with fixtures: a write inside declared paths (no violation), a write outside them
      (violation named), and a write to `openspec/` or `.harnex/` (violation named,
      independent of what was declared).
- [x] 3.2 Wire `check_protected` to run unconditionally for every task, and
      `check_declared` to run only when the task declares paths, falling through to
      `task.scope` (a single `decide()` call once the builder has written, task 1.4) when
      it does not. Verify with a task that
      declares a protected path in its own scope: the write is still refused, and the
      refusal names `task_scope_check.py`, not the task's declared scope.

## 4. The apply loop: fingerprinting, acceptance, fix-or-escalate, recovery

- [x] 4.1 Implement the tree fingerprint (`sha256` of the diff against the change's base
      commit plus a sorted listing of untracked files and their content hashes) in the
      loop script. Verify two identical trees fingerprint identically and any single-byte
      change fingerprints differently.
- [x] 4.2 Implement the run-state file `.harnex/state/apply/<change>.json` — one entry per
      task, atomic write-to-temp-then-rename, transitions `queued → delegated → returned →
      checked → accepted` (or `escalated` off `checked`). Verify the file after each
      transition is valid JSON and a crash mid-write (simulated) leaves the previous valid
      state intact, never a half-written file.
- [x] 4.3 Implement acceptance as the conjunction `apply-command`'s spec lists (builder
      reported done, check exited 0, paths in scope, protected paths unchanged, `HEAD` and
      refs unmoved, fingerprint at acceptance matches the one the check ran against).
      Verify with a fixture where every condition holds but one (each in turn) and confirm
      the task is not accepted in any of those cases.
- [ ] 4.4 Implement the one-fix-attempt step: on a failing check, hand the same builder the
      check's output and current diff once, then check again. Verify a fixture where the
      fix succeeds (task accepted) and one where it does not (task escalated, not retried
      again).
- [x] 4.5 Implement recovery on resume: a `delegated` task triggers the Codex job-status
      lookup first; a lookup failure or no progress past a fixed staleness interval shows
      the diff since the task's base fingerprint and asks keep/discard/re-delegate. Verify
      with recorded run-state fixtures for each of: interrupted mid-`delegated`,
      interrupted mid-`checked`, and a run resumed after every task was already
      `accepted` (nothing is touched).

## 5. `/harnex:apply`

- [x] 5.1 Write `plugin/skills/apply/SKILL.md`. Once, before any task starts: read every
      task from `tasks.md`, ask `task.route` for all of them together through
      `decide_many` (one question per task, that task's own text and paths embedded in
      its own instructions, D2 — never sharing a `task.route`/`task.scope` call), and
      print every decision line up front. Then per task in order: start the routed
      builder, run the declared-path check or, for a paths-less task, a single
      `task.scope` call once the builder has written, run the protected-path check, run
      the check command, apply fix-or-escalate, accept-and-tick or escalate-and-stop.
      Verify by running it against a two-task fixture change with a fake
      `codex-companion` on `PATH` that records what it was asked and returns a canned
      diff: both tasks land ticked, with evidence.
- [ ] 5.2 Verify the interruption story end to end: start `apply` against the fixture
      change, kill it mid-task, run it again, confirm the already-accepted task is
      untouched and the interrupted one resumes or asks, per task 4.5's cases.

## 6. Restating the `sdd` and `code` rules

- [x] 6.1 Edit `plugin/context/rules/code/no-scope-beyond-the-task.md`'s `**Enforced by:**`
      line to name the path check, `task.scope`, and the protected-path check
      (`plugin/feedback/task_scope_check.py`) in place of "the scope question of pillar
      3". Verify the rule-sets rendering test still passes with the new body.
- [x] 6.2 Edit `plugin/context/rules/sdd/builders-never-tick-tasks.md`'s frontmatter to
      `enforced_by: check` and add a body line naming the apply loop's ticking step as the
      enforcer. Verify the rule-sets frontmatter check still passes.

## 7. Docs and manual verification

- [x] 7.1 Append `apply`'s manual steps to `docs/smoke.md`, per the format C1a fixed:
      propose a two-task change, run `/harnex:apply`, watch the decision line, watch the
      check and evidence, break a test on purpose and watch the one-fix escalate/accept,
      interrupt and resume. Verify by actually walking the steps once against a scratch
      change in this repository.
- [x] 7.2 Update `docs/PLAN.md` to mark C3 delivered — the "Delivers," "You try it,"
      "Tests," and "Exit" bullets matching what actually landed, any correction the build
      surfaced recorded under "What changed the plan," and the roadmap line for C4
      unchanged beneath it. Verify `docs/PLAN.md` still describes the repository as it is,
      per this project's own "Before committing" checklist.
