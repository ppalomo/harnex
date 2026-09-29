## MODIFIED Requirements

### Requirement: The floor comes from the same statements the harness enforces

The floor SHALL be generated from the same pattern source the shell guard reads, so that
the floor and the guard cannot state different things for the same rule. Every statement
that declares `enforced_by: guard` SHALL be covered by at least one floor entry, or SHALL
be recorded as one the host's syntax cannot express. Regenerating the floor from that
source SHALL produce output identical to what is committed; a difference means the two
have drifted and the check that compares them SHALL fail.

#### Scenario: Every statement is covered

- **WHEN** the floor is checked against the harness's statements of what is refused and
  asked about
- **THEN** each statement resolves to at least one floor entry, or to a recorded note
  saying the host's syntax cannot express it and that it is covered only by a component
  that must be running

#### Scenario: A statement added without a floor entry

- **WHEN** a statement declaring this kind of enforcement has neither a floor entry nor the
  recorded note
- **THEN** the check fails and names the statement

#### Scenario: The floor and the guard's patterns agree

- **WHEN** the floor is regenerated from the pattern source the guard also reads
- **THEN** the regenerated file is byte-identical to the one committed

#### Scenario: The floor and the guard's patterns have drifted

- **WHEN** a pattern is added to or removed from the guard's source without regenerating
  the floor
- **THEN** the comparison check fails and names the entry that is missing or extra
