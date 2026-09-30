# review-command Specification

## Purpose
What `/harnex:review` does for the person: a code-quality review of a change's diff, run
by the reviewer role, independent of `verify` and `ship` and never required by either.

## Requirements

### Requirement: `/harnex:review` can run at any point after a change has a diff

`/harnex:review` SHALL be runnable against any change that has produced a diff, whether or
not `/harnex:verify` or `/harnex:ship` has ever run, and SHALL NOT require either to have
run first.

#### Scenario: Run before `verify`

- **WHEN** the person runs `/harnex:review` on a change that has not yet had
  `/harnex:verify` run against it
- **THEN** `/harnex:review` runs anyway, against whatever diff exists

### Requirement: `/harnex:review` never blocks `/harnex:ship`

Nothing `/harnex:review` finds, and whether or not it has been run at all, SHALL affect
`/harnex:ship`'s disagreement rule or any other check `ship` performs. It is a
recommended, independent step the person chooses to run.

#### Scenario: `ship` runs without a prior `review`

- **WHEN** the person runs `/harnex:ship` on a change that never had `/harnex:review` run
  against it
- **THEN** `ship` proceeds exactly as it would if `/harnex:review` had run and found nothing

#### Scenario: `review` found a bug and `ship` runs anyway

- **WHEN** the person runs `/harnex:ship` after `/harnex:review` reported a bug
- **THEN** `ship` is unaffected by that finding; only `verify`'s blocking findings can
  refuse `ship`

### Requirement: `/harnex:review` presents the reviewer's findings exactly as returned

`/harnex:review` SHALL start the reviewer once per run and present its findings exactly as
returned, without summarising away a finding or revising the diff on the reviewer's
behalf.

#### Scenario: A run with findings

- **WHEN** `/harnex:review` completes a run and the reviewer's review names findings
- **THEN** every finding is shown to the person, unedited
