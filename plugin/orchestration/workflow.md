# The workflow

Five phases, in order: `explore`, `propose`, `apply`, `verify`, `ship`. Each is a command
in `docs/PLAN.md`'s sense — hiding OpenSpec, the decision model, and the roles that play
each phase — and each has its own entry criterion, its own limit on what it may write, and
its own exit criterion. Moving from one phase to the next is always the person's choice,
never automatic: nothing here describes an unattended mode, and `docs/PLAN.md` names one
explicitly as a non-goal.

Before any phase starts, it asks `phase.route` (`decisions/phase-route.yaml`) and prints
the fixed screen line. `explore` and `propose` run in the main session, whose model harnex
cannot switch, so their line says "advice" (§3); `apply` and `verify` bind the answer once
they exist, since they delegate to a fresh player who can actually be routed.

## `explore` — built, `C2`

- **Enters:** the person has something they want to think through before committing it to
  a proposal. Nothing about the project needs to be in any particular state.
- **May write:** nothing. It never creates a file under `openspec/` and never starts the
  verifier — there is nothing yet for either to act on.
- **Leaves:** when the person decides either to run `propose` next, or to stop. There is no
  artifact that marks this phase "done"; the conversation itself is the output.

## `propose` — built, `C2`

- **Enters:** the person is ready to turn an idea into a change, whether or not they ran
  `explore` first.
- **May write:** exactly the new change's own directory under `openspec/changes/<name>/` —
  the proposal, the delta specs for every capability it names, the design where the schema
  requires one, and the task list. Anything else written during this phase is reported by
  the scope check, never silently accepted (`the-proposal-is-the-scope`).
- **Leaves:** once every required artifact exists, the scope check has run, and the
  verifier has reviewed the change and shown its findings. Whether to revise the proposal
  or move on to `apply` is the person's decision; `propose` does not gate on the review.

## `apply` — not yet implemented, arrives in `C3`

- **Enters:** a change whose planning artifacts are complete — in particular, `tasks.md`
  exists and lists every task in order (`docs/PLAN.md` §10: "linear in v0.1").
- **May write:** source and tests, within the paths a task declares (or, for a task that
  declares none, within what `task.scope` judges in scope). Never `tasks.md` itself except
  to tick a task once accepted, never `openspec/` or `.harnex/`, never a commit.
- **Leaves:** every task ticked, each on the facts §10 lists (check exit code, path
  containment, protected paths unchanged, refs unmoved, evidence bound to a tree
  fingerprint) — or escalated to the person when a retry cannot fix it.

## `verify` — not yet implemented, arrives in `C5`

- **Enters:** a change whose tasks are all ticked by `apply` (or, mid-way, whichever tasks
  exist so far).
- **May write:** nothing — the same read-only boundary as `propose`'s verifier, extended
  with running the project's own check command and, where a UI profile is in play,
  checking it in a running app.
- **Leaves:** a report with findings, each carrying a severity; any blocking finding blocks
  `ship`, per `docs/PLAN.md`'s disagreement rule.

## `ship` — not yet implemented, arrives in `C5`

- **Enters:** `verify` found nothing blocking, or the person overrides a non-blocking
  finding explicitly.
- **May write:** a commit — the only phase that may ever run `git commit`, and only after
  the person's explicit yes — a pull request, and the change's own archive and spec sync.
- **Leaves:** the change merged or its PR opened, and `openspec/specs/` carrying its deltas.
