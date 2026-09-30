# verifier Specification

## Purpose

The read-only role that reviews a change's artifacts for coherence before the person acts
on them — a boundary held by what the role can do, not only by what its prompt says to do.

## Requirements

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
another context. When called by `/harnex:verify`, it SHALL also read the change's diff
against the working tree's base and the facts file the check-command and Playwright steps
wrote to disk — never running either itself, and never trusting a description of either
carried over from another context.

#### Scenario: The verifier is started fresh

- **WHEN** the verifier begins a review of a change
- **THEN** it reads the change's proposal, specs, design, and task list from disk before
  reporting anything

#### Scenario: The verifier is called by `/harnex:verify`

- **WHEN** `/harnex:verify` starts the verifier after the check-command and, where
  applicable, Playwright steps have written their facts to disk
- **THEN** the verifier reads the diff and the facts file from disk before reporting
  anything, and does not run either step itself

### Requirement: The review reports coherence, and nothing beyond it

The verifier's review SHALL report contradictions between the change's own artifacts,
contradictions with `docs/PLAN.md`'s settled decisions, and gaps against the phase's own
exit criterion. When called by `/harnex:verify`, it SHALL also report where the diff does
not satisfy the specs it claims to implement, and SHALL report the check-command and
Playwright facts it was handed rather than re-deriving or guessing at them. It SHALL NOT
reopen a decision `docs/PLAN.md` records as settled, and SHALL NOT propose a fix — only
name what it found. Every finding SHALL carry a severity of either `blocking` — the
disagreement rule refuses `ship` while one stands — or `advisory` — shown to the person but
never refusing anything on its own.

#### Scenario: An artifact contradicts a settled decision

- **WHEN** a change's design contradicts a decision `docs/PLAN.md` §12 already records
- **THEN** the review names the contradiction and does not suggest which side should give

#### Scenario: Nothing is wrong

- **WHEN** the verifier finds no contradiction and no gap
- **THEN** the review says so plainly, rather than inventing a finding to justify its run

#### Scenario: The diff does not satisfy a spec it claims to implement

- **WHEN** `/harnex:verify` calls the verifier and the diff does not do what a delta spec
  under the change's `specs/` requires
- **THEN** the review names the gap, which spec it is against, and the severity it carries

#### Scenario: The check command failed

- **WHEN** the facts file the verifier reads records a non-zero exit from the project's
  `check_command`
- **THEN** the review reports the failure as a finding, using the facts file's own output
  rather than re-running the command itself

### Requirement: The review never blocks the person from proceeding

Whatever the verifier finds, the calling command SHALL present the review and then finish
normally. Finding something SHALL NOT stop the command, roll back a write, or require a
second run before the person can continue. The one exception is `/harnex:ship`: it SHALL
refuse to proceed when the verifier's most recent review, fingerprinted to the current
working tree, contains a finding marked blocking — the disagreement rule. Every other
caller, and `ship` itself when facing only non-blocking findings, follows the rule as
stated.

#### Scenario: The review reports a contradiction

- **WHEN** the verifier reports a contradiction in its review, and the calling command is
  not `/harnex:ship`
- **THEN** the calling command still finishes, and the person decides what to do about it

#### Scenario: `ship` faces a blocking finding

- **WHEN** `/harnex:ship` runs and the verifier's latest review, fingerprinted to the
  current working tree, contains a finding marked blocking
- **THEN** `ship` refuses to commit, open a pull request, archive the change, or sync
  specs, and reports the blocking finding to the person instead

#### Scenario: `ship` faces only non-blocking findings

- **WHEN** `/harnex:ship` runs and the verifier's latest review contains no finding marked
  blocking
- **THEN** `ship` proceeds to ask the person for their explicit yes before committing
