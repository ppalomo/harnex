# shell-guard Specification

## Purpose
What happens before every shell command an agent runs: deterministic rules decide first,
a decision model only sees what those rules leave ambiguous, and nothing that fails on the
guard's own side of the line is ever silently allowed.

## Requirements

### Requirement: Every command is classified before it runs

Before a `Bash` command is executed, the guard SHALL classify it, in order: every part in
the read-only allowlist resolves to allow; failing that, a match against a deny pattern
resolves to deny; failing that, a match against an ask pattern resolves to ask; anything
left, including a command the guard cannot parse, is residue and is never allowed by this
step alone.

#### Scenario: A read-only command

- **WHEN** every part of the command is in the read-only allowlist
- **THEN** the command runs with no prompt and nothing is journalled

#### Scenario: A command matching a deny pattern

- **WHEN** the command matches a deny pattern
- **THEN** the command is refused, the person sees which pattern and which rule it comes
  from, and the refusal is journalled

#### Scenario: A command matching an ask pattern

- **WHEN** the command matches an ask pattern and no deny pattern
- **THEN** the person is asked before the command runs, and the question is journalled

#### Scenario: An unparseable command

- **WHEN** the command cannot be split into its parts (an unrecognised compound form, for
  instance)
- **THEN** it is treated as residue, never as allow

### Requirement: Deny never comes from the decision model alone

Only a deterministic deny pattern SHALL refuse a command. The decision model asked about
the residue SHALL resolve to allow or to ask, never to deny.

#### Scenario: The decision model judges the residue

- **WHEN** a command reaches the decision model because no deterministic pattern matched it
- **THEN** the only outcomes it can produce are allow or ask; a command that should be
  refused instead reaches the person as a question, never as a silent action

### Requirement: The guard never allows on its own error

Any failure inside the guard's own classification — an unreachable decision backend, a
timeout, a missing key, the `mock` backend, an exception raised while classifying — SHALL
resolve to ask, never to allow.

#### Scenario: The decision backend is unreachable or times out

- **WHEN** the guard asks the decision model about the residue and the backend does not
  answer within its budget
- **THEN** the outcome is ask, and the reason names the failure

#### Scenario: No backend is configured

- **WHEN** the project's decision backend is `mock` or no key is available
- **THEN** the outcome for any command reaching the decision model is ask

#### Scenario: The guard's own classification raises an exception

- **WHEN** an unexpected error occurs while the guard is classifying a command
- **THEN** the outcome is ask, not allow, and the error is recorded

### Requirement: A subagent's own role list applies to its commands

When a tool call carries the `agent_type` field Claude Code attaches to a subagent's
calls, the guard SHALL classify that command against the pattern lists for that role,
where the role has its own, instead of the main session's lists.

#### Scenario: A builder subagent runs a command its own list restricts

- **WHEN** a `Bash` call carries `agent_type: builder` and the command matches a pattern on
  the builder's own list that the main session's list does not carry
- **THEN** the builder's list decides the outcome

#### Scenario: A role with no list of its own

- **WHEN** a tool call's `agent_type` has no role-specific list
- **THEN** the main session's lists apply

### Requirement: Every deny and ask decision is journalled

The guard SHALL record every deny and every ask decision — the command, the outcome, and
which of a deterministic pattern, a decision-model call, or an exception in the guard's
own classification (the previous requirement's scenario) produced it. A silent allow from
the read-only allowlist SHALL NOT be journalled.

#### Scenario: A denied command is journalled

- **WHEN** the guard refuses a command
- **THEN** the journal gains an entry naming the command and the pattern that refused it

#### Scenario: An allowed read-only command is not journalled

- **WHEN** the guard allows a command because every part is on the read-only allowlist
- **THEN** no journal entry is written for it

### Requirement: A guard hook failure never blocks or bypasses the host's own permission flow

When the hook itself cannot complete — the interpreter is missing, the script does not
start, it runs past its declared timeout, or it prints output the host cannot parse — the
guard SHALL NOT claim to have made a decision, and the host's own permission flow SHALL
decide instead.

#### Scenario: The hook crashes before classifying a command

- **WHEN** the guard script exits with an error or does not start
- **THEN** no allow, deny or ask is attributed to the guard, and the host falls back to its
  own permission resolution for that command

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
