## MODIFIED Requirements

### Requirement: `propose` consults every advisor of the project's teams before `design.md`

Once the proposal exists and before `design.md` is written, `/harnex:propose` SHALL
start, once each, every agent of the project's team whose role's phase is `propose` —
the agents the roster's `team` list renders, or, for a project that records no roster,
every agent its chosen profiles render — with the proposal to read, and SHALL fold what
each returns into `design.md` as the architect's own input — naming the advisor whose
brief a section comes from. It SHALL NOT start an advisor on the project's `bench`,
SHALL NOT let an advisor write any artifact itself, and SHALL still call the verifier
exactly once after every required artifact exists.

#### Scenario: A project with an API designer

- **WHEN** `/harnex:propose` runs in a project whose `team` names `api-designer`
- **THEN** the agent is started once with the proposal before `design.md` is written,
  `design.md` carries its brief under its name, and the verifier runs once at the end

#### Scenario: An advisor on the bench

- **WHEN** `/harnex:propose` runs in a project whose `bench` names `designer` and whose
  `team` does not
- **THEN** the designer is not consulted, and `design.md` is written without its brief

#### Scenario: A roster and no profile

- **WHEN** `/harnex:propose` runs in a project that chose no profile and whose `team`
  names `designer`
- **THEN** the generic designer is consulted once before `design.md` is written

#### Scenario: A project without a roster

- **WHEN** `/harnex:propose` runs in a project whose choices carry neither `team` nor
  `bench` and whose chosen profile renders an `api-designer`
- **THEN** the agent is consulted exactly as before the roster existed

#### Scenario: A project without advisors

- **WHEN** `/harnex:propose` runs in a project with no `propose`-phase agent on its team
- **THEN** the command proceeds exactly as before this capability existed
