# reviewer-role Specification

## Purpose
The read-only role that reviews a change's diff for code quality — bugs, simplification,
efficiency — held to the same no-write boundary as the verifier, but distinct from it in
what it checks and in a guarantee the verifier does not need: it always runs on a fixed
model different from the builder fallback's own fixed model.

## Requirements

### Requirement: The reviewer cannot write anything

The reviewer SHALL run as a subagent whose declared tools include no capability to edit a
file, write a file, or run a shell command. This SHALL hold regardless of what its prompt
says, so that a prompt injected through the diff it reviews cannot make it write.

#### Scenario: The reviewer's own definition is inspected

- **WHEN** the reviewer's tool list is read from its definition
- **THEN** it names no file-editing, file-writing, or command-execution capability

### Requirement: The reviewer always runs on a fixed model, independent of who built the code

The reviewer's caller SHALL start it bound to one fixed model, the same on every run,
regardless of which builder or model built the code under review — Codex, the Claude
fallback subagent, or a person. This fixed model SHALL be different from the model the
Claude fallback builder runs on — a fixed value itself, since `task.route`'s own type
(`Choice: codex / claude / human`) has no per-Claude-model granularity — so a change built
by the Claude fallback is always reviewed by a different model, even though this rule does
not exclude Codex-built code from a same-tool review the way an earlier, journal-driven
design tried to (see `proposal.md`'s "What Changes" for why that was simplified).

#### Scenario: Codex built the code under review

- **WHEN** the code under review was built through the Codex binding
- **THEN** the reviewer runs on the fixed model, as it does on every run

#### Scenario: The Claude fallback subagent built the code under review

- **WHEN** the code under review was built by the Claude fallback subagent
- **THEN** the reviewer runs on the fixed model, which is different from the fixed model
  the Claude fallback builder runs on

#### Scenario: No builder is recorded for the code under review

- **WHEN** there is no record of who built the code under review — written by a person, or
  by `apply` before this change existed
- **THEN** the reviewer still runs on the same fixed model; nothing about starting it
  depends on that record

### Requirement: The reviewer reads the diff on disk, not the conversation

The reviewer SHALL read the change's diff from disk at the start of its review, and SHALL
NOT rely on a description of it carried over from another context.

#### Scenario: The reviewer is started fresh

- **WHEN** the reviewer begins a review
- **THEN** it reads the diff from disk before reporting anything

### Requirement: The review reports code quality, not spec coherence

The reviewer's review SHALL report bugs, simplification opportunities, and efficiency
concerns in the diff. It SHALL NOT report on whether the diff matches the change's own
specs or `docs/PLAN.md`'s settled decisions — that is the verifier's job, not the
reviewer's — and SHALL NOT propose a fix, only name what it found.

#### Scenario: The diff has a correctness bug

- **WHEN** the reviewer finds a concrete failure scenario in the diff
- **THEN** the review names the file, the bug, and the failure scenario, without editing
  anything

#### Scenario: Nothing is wrong

- **WHEN** the reviewer finds no bug, no simplification, and no efficiency concern
- **THEN** the review says so plainly, rather than inventing a finding to justify its run

### Requirement: The review never blocks anything

Whatever the reviewer finds, the calling command SHALL present the review and then finish
normally. Finding something SHALL NOT stop the command, roll back a write, or require a
second run before the person can continue — unlike the verifier's review, this holds for
every caller without exception, since `/harnex:review` never gates `ship`.

#### Scenario: The review reports a bug

- **WHEN** the reviewer reports a bug in its review
- **THEN** the calling command still finishes, and the person decides what to do about it
