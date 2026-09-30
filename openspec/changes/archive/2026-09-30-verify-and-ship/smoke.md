## Task 9.2 — manual walkthrough

Run on a scratch project (`/private/tmp/harnex-smoke-verify-and-ship`, git-initialised,
harnessed with `setup.py write` from the installed plugin — sets `git, code, sdd`,
`decision_model: mock`), driving a real, trivial change (`add-greet-script`: a `greet(name)`
function and its test) through `explore → propose → apply → review → verify → ship`.

**Bootstrapping note, the same one `shell-guard`'s own `smoke.md` used for the guard
script:** at the time of this walkthrough, `review`, `verify`, and `ship` are brand new,
uncommitted files in this dev checkout — the installed
plugin (`~/.claude/plugins/cache/harnex/harnex/0.1.0/`) predates this whole change and has
no such skills. `explore`, `propose`, and `apply` genuinely exist there, so those three
steps below are real `Skill` tool invocations. `review` and `verify`'s "start the
reviewer/verifier" steps are simulated by handing this dev checkout's own current role-prompt
content directly to a generic Claude subagent (not the `reviewer`/`verifier` subagent
types, which either don't exist yet or would load stale cached prompts) — this exercises
the real, current role text without needing it installed. `verify_checks.py` and
`ship_gate.py` are run directly from this dev checkout's own path, for the same reason.
`ship`'s `git push` / `gh pr create` steps are not exercised — no real remote exists for a
throwaway scratch project, and creating one is out of scope; this is called out honestly
below rather than faked.

### 1 — `explore` and `propose` (real skill invocations)

`Skill(harnex:explore)` printed `Decision (advice): explore → unavailable (mock_backend)`
and, given the idea was already concrete, moved straight to suggesting `propose`.
`Skill(harnex:propose)` printed `Decision (advice): propose → unavailable (mock_backend)`,
ran `openspec new change "add-greet-script"`, and walked through writing `proposal.md`,
`specs/greeting/spec.md`, `design.md`, and `tasks.md` (one task: write `greet.py` and
`tests/test_greet.py`). The scope check reported "Nothing was written outside the change's
own directory."

`propose`'s own step 6 (starting the real, already-installed `verifier` subagent) found one
genuine ambiguity, worth recording as an example of the role doing its actual job:
`design.md` decides where `greet.py` lives but never says where its test does; `tasks.md`
then places it at `tests/test_greet.py` unilaterally. The verifier judged this an
unresolved ambiguity, not a confident violation, and said so plainly rather than picking a
reading. `propose` does not gate on this review, so the change proceeded to `apply`
unchanged.

### 2 — `apply` (real skill invocation)

`Skill(harnex:apply)` routed the one task (`task.route` was also `mock_backend`; the
Claude fallback binding was used), started the real `harnex:builder` subagent, and
accepted the result: `greet.py` and `tests/test_greet.py`, both new, nothing outside
declared scope, the test passing under `uv run --with pytest pytest`. `tasks.md`'s only
task was ticked.

### 3 — `review` never affects `ship` (structural + a real run)

`plugin/scripts/ship_gate.py` never reads anything a review produces — confirmed by
reading its source: the only record it reads is `.harnex/state/verify/<change>.json`,
written by the verify step, never by review. `grep -n "review" plugin/scripts/ship_gate.py`
turns up only the *verifier's* own review record, not `/harnex:review`'s reviewer role.

A real simulated `review` run (the reviewer role's current content, on `opus`, given the
diff on disk) found two minor code-quality points — worth showing as genuine output, not
fabricated for this test:

> 1. `tests/test_greet.py`'s `sys.path.insert(...)` bootstrap is fragile and
>    non-idiomatic; a root `conftest.py` would be the conventional fix and avoids
>    duplicate `sys.path` entries as the suite grows.
> 2. `greet.py`'s `greet(name)` has no type annotation or docstring — flagged as a
>    judgement call, not a defect, given the design's own "smallest thing that satisfies
>    the spec" decision.

Neither finding touched `ship_gate.py`'s own decision in step 5 below, which was computed
without ever reading this review's output — matching the spec's own "review's findings
never affect `ship`" requirement both by code inspection and by this run's own outcome.

### 4 — `verify`'s severity-carrying findings, twice over

First pass, before fixing anything: `verify_checks.py` ran with the scratch project's
initial `check_command: true` (a no-op). The simulated `verifier`, in `/harnex:verify`
mode, caught this as a real, **blocking** finding:

> The facts file records `check_command: "true"` with `exit_status: 0` and empty output.
> `true` is a shell no-op — it proves nothing about whether `tests/test_greet.py` passes,
> which is exactly what `tasks.md`'s own verify line requires. A zero exit from `true`
> cannot stand in for "the test passes."

This is a genuine bug in the scratch project's own setup (an unrealistically weak
`check_command`), not a defect in the harness — fixed for real: `.harnex.yml`'s
`check_command` became `uv run --with pytest pytest`. Re-running `verify_checks.py`
produced a real pytest pass (`1 passed`), and the re-run verifier found no blocking issue,
only one **advisory** finding: the `.harnex.yml` fix itself sits outside `proposal.md`'s
declared Impact ("one new module and one new test file") — a real, correctly-scoped
observation, not a defect in the change's own code.

Both severities were shown in the review exactly as returned, unedited — confirming
`verify`'s severity-carrying findings are genuinely produced and surfaced, not merely
documented as a possibility.

**Corrected follow-up:** running the check command itself (`pytest`) leaves `__pycache__/`
behind. This scratch project has no `.gitignore`, so those directories are untracked, but
`verify_checks.py` now fingerprints the tree after the command completes. The matching
`ship_gate.py check` immediately after `verify` therefore sees the same tree and proceeds;
the cache is only a stale-fingerprint cause if it changes after verification.

### 5 — `ship` refuses with a named reason when no `verify` run exists yet

Before any `verify` run for this change:

```
$ uv run plugin/scripts/ship_gate.py check --project <scratch> --change add-greet-script
{"decision": "refuse", "reason": "no run found", "findings": []}
$ echo $?
1
```

### 6 — `ship` refuses again when the tree is dirtied after a `verify` run

After a fresh, matching `verify` record was written (`ship_gate.py record`, using the
facts file's own `base_ref` and `fingerprint` — `check` returned `"go"` at this point, with
the one advisory finding from step 4 attached), a tracked file was deliberately edited:

```
$ echo "# a stray edit" >> greet.py
$ uv run plugin/scripts/ship_gate.py check --project <scratch> --change add-greet-script
{"decision": "refuse", "reason": "stale fingerprint", "findings": [{"severity": "advisory", ...}]}
$ echo $?
1
```

### 7 — `ship` proceeds once a fresh, clean `verify` run exists and the person says yes

The stray edit was reverted, `verify` re-run for a matching fingerprint, and the gate
re-checked:

```
$ uv run plugin/scripts/ship_gate.py check --project <scratch> --change add-greet-script
{"decision": "go", "reason": null, "findings": [{"severity": "advisory", "summary": "The diff modifies .harnex.yml ..."}]}
$ echo $?
0
```

With the advisory finding shown and an explicit yes given, `ship`'s own step 3 ran for
real, inside the scratch project only:

```
$ git add -A && git commit -m "feat: add greet script

Add a tiny greet(name) helper returning a greeting, with a unit test,
to smoke-test the harness's explore-to-ship pipeline."
```

### 8 — the resulting commit carries no AI author or co-author line

```
$ git log -1 --format='%H%n%B'
54b0f4d3bbdfd79a86a71aa6f98ff2e9e12ca6d9
feat: add greet script

Add a tiny greet(name) helper returning a greeting, with a unit test,
to smoke-test the harness's explore-to-ship pipeline.
```

No `Co-Authored-By` or any other AI-attribution line — matching `ship/SKILL.md`'s own step
3 instruction and `AGENTS.md`'s git rule, deliberately followed here even though a
different, session-level convention would otherwise have applied one to a commit made in
this conversation.

### 9 — the local-only remainder of `ship`, exercised for completeness

`git push` and `gh pr create` were **not** exercised — no real remote exists for this
scratch project, and creating one is out of scope for a local smoke test; said here
plainly rather than faked. `openspec archive add-greet-script --yes --json` needs no
remote, so it was run for real: it archived the change to
`openspec/changes/archive/2026-09-29-add-greet-script/` and synced its delta spec into
`openspec/specs/greeting/spec.md`, exit `0`. One nuance worth naming: the archive step
leaves the scratch project's working tree with new, uncommitted paths (the archived copy
and the synced spec) — `ship/SKILL.md` does not commit again after archiving, so a real
project would carry that as a follow-up commit rather than have `ship` fold it into the
one already made in step 7.

## Result

All six required confirmations passed:

1. `review`'s findings never affect `ship` — confirmed by code (`ship_gate.py` reads only
   the verifier's own record) and by this run (a real review ran with findings, `ship`'s
   own decision never referenced them).
2. `verify`'s severity-carrying findings are shown — a real `blocking` finding (step 4,
   first pass) and a real `advisory` finding (step 4, second pass; step 7) were both
   surfaced exactly as returned.
3. `ship` refuses, named `"no run found"`, before any `verify` run (step 5).
4. `ship` refuses again, named `"stale fingerprint"`, after the tree is dirtied post-`verify`
   (step 6).
5. `ship` proceeds to the person's explicit yes once a fresh, clean `verify` run exists
   (step 7).
6. The resulting commit carries no AI author or co-author line (step 8).

The Playwright/UI path was not exercised (proposal's own Non-goals; out of scope for this
task). Two genuine, non-blocking observations surfaced along the way and are recorded
above rather than silently fixed: a check-command's own cache artifacts can spuriously
stale a fingerprint one call later without a project `.gitignore`, and `ship`'s archive
step leaves its own writes uncommitted.
