## Purpose

The read-only role that reviews a change's artifacts for coherence before the person acts
on them — a boundary held by what the role can do, not only by what its prompt says to do.

## ADDED Requirements

### Requirement: The verifier cannot write anything

The verifier SHALL run as a subagent whose declared tools include no capability to edit a
file, write a file, or run a shell command. This SHALL hold regardless of what its prompt
says, so that a prompt injected through a reviewed artifact cannot make it write.

#### Scenario: The verifier's own definition is inspected

- **WHEN** the verifier's tool list is read from its definition
- **THEN** it names no file-editing, file-writing, or command-execution capability

#### Scenario: A reviewed artifact asks the verifier to change something

- **WHEN** an artifact the verifier reads contains an instruction to edit a file or run a
  command
- **THEN** the verifier has no tool capable of doing either, regardless of what it decides

### Requirement: The verifier reads the artifacts on disk, not the conversation

The verifier SHALL read every artifact in the change's directory from disk at the start of
its review, and SHALL NOT rely on a description of those artifacts carried over from
another context.

#### Scenario: The verifier is started fresh

- **WHEN** the verifier begins a review of a change
- **THEN** it reads the change's proposal, specs, design, and task list from disk before
  reporting anything

### Requirement: The review reports coherence, and nothing beyond it

The verifier's review SHALL report contradictions between the change's own artifacts,
contradictions with `docs/PLAN.md`'s settled decisions, and gaps against the phase's own
exit criterion. It SHALL NOT reopen a decision `docs/PLAN.md` records as settled, and SHALL
NOT propose a fix — only name what it found.

#### Scenario: An artifact contradicts a settled decision

- **WHEN** a change's design contradicts a decision `docs/PLAN.md` §12 already records
- **THEN** the review names the contradiction and does not suggest which side should give

#### Scenario: Nothing is wrong

- **WHEN** the verifier finds no contradiction and no gap
- **THEN** the review says so plainly, rather than inventing a finding to justify its run

### Requirement: The review never blocks the person from proceeding

Whatever the verifier finds, the calling command SHALL present the review and then finish
normally. Finding something SHALL NOT stop the command, roll back a write, or require a
second run before the person can continue.

#### Scenario: The review reports a contradiction

- **WHEN** the verifier reports a contradiction in its review
- **THEN** the calling command still finishes, and the person decides what to do about it
