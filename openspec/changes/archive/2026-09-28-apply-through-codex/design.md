## Context

See proposal.md for why. What exists today, and what this design builds on:

- `docs/PLAN.md` §10 already fixes the loop's own contract in detail — who accepts and
  ticks, that evidence is bound to a fingerprint of the tree it describes, that a retry is
  one fix not a re-check, that interrupted work resumes from recorded state, and that
  branch/worktree isolation is harnex's own job because `/codex:rescue` has none of its
  own. This design does not re-decide any of that; it says how each piece is built.
- `docs/PLAN.md` §8's table already fixes `task.route` (Choice: codex / claude / human,
  state = one task's text and its file list, same 0.70 rule as `phase.route`) and
  `task.scope` (Noul, state = task text and changed paths, asked only when a task declares
  no paths, ≥ 0.85 in scope, ≤ 0.35 out of scope, between → ask). Neither needs a change to
  `decide.py`'s own code — C2's design (D1–D2) already built the question format and the
  `resolved: false` contract to take exactly this.
- `S1`'s decision note is the other input: no targeting of a branch or worktree from
  Codex's own side, a job record that only ever says `running` or `done` with no liveness
  check, and a sandbox toggle read from source, not observed. `apply` therefore owns
  checkout/worktree creation and passes `--cwd`, and treats `running` as untrustworthy
  without its own staleness rule.
- `C2`'s D4 already flagged the split this design reuses: "`C3`'s `builder` needs the
  identical split (one Codex-side adapter, one Claude-subagent-side adapter, one shared
  role prompt)". The verifier's own split (`orchestration/roles/verifier.md` +
  `agents/verifier.md`) is the precedent, extended here to two bindings instead of one.
- `plugin/context/rules/code/no-scope-beyond-the-task.md` already says `enforced_by:
  decision`, naming "the scope question of pillar 3, asked of the decision model with the
  task's text and the paths that changed" — written before this change existed, and
  slightly wrong for what this design actually builds: most tasks declare their own paths
  and are checked deterministically (D3 below); the decision model is asked only for the
  minority that declare none. The rule's body is corrected to say so.
- `plugin/context/rules/sdd/builders-never-tick-tasks.md` already says `enforced_by:
  none`. This change gives it a real enforcer for the first time.

## Goals / Non-Goals

**Goals:**

- A task with declared paths is checked deterministically — no network call, no model
  judgement, on the critical path of every task.
- The builder's write and tick boundary hold identically whichever binding runs it, so a
  Codex outage never changes what a task is allowed to touch.
- Every fact `docs/PLAN.md` §10 lists for acceptance is a fact the loop can point to in its
  run state, not a summary it trusts from the builder's own report.
- An interrupted `apply` is safe to run again, by default, without the person having to
  know which task was mid-flight.

**Non-Goals:**

- `guard.py`, `patterns.yaml`, the `PreToolUse` hook, or anything that stops a command
  *before* it runs — `C4`. This design's checks all run after a builder has already
  written; nothing here gates what a builder is allowed to attempt.
- `/harnex:verify` and `/harnex:ship` — `C5`. `apply`'s own acceptance is not the
  verifier's coherence review; a task can be accepted here and still be found wanting by
  `verify` later.
- Getting a live Codex run to succeed against this account's own entitlement gap. `apply`
  is built and tested against a fake `codex-companion` on `PATH` (per `docs/PLAN.md`
  §11's own test plan) and against the Claude fallback binding directly; a first live
  Codex run, once the account issue clears, is this change's own "try it" step for that
  path specifically, same as C2 left `jev`'s first live call as its own remaining step.
- Scoping one shared `state` object per item inside a batched `decide_many()` call — a
  shape neither OpenRouter's docs nor a live call confirm. `task.route` is batched across
  every queued task instead, each with its own self-contained `instructions` and an empty
  `state`, needing no such scoping (D2). `task.route` and `task.scope` are never batched
  together for the same task, since `task.scope`'s own state does not exist until after
  that task's builder has already written.
- `guard.risk`'s `score` type, or `guard.py` itself — `C4`'s to add; `noul` is the only
  new question type this change teaches `decide.py`.

## Decisions

### D1 · The builder role: one prompt, two bindings, the verifier's split reused

`plugin/orchestration/roles/builder.md` — tool-agnostic: what a task hands it (the task's
own text, its declared paths if any, the check command), what it must do (produce a diff,
run nothing it was not asked to run, report done or report why not), what it must never do
(tick `tasks.md`, write outside its scope, touch `openspec/` or `.harnex/`).

Two bindings implement it:

- `plugin/agents/builder.md` — the Claude fallback: frontmatter `tools: Read, Grep, Glob,
  Edit, Write, Bash`, scoped by the same path check every binding is scoped by (D3); no
  tool grants it a way to touch `tasks.md` more directly than any other file under
  `openspec/`, so the tick boundary holds by the same mechanism D4 of C2 used for the
  verifier's read-only boundary, just for a narrower slice: it *can* write, but not there.
- The Codex binding — reached through `/codex:rescue`, given the task's text and the
  checked-out branch or worktree path (`--cwd`, per S1). Codex's own sandbox toggle is not
  observed live (S1), so this binding is not trusted to self-report scope; D3's checks run
  against its diff exactly as they run against the Claude binding's, with no exception.

*Alternative considered:* trust each binding's own tool restrictions (Codex's sandbox,
Claude's file-scoped tools) as the only boundary, skipping D3's post-hoc checks. Rejected:
S1 found Codex's sandbox toggle is read from source, never observed running, so a Codex
job's own restriction is not evidence of anything; the loop needs a check it runs itself,
against both bindings equally, or the boundary is only as strong as the binding the person
happens not to be using.

### D2 · `task.route` and `task.scope`: two more question files, one batched call added

`plugin/orchestration/decisions/task-route.yaml` and `task-scope.yaml`, in the same
YAML-shaped format C2's D2 built (flat `key: value` frontmatter, a `---` line, prose
below). `decide.py`'s own `_validate_state` (C2) already refuses any state field that is a
list or tuple, so both files carry their path lists as a single newline-joined *string*
field, not a JSON array — the "embed it in the question's own text" alternative the
never-index-by-position rule already names, applied to the state object instead of the
prose, which needs no change to `_validate_state` at all. `task.route`'s state is keyed
`task_text` and `paths` (the task's own declared paths, or an empty string when it
declares none); `task.scope`'s is `task_text` and `changed_paths` (what the builder
actually touched). Neither ever holds more than one task's own handful of paths, so a
string is not a loss of structure — it is what a person reading the same state would
write by hand.

`task.scope` is `type: noul`, the format's first use of a type besides `choice`. Read
from OpenRouter's own tutorial (`docs/guides/community/jev-tutorial`, fetched while
designing this change, since C2's D3 never needed to): a `noul` question's request entry
is `{"type": "noul", "instructions": "...", "criteria": {"true": "...", "false": "..."}}`
— `criteria` declares exactly the two fixed keys `true` and `false`, reusing the question
file's existing `option.*` convention (`option.true`, `option.false`), now required to be
exactly those two names when `type: noul`. The response is `{"type": "noul", "noul":
0.96}` — one probability, no separate confidence field, the probability *is* the
confidence. `task-scope.yaml`'s `option.true` reads "The write is in scope for this
task," `option.false` "The write is out of scope." A `noul` question needs a second
threshold `docs/PLAN.md` §8 already fixes (0.85 / 0.35) that `choice` never needed, so the
question format gains one new optional field, `rule_threshold_low` — required exactly
when `type: noul`, refused for any other type, parsed and range-checked the same way
`rule_threshold` already is. The response carries one probability, `p` (`answer["noul"]`);
`decide.py` reports `{"true": p, "false": 1 - p}` since there is no second number to read.
It resolves a `noul` answer to `true` at or above `rule_threshold`, to `false` at or below
`rule_threshold_low`, and returns unresolved, carrying that same pair, strictly between the
two.

`decide.py` also gains `decide_many(questions: list[tuple[Question, state]]) ->
list[Decision]`, sending every *distinct* question in one request over one shared state
object, when the backend is `jev`. `task.route` and `task.scope` cannot be batched
*together* for one task — `task.route` is asked before a builder starts, to pick the
binding; `task.scope` is asked after a builder has already written, since its own state
(`changed_paths`) does not exist until then. Asking them in the same call would mean
asking `task.scope` about a diff that has not been produced yet, so this change does not
attempt that shape.

What `decide_many` batches instead is `task.route` *across every task `apply` is about to
run*, once, at the start of a run — every task's own text and declared paths are already
known from `tasks.md` before any builder starts, so nothing about this shape depends on
a builder having run first. Rather than one shared `state` scoped per task (a shape
neither OpenRouter's docs nor a live call confirm, so this design does not lean on it),
`apply_loop.py` builds one `Question` per task at call time — same `type`, `options`, and
`rule_threshold` as `task-route.yaml`, but its own id (`task.route#<task index>`) and its
own `instructions`, with that task's own text and declared paths embedded directly into
the instructions string. Every item's `state` is passed empty, so `build_batch_request`'s
state-merging never has anything to merge — each question is fully self-contained, the
"embed it in the question's own text" alternative the never-index-by-position rule already
names, applied to build one call instead of one call per task. This is the batching shape
`docs/PLAN.md` §8 actually asks for ("when a change has several such tasks queued at once,
one batched call beats one call per task"), built without guessing at anything the docs
do not confirm. `task.scope` stays a single `decide()` call per paths-less task, made once
that task's builder has written and `changed_paths` is known — never batched with
anything. `decide()` stays a one-question convenience over `decide_many()`; every existing
caller (`explore`, `propose`, C2's own test surface) sees no change in behaviour.

*Alternative considered:* batch `task.route` and `task.scope` together for one task,
sharing one state object (an earlier draft of this design). Rejected on a re-read of the
loop's own order of operations (D6): `task.scope`'s state cannot exist before the builder
it is judging has already run, so nothing about the two questions is ever simultaneously
askable. *Also considered:* one `decide()` call per task, in sequence, deferring
`decide_many()` entirely. Rejected: every task's `task.route` inputs are known upfront
from `tasks.md`, so batching them at the start of a run is a real reduction in round trips
that costs one function and no assumption about the API this design cannot back with a
documented shape.

### D3 · The path check and the protected-path check: one script, two functions, no network

`plugin/feedback/task_scope_check.py` (one module, following C2's D5 precedent of a single
script per check rather than a family of near-identical ones):

- `check_declared(task_paths, before, after) -> Violation | None` — a pure set
  comparison, reusing `scope_check.py`'s before/after `git status
  --porcelain=v1 --untracked-files=all` technique (C2 D5) rather than the fingerprint
  (D5's own "not before" reasoning — the fingerprint's point is comparing the *same* tree
  before and after a re-run, which this check does not need either; it compares one
  builder's before/after against a static declared list).
- `check_protected(before, after) -> Violation | None` — the same technique against the
  fixed list `openspec/`, `.harnex/` (`docs/PLAN.md` §10), run unconditionally, whatever
  the task declared.

A task's own declared paths are read from its text the same way a person reading
`tasks.md` already finds them: every backtick-quoted span in the task's own line that
looks like a path (contains a `/`, no whitespace) — exactly how every task in this
repository's own `tasks.md` files already names its target files, so no new authoring
convention is needed. A task with no such span declares none.

For a task with no declared paths, `check_declared` is skipped and the loop asks
`task.scope` instead — a single `decide()` call, made once the builder has written, with
the same before/after diff as its `changed_paths` state (D2: never batched with
`task.route`, since that diff does not exist before the builder runs). `check_protected`
always runs, for every task, regardless of whether `task.scope` was asked — matching
builder-role's own requirement that no declared or judged scope can widen the protected
list.

*Alternative considered:* one process-level sandbox (a restricted shell, a filesystem
overlay) instead of a post-hoc diff. Rejected for this change: it would duplicate C4's own
job (a *prevention* mechanism, per the guarantees table below) and neither binding — Codex
through its own plugin, a Claude subagent through its own tools — exposes a hook this
design could wrap without reaching into `C4`'s territory early. Detection here, prevention
in `C4`, same split C2's scope check already drew for `propose`.

### D4 · Evidence, fingerprinting, and the fix-or-escalate step

Before a task's check runs, `apply` takes a fingerprint — `sha256` of the diff against the
change's base commit, plus a sorted listing of untracked files and their own content
hashes — and takes it again once the check finishes. Evidence recorded is `{fingerprint,
command, exit_code, output_tail}`. Acceptance (the conjunction the `apply-command` spec
lists) compares the fingerprint at acceptance time against the one the check actually ran
against; a mismatch means the tree moved since the check ran, so the check is re-run
rather than trusted.

On a failing check, the loop hands the same builder the check's output and the current
diff for exactly one further attempt (`docs/PLAN.md` §10: "a retry is a fix, not a
re-check"); that attempt's check is a normal check, fingerprinted the same way. A second
failure, or any scope/protected-path violation on either attempt, escalates: the loop
stops the task, reports what it saw, and does not touch `tasks.md`.

### D5 · Run state and recovery: `.harnex/state/apply/<change>.json`

One record per change, one entry per task, transitions written atomically
(write-to-temp-then-rename) before the next step starts:
`queued → delegated → returned → checked → accepted` (or `escalated` off the `checked`
step). A task's entry carries its base fingerprint, its current binding, and — while
`delegated` to Codex — the job identifier `/codex:rescue` returned.

On start, `apply` reads this file. A task found `delegated` triggers the Codex job-status
lookup first (S1: `running` or `done`, no liveness signal); if the lookup itself fails or
the job has shown no progress past a fixed staleness interval, `apply` shows the diff
since the task's base fingerprint and asks: keep and check it, discard it (destructive, so
it asks — per the `safety` rule set's own `destructive-commands-ask`), or delegate again.
It never re-delegates onto a tree the task's own base fingerprint no longer matches,
without asking first. A task already `accepted` (ticked) is never revisited by a resumed
run.

*Alternative considered:* re-delegate automatically on any interruption, trusting the
`--cwd` worktree to be exactly as left. Rejected: `docs/PLAN.md` §10 already rules this out
explicitly ("It never re-delegates onto a dirty tree without asking") — S1's finding that a
normal session exit kills its own background Codex jobs outright means "resume" usually
means "the job is gone," not "the job is still running," so silently retrying would as
often redo already-good work as recover anything.

### D6 · `/harnex:apply`: the skill that drives the loop, same split as C2

`plugin/skills/apply/SKILL.md` holds the conversation and every screen line; the loop's
own steps (D4, D5) live in `plugin/scripts/apply_loop.py` — kept in `scripts/` beside
`decide.py` and `setup.py`, per `orchestration/README.md`'s own "every harness script
lives" rule, importing `decide.py` directly as a sibling module (the way `decide.py`
already imports `setup.py`, C2) rather than shelling out to it — that the skill calls and
reads structured output from, the same contract `decide.py` and `scope_check.py` already
establish.

Once, before any task starts: read every task from `tasks.md`, call `decide_many` with one
`task.route` question per task (D2's embedded-instructions shape), and print every task's
decision line before the first builder starts — so the person sees the whole run's routing
up front, not staggered between builders. Then, for each task in order: start the routed
builder, run D3's declared-path check (or, for a task with no declared paths, a single
`task.scope` call once the builder has written, D2), run the protected-path check, run the
check command, apply D4's fix-or-escalate, accept and tick or escalate and stop.

### D7 · Restating the two `sdd` rules and moving the two profiles

`no-scope-beyond-the-task.md`'s `**Enforced by:**` line changes from "the scope question
of pillar 3" to: the path check for a task with declared paths, `task.scope` (asked
through `decide_many`) for one without, and the protected-path check unconditionally in
both cases — naming `plugin/feedback/task_scope_check.py` by path, per pillar 1's own
"names the component doing the enforcing" requirement. `builders-never-tick-tasks.md`
gains `enforced_by: check` (renamed from `none`) and a body line naming
`apply_loop.py`'s ticking step as the enforcer, on the same "names it or the walk fails"
requirement `rule-sets` already checks for hook-based enforcement, applied here by hand
since a script that is not a hook has no automated two-way walk to satisfy — the rule text
itself is the only place this link is recorded. No requirement in `rule-sets`' own spec
changes: the format already allowed `enforced_by: check` (`the-proposal-is-the-scope`
already uses it), so this is content, not a spec delta.

The two profiles move from their old, pre-harnex kit locations into `plugin/tools/
profiles/`, named there per the layout rule ("technologies are named only in
`plugin/tools/profiles/`") — a file move, not a behavior change, so no capability names it.

## Risks / Trade-offs

- [A live Codex run remains untested by this change, same gap S1 left open] → Every check
  in D3–D5 runs identically against a fake `codex-companion` on `PATH` and against the
  Claude fallback binding directly; the loop's own contract does not depend on which
  binding answered, so the untested surface is narrowed to "does `/codex:rescue` behave as
  its source and S1's reading say it does," not "does the loop work."
- [`check_protected` and `check_declared` are a diff-based detection, not a sandboxed
  prevention — a fast or unusual write pattern could in principle land and be reverted
  before either check's `git status` snapshot catches it] → Accepted for `C3`: `C4`'s
  guard is the prevention layer (§4's own I·P split); this design's job is to catch what
  actually landed in the tree the check evidence is fingerprinted against, which is the
  only thing acceptance depends on.
- [`decide_many` and `noul` support add two code paths through `decide.py` that C2's
  tests do not cover, and the `noul` request/response shape is read from a tutorial page,
  not exercised live] → Built and tested the same way C2 tested `decide()`: a stubbed
  multi-question OpenRouter response fixture, a stubbed hang, a `mock`-backend path that
  answers each question with its own unresolved prompt rather than a merged one, and a
  `noul` fixture for each of resolved-true, resolved-false, and between-thresholds. A
  first live `task.scope` call, once a working key exists, is this change's own remaining
  step for that path, same as C2 left `phase.route`'s first live call as its own.
- [The run-state file (D5) is hand-rolled JSON with atomic-rename writes, not a database]
  → Matches C1c's own `.harnex/manifest.json` and C2's journal, both the same shape; one
  file, one change, no concurrent writer to serialize against since `apply` runs one task
  at a time in the main session.

## What setup and update write

Nothing new in a harnessed project's own committed files. The two new question files, the
builder role and its two bindings, the checks, the loop script and `/harnex:apply` itself
arrive with a plugin update, the same way `C1d`'s hook and `C2`'s skills did — no new
`.harnex.yml` key, no change to `.claude/settings.json`. `.harnex/state/apply/<change>.json`
is written by `apply` itself, per task, the same way `.harnex/state/journal.jsonl` is
written by `decide.py` (C2) rather than by `setup`; it is self-ignoring the same way
`.harnex/state/` already is (C1c).

## Guarantees and what happens when they fail

| Guarantee | Kind | When the component fails |
|---|---|---|
| A builder never ticks `tasks.md` | **prevention** for the Claude fallback binding (its tool grants writing but the tick step lives only in the loop's own script, which the binding never runs) · **detection** for the Codex binding (its own tools are not harnex's to restrict, so a write to `tasks.md` is caught by the protected-path check after the fact) | If the protected-path check itself crashes, the task is not accepted (D4's conjunction includes "the check command exited 0" and the protected-path result; a crash is neither a pass), so the loop stops rather than silently trusting an unchecked tree |
| A task's write stays inside its own scope | **detection**: `check_declared` or `task.scope`, always after the builder has already written | A crashed check leaves the task un-accepted, same failure mode as above — never silently accepted |
| A protected path is never touched, whatever the task declares | **detection**: `check_protected`, unconditional | Same as above — a crash blocks acceptance rather than defaulting to it |
| Evidence accepted matches the tree it was produced against | **prevention** by construction: acceptance compares the fingerprint, and a mismatch re-runs the check rather than trusting stale evidence | None — this is the fallback path itself |
| An interrupted run never redoes ticked work or re-delegates blind | **prevention**: the run-state file is the only source `apply` reads on resume, and a ticked task's entry is never revisited | If the state file itself is corrupt or missing, `apply` cannot tell what was in flight and asks the person before touching anything, rather than guessing |
| A job's `running` status is not trusted past a staleness interval | **detection**, bounded by S1's own finding that no liveness signal exists | A job that is actually still alive past the staleness interval is asked about rather than assumed dead — the person, not the loop, breaks the tie |
