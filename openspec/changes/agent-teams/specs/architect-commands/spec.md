## ADDED Requirements

### Requirement: `propose` consults every advisor of the project's teams before `design.md`

Once the proposal exists and before `design.md` is written, `/harnex:propose` SHALL
start, once each, every agent rendered for the project's chosen profiles whose role's
phase is `propose`, with the proposal to read, and SHALL fold what each returns into
`design.md` as the architect's own input — naming the advisor whose brief a section
comes from. It SHALL NOT let an advisor write any artifact itself, and SHALL still call
the verifier exactly once after every required artifact exists.

#### Scenario: A project with an API designer

- **WHEN** `/harnex:propose` runs in a project whose chosen profile rendered an
  `api-designer`
- **THEN** the agent is started once with the proposal before `design.md` is written,
  `design.md` carries its brief under its name, and the verifier runs once at the end

#### Scenario: A project without advisors

- **WHEN** `/harnex:propose` runs in a project with no `propose`-phase agent
- **THEN** the command proceeds exactly as before this capability existed
