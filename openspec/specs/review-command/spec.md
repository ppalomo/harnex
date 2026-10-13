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

### Requirement: `/harnex:review` starts every reviewer of the project's teams

After the core reviewer, `/harnex:review` SHALL start, once each, every agent of the
project's team whose role's phase is `review` — the agents the roster's `team` list
renders, or, for a project that records no roster, every agent its chosen profiles
render — with the same diff, and SHALL present each review exactly as returned,
labelled with the agent's emoji and name. It SHALL NOT start an agent on the project's
`bench`, SHALL NOT merge reviews, drop a finding because another agent reported it, or
start any agent more than once per run. A project with neither a roster nor a profile
with fragments SHALL see exactly the core reviewer's review, as before. None of these
reviews SHALL affect `/harnex:ship`.

#### Scenario: A project with two review-phase agents

- **WHEN** `/harnex:review` runs in a project whose `team` names `security-reviewer`
  and `migration-reviewer`
- **THEN** the core reviewer's review is shown first, then each of the two agents' reviews
  under its own emoji and `name`, each as returned

#### Scenario: A reviewer on the bench

- **WHEN** `/harnex:review` runs in a project whose `bench` names `migration-reviewer`
  and whose `team` does not
- **THEN** the migration reviewer is not started, is not listed, and the person may
  still start it by name

#### Scenario: A roster and no profile

- **WHEN** `/harnex:review` runs in a project that chose no profile and whose `team`
  names `security-reviewer`
- **THEN** the generic security reviewer is started after the core reviewer, and its
  review is shown under its emoji and `name`

#### Scenario: A project without a roster

- **WHEN** `/harnex:review` runs in a project whose choices carry neither `team` nor
  `bench`
- **THEN** every `review`-phase agent its chosen profiles render is started, exactly as
  before the roster existed

#### Scenario: A project without a team

- **WHEN** `/harnex:review` runs in a project whose chosen profiles are all single-file
  and whose choices carry no roster
- **THEN** only the core reviewer runs, exactly as before this capability existed

#### Scenario: A rendered agent is missing from disk

- **WHEN** a `review`-phase agent `/harnex:review` would start — on the team, or
  rendered by the profiles when no roster is recorded — is not
  present under `.claude/agents/`
- **THEN** `/harnex:review` says so, names `/harnex:update` as the remedy, and finishes
  with the reviews it could obtain
