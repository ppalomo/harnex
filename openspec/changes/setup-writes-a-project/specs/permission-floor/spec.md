## Purpose

The minimum set of permission entries a harnessed project carries so that the actions the
harness refuses or asks about are still refused or asked about when nothing of the harness
is running, and what is reported when the project's own permissions undercut them.

## ADDED Requirements

### Requirement: A harnessed project carries a permission floor

A harnessed project SHALL carry, in the file the host reads its permissions from, entries
that refuse what the harness refuses and ask about what the harness asks about, expressed in
the host's own permission syntax. Those entries SHALL be present whether or not any harness
component is installed, running or working.

#### Scenario: A project with no harness component running

- **WHEN** a command the harness would refuse is attempted in a harnessed project and nothing
  of the harness intercepts it
- **THEN** the host refuses it on the floor's entry alone

#### Scenario: A command the harness would ask about

- **WHEN** a command the harness would put to the person is attempted and nothing of the
  harness intercepts it
- **THEN** the host asks the person before it runs

### Requirement: The floor comes from the same statements the harness enforces

The floor's entries SHALL be derived from the harness's own statements of what must be
refused and what must be asked about, so that the floor and any later component enforcing the
same statements cannot state different things. Every statement that declares this kind of
enforcement SHALL be covered by at least one floor entry, or SHALL be recorded as one the
host's syntax cannot express.

#### Scenario: Every statement is covered

- **WHEN** the floor is checked against the harness's statements of what is refused and asked
  about
- **THEN** each statement resolves to at least one floor entry, or to a recorded note saying
  the host's syntax cannot express it and that it is covered only by a component that must be
  running

#### Scenario: A statement added without a floor entry

- **WHEN** a statement declaring this kind of enforcement has neither a floor entry nor the
  recorded note
- **THEN** the check fails and names the statement

### Requirement: The floor merges by entry, never by text

The floor SHALL be merged into the project's permission file as data, entry by entry. Entries
the project already has SHALL be preserved exactly, entries the harness already wrote SHALL
NOT be duplicated, and the entries written SHALL be recorded as the harness's own.

#### Scenario: A project that already has its own permissions

- **WHEN** the floor is merged into a permission file holding the project's own entries
- **THEN** the floor's entries are present, every entry the project had is still there
  unchanged, and the harness's entries are recorded as its own

#### Scenario: Merging a floor that is already there

- **WHEN** the merge runs again on a project that already carries the floor
- **THEN** no entry is duplicated and the file is left byte-identical

### Requirement: A project permission that undercuts the floor is a conflict

A project entry that would allow what the floor refuses or asks about SHALL be reported as a
conflict and SHALL NOT be removed, narrowed or overridden by the harness. The run SHALL stop
before writing anything.

#### Scenario: A project allowing what the floor asks about

- **WHEN** the survey finds a project entry allowing a command the floor asks about
- **THEN** the run stops before any write, names the entry and the floor entry it undercuts,
  and leaves the resolution to the person

#### Scenario: A broad project entry

- **WHEN** a project entry is broad enough to cover commands the floor refuses, without naming
  them
- **THEN** it is reported with what it covers, so the person can narrow it or accept it
  knowingly

### Requirement: The floor says what it guarantees and what defeats it

The floor SHALL state the kind of guarantee it gives and the limits of it: that it is coarser
than a component that parses a command, that it therefore asks about some things such a
component would refuse, and that a host mode which bypasses permissions altogether leaves
nothing of it in force. Setup SHALL warn about such a mode rather than claim protection it
cannot give.

#### Scenario: Reading what the floor promises

- **WHEN** a person or an agent reads the statement of the floor
- **THEN** it says that the floor matches coarsely, that it is a floor and not a replacement
  for a component that classifies a command, and what happens to each guarantee when that
  component is not running

#### Scenario: A mode that bypasses permissions

- **WHEN** setup completes
- **THEN** it warns that a host mode bypassing permissions leaves the floor with no effect, and
  says that no harness can defend against it
