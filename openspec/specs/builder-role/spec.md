# builder-role Specification

## Purpose

The role that turns one task into a diff — bound to the same write and tick boundary
whether it runs through Codex or the Claude fallback subagent, so the loop that drives it
never has to know which one answered.

## Requirements

### Requirement: Both bindings implement the same contract

The builder role SHALL be defined once, tool-agnostic, and SHALL have exactly two
bindings that implement it — Codex, reached through its plugin, and a Claude subagent as
fallback. Both bindings SHALL be held to the same write boundary and the same tick
boundary; neither SHALL be granted a capability the other is refused.

#### Scenario: Codex is unreachable

- **WHEN** the Codex binding cannot be reached or fails to negotiate a model
- **THEN** the Claude fallback subagent can carry out the same task under the same
  boundary, without the loop or the person changing anything about what the task may touch

### Requirement: The builder never ticks its own task

The builder SHALL have no way, in either binding, to mark a task done in `tasks.md`.
Ticking SHALL remain the apply loop's own act, taken after a check has passed and the
loop has read the evidence — never the builder's.

#### Scenario: A builder finishes a task

- **WHEN** a builder binding completes the diff for a task
- **THEN** `tasks.md` is unchanged by that binding; only the loop that called it can tick
  the task, and only after its own check passes

### Requirement: A builder cannot write outside its task's own scope

Given a task that declares its own paths, a builder's write SHALL be limited to those
paths; a write outside them SHALL be refused before it reaches the loop's evidence. Given
a task that declares no paths, the write is scoped by `task.scope`'s judgement rather than
by a fixed list, but is refused on the same terms once that judgement finds it out of
scope.

#### Scenario: A task with declared paths

- **WHEN** a builder writes to a path the task did not declare
- **THEN** the write is refused and reported, and the task's own evidence is not produced
  from it

#### Scenario: A task without declared paths

- **WHEN** a task declares no paths and a builder's write is judged out of scope by
  `task.scope`
- **THEN** the write is refused on the same terms as a declared-path violation

### Requirement: A protected path refuses a builder regardless of scope

A fixed list of protected paths — `openspec/` and `.harnex/`, per `docs/PLAN.md` §10 —
SHALL refuse a builder's write even when the task's own declared scope would otherwise
allow it. No task's scope SHALL be able to widen this list. `tasks.md` is protected as a
consequence, since it lives under `openspec/changes/<name>/`.

#### Scenario: A task that names a protected path in its own scope

- **WHEN** a task's declared paths include a protected path
- **THEN** the builder is still refused from writing it, and the refusal names the
  protected-path check, not the task's own scope, as the reason
