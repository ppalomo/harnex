## Why

`explore` and `propose` (C2) get an idea to a reviewable set of artifacts, but nothing yet
turns a task list into code. Right now the person has to implement every task themselves,
by hand, outside the harness — the one step the plan (§11, C3) calls out as the next
capability that "leaves something you can use." S1's spike answered the questions this
phase depends on: Codex has no way to target a branch or worktree of its own, its job
record cannot distinguish a stale pid from a live one, and its sandbox toggle is read from
source, not observed live — so the loop this change builds has to check out or worktree the
branch itself, pass `--cwd`, and treat every job record as unproven until its own evidence
says otherwise. S1 also found every model this account tried unreachable through Codex,
traced to the account's own entitlement rather than to the design — so this change delivers
a Claude fallback subagent as a first-class path, not a stopgap, and needs no live Codex run
to be usable end to end.

## What Changes

- **New:** the `builder` role — a tool-agnostic prompt (`orchestration/roles/builder.md`)
  and two bindings that implement it: Codex, reached through its plugin, and a Claude
  subagent as fallback. Both are bound by the same contract: never tick `tasks.md`, never
  write outside the task's own scope, never touch a protected path regardless of scope.
- **New:** `task.route` (Choice) and `task.scope` (Noul), two decision questions
  (`orchestration/decisions/task-route.yaml`, `task-scope.yaml`) picking which binding
  builds a given task and judging scope for a task that declares no paths of its own.
  `task.scope` is the first `noul`-typed question the harness asks — `decide.py`
  declared `noul` as a valid question type since C1b/C2 but never built a request or
  parsed an answer for one (only `choice` was implemented, `phase.route`'s own type).
  This change fills that in, and adds `decide_many()` so the loop can ask `task.route`
  for every queued task in one call at the start of a run, rather than once per task —
  both changes to `decide.py`'s own code, not just a new question file dropped beside it.
- **New:** the path check and the protected-path check (`feedback/`) — deterministic,
  comparing what a builder wrote against the task's own declared paths and against
  `docs/PLAN.md` §10's fixed protected list (`openspec/`, `.harnex/`, which makes
  `tasks.md` protected as a consequence). `task.scope` judges scope only for a task that
  declares no paths, where no deterministic check is possible.
- **New:** the apply loop (§10) — run state per task, evidence fingerprinted to the
  working tree it was produced against (`apply` never commits), one fix attempt per
  failure before escalating, and recovery that resumes an interrupted run rather than
  redoing or losing work.
- **New:** `/harnex:apply` (`skills/apply/`) — drives the loop for every task in a change,
  printing `task.route`'s decision line per task, showing the check and its evidence, and
  ticking `tasks.md` itself once a task's evidence is green (the loop ticks; the builder
  never does).
- **Changed (content, not behaviour):** the `sdd` rule `builders-never-tick-tasks` and the
  `code` rule `no-scope-beyond-the-task` are restated to name the path and protected-path
  checks as their detection, in place of the generic "decision" enforcement
  `no-scope-beyond-the-task` currently names. This is a rewording of existing rule files,
  not a change to how `rule-sets` renders or checks them.
- **Moved:** the two builder profiles that were living in the old, pre-harnex kits move to
  `plugin/tools/profiles/`, named only there per the layout rule.

## Capabilities

### New Capabilities
- `builder-role`: what the builder role may and may not do, regardless of which binding
  (Codex or the Claude fallback subagent) carries it out — the write boundary, the
  tick boundary, and the fact that both bindings are held to the same contract.
- `apply-command`: what `/harnex:apply` does for the person — the run loop, the decision
  line per task, the path/protected-path/task.scope checks it depends on, fingerprinted
  evidence, one fix per failure, escalation, and recovery after an interruption.

### Modified Capabilities
- `decision-model`: `decide.py` gains `decide_many()` (answer several questions, sharing
  one state, in a single call) and support for building a request and parsing an answer
  for a `noul`-typed question — both externally observable additions to the interface
  §8's table already named as this phase's to add, not covered by C2's delivery. The
  `sdd` rule edits are content only, not a change to how `rule-sets` renders or checks
  rule files, so `rule-sets` itself is not listed here.

## Impact

- `plugin/orchestration/roles/builder.md`, `plugin/agents/builder.md` (Claude fallback
  binding), `plugin/orchestration/decisions/task-route.yaml`,
  `plugin/orchestration/decisions/task-scope.yaml`.
- `plugin/scripts/decide.py` (`decide_many()`, `noul`-type support), plus its tests.
- `plugin/feedback/task_scope_check.py` (declared-path and protected-path checks in one
  module, per design.md D3), plus its fixtures.
- `plugin/scripts/apply_loop.py` (the loop's own filesystem and process steps, kept in
  `scripts/` beside `decide.py` and `setup.py` per `orchestration/README.md`'s own "every
  harness script lives" rule, following the C1c/C2 split: scripts never talk to the
  person).
- `plugin/skills/apply/SKILL.md`.
- `plugin/context/rules/sdd/builders-never-tick-tasks.md`,
  `plugin/context/rules/code/no-scope-beyond-the-task.md` (body edits only).
- `plugin/tools/profiles/` (the two moved profiles).
- `docs/smoke.md` gets `apply`'s manual steps appended, per the format C1a fixed.
- No change to `plugin/control/` — the shell guard (`guard.py`, the PreToolUse hook) is
  C4's delivery; this change's checks run after a builder has already written, not before.

## Non-goals

- The shell guard and its hook (`guard.py`, `patterns.yaml`, `guard.risk`) — C4.
- `/harnex:verify` and `/harnex:ship` — C5.
- Making a live Codex run succeed against this account's entitlement gap — outside the
  harness's own code, per S1's finding; this change keeps the Claude fallback fully usable
  without one.
- Scoping one shared `state` object per task inside a batched call — a shape neither
  OpenRouter's docs nor a live call confirm. `decide_many()` batches `task.route` across
  every queued task instead by giving each task its own question, with that task's text
  and paths embedded directly into its own `instructions` (see design.md D2), which needs
  no such scoping to work. `task.route` and `task.scope` are never batched together for
  the same task, since `task.scope`'s own state does not exist until after that task's
  builder has already written (design.md D2).
- Any change to how `rule-sets` renders or checks rule files, or to `guard.risk`'s own
  `score` type — both are reused or deferred exactly as C1b/C2/C4 already fix them.

## Phase

C3 · apply through Codex (`docs/PLAN.md` §11). Exit criterion: both tasks of a two-task
change land on the change's own branch with a green check and evidence, ticked by `apply`,
without the person writing code; an interrupted run resumes without redoing or losing work.
