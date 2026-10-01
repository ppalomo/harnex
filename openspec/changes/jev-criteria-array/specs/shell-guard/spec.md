## ADDED Requirements

### Requirement: The default list acts only where the project chose the `safety` set

The guard's read-only allowlist, deny patterns, ask patterns, and decision-model residue
call — the default list — SHALL be inert in a project without a `.harnex.yml` at its root,
and in a project whose `.harnex.yml` does not list `safety` among its sets. Inert means
every command resolves to allow without consulting the default list or calling the
decision model, and nothing is journalled.

This gate applies to the default list only. A role's own additions (`agent_type`-scoped
patterns, §"A subagent's own role list applies to its commands") SHALL continue to apply
regardless of whether `safety` is chosen, since they protect the harness's own state
during `apply` and are not a set a project opts into or out of.

A `.harnex.yml` that exists but cannot be read or parsed is not the same as a project that
did not choose the set: per "The guard never allows on its own error", that failure SHALL
leave the default list active, not inert — an error is never grounds to allow.

#### Scenario: A project that never ran setup

- **WHEN** a command reaches the guard in a project with no `.harnex.yml` at its root
- **THEN** the command runs with no prompt, no decision-model call, and nothing journalled

#### Scenario: A project that did not choose the set

- **WHEN** a command reaches the guard in a project whose `.harnex.yml` does not list
  `safety` among its sets
- **THEN** the command runs with no prompt, no decision-model call, and nothing journalled

#### Scenario: A project that chose the set

- **WHEN** a command reaches the guard in a project whose `.harnex.yml` lists `safety`
  among its sets
- **THEN** the default list classifies the command exactly as "Every command is classified
  before it runs" describes

#### Scenario: `.harnex.yml` cannot be read

- **WHEN** a project's `.harnex.yml` exists but cannot be read or parsed
- **THEN** the default list stays active, classifying the command exactly as if `safety`
  were chosen

#### Scenario: A role addition still applies when the default list is inert

- **WHEN** a command reaches the guard in a project that did not choose `safety`, and the
  command's `agent_type` has a role-specific deny or ask pattern matching it
- **THEN** that role's outcome applies, even though the default list itself would have
  allowed every command unconditionally
