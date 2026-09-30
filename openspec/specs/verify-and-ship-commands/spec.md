# verify-and-ship-commands Specification

## Purpose
What `/harnex:verify` and `/harnex:ship` do for the person, in order — running a change's
checks deterministically and presenting the verifier's severity-carrying review, then
letting `ship` commit, open a pull request, archive the change, and sync specs only when
nothing blocking stands in the way.

## Requirements

### Requirement: `verify` runs the check command deterministically, never through the verifier's own judgement

`/harnex:verify` SHALL run the project's `check_command` itself, outside the verifier
subagent, and SHALL write its exit status and output to a facts file the verifier then
reads. The verifier SHALL NOT be asked to run the check or to judge whether it passed from
a description.

#### Scenario: A project with a check command

- **WHEN** `/harnex:verify` runs on a project whose `.harnex.yml` names a `check_command`
- **THEN** the command is executed by `/harnex:verify` itself, and its exit status and
  output are written to disk before the verifier is started

### Requirement: `verify` refuses to start the verifier when its own check-running step fails internally

If the step that runs `check_command` (and, where applicable, Playwright) fails before it
can write the facts file — the script crashes, the interpreter is missing, `check_command`
is not set in `.harnex.yml` — `/harnex:verify` SHALL NOT start the verifier at all, and
SHALL report the failure directly to the person. This is distinct from `check_command`
running and exiting non-zero, which is a normal facts-file outcome the verifier reports as
a finding, not a reason to skip the review.

#### Scenario: The check-running step crashes

- **WHEN** the script that runs `check_command` fails before writing the facts file
- **THEN** `/harnex:verify` reports the failure and does not start the verifier

#### Scenario: `check_command` runs and fails normally

- **WHEN** `check_command` runs to completion and exits non-zero
- **THEN** the facts file is written recording that exit status, and the verifier is
  started and reports it as a finding

### Requirement: `verify` runs a Playwright step only when the project declares a UI profile

When the project's `.harnex.yml` names a UI profile, `/harnex:verify` SHALL run a Playwright
MCP step and write its result to the same facts file. In this version, that step is a
stubbed placeholder recording that Playwright MCP is not yet configured — an actual
Playwright check of the running app is not yet built (proposal's Non-Goals) — but the facts
file SHALL always carry an unambiguous record of whether the step ran or was skipped, so the
shape is real and testable even before the check itself is. When no UI profile is declared,
`/harnex:verify` SHALL skip this step entirely rather than attempt it against a project with
nothing to run.

#### Scenario: A UI profile is declared

- **WHEN** `/harnex:verify` runs on a project whose profile is a UI stack
- **THEN** the Playwright step runs (today, its stubbed placeholder) and the result is
  written to the facts file before the verifier is started

#### Scenario: No UI profile is declared

- **WHEN** `/harnex:verify` runs on a project with no UI profile
- **THEN** no Playwright step is attempted, and the facts file records no such step ran

### Requirement: `verify` presents the verifier's review with severity, every time

`/harnex:verify` SHALL start the verifier once per run, with the diff and the facts file
already on disk, and SHALL present its review exactly as returned, including every
finding's severity. It SHALL NOT summarise away a finding or revise the diff on the
verifier's behalf.

#### Scenario: A run with findings

- **WHEN** `/harnex:verify` completes a run and the verifier's review names findings
- **THEN** every finding is shown to the person with its severity, unedited

### Requirement: `ship`'s disagreement rule refuses on a blocking finding

`/harnex:ship` SHALL check for a `/harnex:verify` run whose review is fingerprinted to the
current working tree. If the most recent such run found a finding marked blocking, `ship`
SHALL refuse to commit, open a pull request, archive the change, or sync specs, and SHALL
report the blocking finding instead. If no `/harnex:verify` run is fingerprinted to the
current tree — because none was run, or the tree moved since the last one — `ship` SHALL
treat this the same as a blocking finding and refuse until a fresh `/harnex:verify` run
exists.

#### Scenario: No `verify` run exists yet

- **WHEN** `/harnex:ship` runs on a change that has never had `/harnex:verify` run against
  it
- **THEN** `ship` refuses and tells the person to run `/harnex:verify` first

#### Scenario: The tree moved since the last `verify` run

- **WHEN** `/harnex:ship` runs and the working tree's current fingerprint does not match
  the fingerprint of the last `/harnex:verify` run's review
- **THEN** `ship` refuses and tells the person the review is stale, rather than trusting
  a review that was not produced against the tree being shipped

#### Scenario: A fresh, clean `verify` run

- **WHEN** `/harnex:ship` runs and the most recent `/harnex:verify` run is fingerprinted to
  the current tree and found no blocking finding
- **THEN** `ship` proceeds toward asking the person for their explicit yes

### Requirement: `ship` commits only after the person's explicit yes

`/harnex:ship` SHALL be the first phase allowed to run `git commit`, and SHALL only do so
after asking the person and receiving an explicit yes. A non-blocking finding from the
latest `verify` run SHALL be shown to the person before that yes is asked, so the decision
to proceed is informed, but SHALL NOT be asked twice or silently dropped.

#### Scenario: The person declines

- **WHEN** `/harnex:ship` asks for the person's yes and they decline
- **THEN** no commit is made, and no pull request, archive, or spec sync follows

#### Scenario: The person agrees

- **WHEN** `/harnex:ship` asks for the person's yes and they agree
- **THEN** it commits, opens a pull request, archives the change, and syncs its deltas into
  `openspec/specs/`, in that order
