## MODIFIED Requirements

### Requirement: What the harness generated is recorded, and the record is committed

The harness SHALL keep, in the project, a record of everything it generated: every path it
owns with a fingerprint of the content it wrote, and, for the one file it shares with the
project, exactly the entries it wrote. Under `shared` visibility, that record SHALL be
part of what the project commits, so that ownership is known in a fresh clone without
inspecting anything else. Under `local` visibility, the record SHALL exist in the same
form and SHALL be read the same way by every later harness operation, but SHALL NOT be
part of what the project commits, consistent with every other path local visibility
writes.

#### Scenario: Reading what the harness owns

- **WHEN** any harness operation needs to know whether a path is its own
- **THEN** it reads the record, which names every harness-owned path with the fingerprint of
  the content written, and the entries it owns inside the shared file

#### Scenario: A fresh clone

- **WHEN** a harnessed project with `shared` visibility (or no recorded visibility) is
  cloned on another machine
- **THEN** the record is present and ownership is established without asking the person and
  without re-deriving it from the files

#### Scenario: A fresh clone, local visibility

- **WHEN** a harnessed project with `local` visibility is cloned on another machine
- **THEN** the record is absent, since it was never committed, and setup is run again
  rather than restoring it — the same way the runtime state location is restored today
