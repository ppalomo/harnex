## Purpose

What `/harnex:explore` and `/harnex:propose` do for the person, in what order, and what
they never expose or require beyond the harness itself — the two architect phases that let
a change reach a reviewable proposal without the person ever running OpenSpec by hand.

## ADDED Requirements

### Requirement: Neither command requires the person to know OpenSpec

Neither command SHALL require the person to type an `openspec` command, name an artifact
id, or choose a schema. Any output naming those things SHALL be for a person who already
knows to look, never a required step of using the command.

#### Scenario: A person who has never heard of OpenSpec

- **WHEN** a person who does not know what OpenSpec is runs `/harnex:propose`
- **THEN** they are asked about their idea in plain language and shown the resulting
  artifacts, without needing to know OpenSpec exists underneath

### Requirement: `explore` writes nothing

`/harnex:explore` SHALL NOT create a change directory, write any file under `openspec/`,
or call the verifier. It SHALL print the phase-routing advice line and then hold a
conversation that helps the person clarify what they want before proposing it.

#### Scenario: Exploring an idea

- **WHEN** the person runs `/harnex:explore` with an idea
- **THEN** no file is created, and the session ends with the person deciding whether to
  run `/harnex:propose` next

### Requirement: `propose` creates exactly the artifacts a change needs

`/harnex:propose` SHALL create a new change directory and write the proposal, the delta
specs for every capability the proposal names, the design where the schema requires it,
and the task list — the complete set a later `apply` phase depends on — and SHALL NOT
leave the change in a state where a required artifact is missing.

#### Scenario: A proposal is completed

- **WHEN** `/harnex:propose` finishes without being interrupted
- **THEN** every artifact its own proposal's capabilities require exists on disk

### Requirement: `propose` reports anything it wrote outside the change's directory

After every required artifact exists, `/harnex:propose` SHALL check whether any path was
written or modified outside the new change's own directory since the command started, and
SHALL report any such path to the person before finishing. It SHALL NOT fail or undo the
write; it SHALL only report it.

#### Scenario: Everything stayed inside the change's directory

- **WHEN** `propose` finishes having written only inside the change's own directory
- **THEN** nothing is reported

#### Scenario: A file outside the change's directory was touched

- **WHEN** a path outside the new change's directory was created or modified after
  `propose` started, and was not already dirty before it started
- **THEN** `propose` names that path to the person as written outside the change's scope

#### Scenario: The working tree already had unrelated changes

- **WHEN** a path outside the change's directory was already modified before `propose`
  started
- **THEN** that path is not reported, since it predates this proposal

### Requirement: `propose` calls the verifier once, and shows its review

Once every required artifact exists, `propose` SHALL start the verifier once against the
change's own directory and present its review to the person before finishing. It SHALL NOT
call the verifier more than once per run, and SHALL NOT revise an artifact on the
verifier's behalf.

#### Scenario: The verifier finds a contradiction

- **WHEN** the verifier's review names a contradiction
- **THEN** `propose` shows the review as written and finishes; the person decides whether
  to revise the proposal

### Requirement: The phase-routing line is printed once per command, as advice

Both `explore` and `propose` SHALL print the phase-routing decision as advice, exactly
once per run, before any artifact is written or any conversation about the idea begins.

#### Scenario: The advice line appears first

- **WHEN** either command starts
- **THEN** the advice line is the first thing printed, before anything else the command
  does
