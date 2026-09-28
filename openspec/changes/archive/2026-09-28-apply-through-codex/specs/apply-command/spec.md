## Purpose

What `/harnex:apply` does for the person: drives one builder per task through a checked
loop, ticks the task list itself once a task's evidence is green, and recovers an
interrupted run instead of redoing or losing work.

## ADDED Requirements

### Requirement: One task, one routed builder, one printed decision

For every task the loop runs, it SHALL ask `task.route` before starting the builder and
SHALL print the decision line — naming the phase, the chosen binding, and the confidence,
or that a person is being asked — before that task's builder starts.

#### Scenario: A well-scoped task

- **WHEN** `apply` starts a task whose evidence already names its tests
- **THEN** the printed line shows a resolved routing decision before the builder for that
  task starts

### Requirement: Evidence is fingerprinted to the working tree it was produced against

The loop SHALL record, alongside a task's check evidence, a fingerprint of the working
tree the evidence was produced against — the diff against the change's base commit plus
the untracked files, not the commit itself, since `apply` never commits (a task's tree
stays uncommitted until `ship`). Evidence whose fingerprint does not match the working
tree's current fingerprint SHALL be treated as stale and SHALL NOT be accepted as proof
the task passed.

#### Scenario: The tree moved after the check ran

- **WHEN** a task's stored evidence carries a fingerprint that does not match the working
  tree's fingerprint at acceptance time
- **THEN** the loop refuses to accept it and re-runs the check rather than trusting it

#### Scenario: The tree is unchanged since the check ran

- **WHEN** a task's stored evidence carries a fingerprint that matches the working tree's
  fingerprint at acceptance time
- **THEN** the loop accepts it as proof the check ran against the tree being accepted

### Requirement: One fix attempt per failure, then escalation

When a task's check fails, the loop SHALL give its builder exactly one further attempt to
fix it, using the check's own output. If that attempt's check still fails, the loop SHALL
escalate to the person rather than retrying again on its own.

#### Scenario: A broken test the builder can fix

- **WHEN** a task's check fails and the builder's one fix attempt makes it pass
- **THEN** the loop accepts the passing evidence and proceeds to tick the task

#### Scenario: A broken test the fix cannot address

- **WHEN** the builder's one fix attempt still leaves the check failing
- **THEN** the loop stops that task and reports the failure to the person instead of
  attempting a further fix on its own

### Requirement: Acceptance is a conjunction of facts, never a judgement call

The loop SHALL accept a task only when every one of these holds, each checked as a fact
rather than inferred: the builder reported the task done; the check command exited 0; the
changed paths sit inside the task's own declared paths, or `task.scope` judged them in
scope for a task that declares none; the protected paths are unchanged; and `HEAD` and the
branch's refs did not move during the run. A task missing any one of these SHALL NOT be
accepted, and SHALL instead go to a fix (per the one-fix-attempt requirement) or to the
person.

#### Scenario: A builder reports done but a protected path moved

- **WHEN** a builder reports a task done and its check passes, but a protected path was
  touched during the run
- **THEN** the task is not accepted, regardless of the builder's report or the check's
  exit code

### Requirement: The loop ticks a task; the builder never does

Once a task's check passes on evidence fingerprinted to the working tree the loop is
about to accept, the loop itself SHALL mark that task done in `tasks.md`. This SHALL be
the only path by which a task in a change driven by `apply` is marked done.

#### Scenario: A task's check passes

- **WHEN** a task's evidence is accepted
- **THEN** `tasks.md` is updated to mark that task done by the loop's own act, not by
  anything the builder wrote

### Requirement: An interrupted run recovers without redoing or losing work

If `apply` is interrupted while a builder is working and is run again on the same change,
the loop SHALL recover the in-flight task's run state rather than starting it over, and
SHALL NOT lose the work or evidence of any task already ticked. Where the interrupted
job's own state cannot tell a stale process from a live one, the loop SHALL ask the person
rather than guess.

#### Scenario: Interrupted mid-task, resumed

- **WHEN** `apply` is interrupted while a task's builder is working and run again
- **THEN** already-ticked tasks are untouched and the interrupted task's run resumes from
  its recorded state rather than starting over

#### Scenario: A job record that cannot be trusted

- **WHEN** the resumed run cannot tell whether the interrupted job is still live
- **THEN** the loop asks the person rather than assuming either state
