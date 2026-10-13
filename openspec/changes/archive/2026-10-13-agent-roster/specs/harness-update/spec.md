## MODIFIED Requirements

### Requirement: Update refreshes the rendered agents from the recorded profiles

The command SHALL re-render every agent the project's recorded roster and profiles
produce — the `team` and `bench` lists when the choices record them, the chosen
profiles' fragments when they do not — write those whose content changed, remove those
the record lists but the choices no longer produce when they still match their
fingerprint, and stop on a conflict for any that was edited by hand — asking nothing,
since the roster and the profiles were recorded at setup or written by the person into
the project's own choices file. The command SHALL NOT add a roster to a project's
choices on its own.

#### Scenario: A role or a fragment changed in the harness

- **WHEN** the harness's own role prompt or profile fragment changes and the command
  runs in a project whose roster or profiles render an agent from it
- **THEN** the affected agents are rewritten, the record is updated, and the project's
  recorded choices are unchanged

#### Scenario: A name added to the roster

- **WHEN** the person adds a specialist's name to the project's `team` or `bench` and
  the command runs
- **THEN** that specialist's agent is rendered — prefixed by each chosen profile holding
  a fragment for it, generic otherwise — and recorded, and nothing else changes

#### Scenario: A name removed from the roster

- **WHEN** the person removes a specialist's name from both lists and the command runs
- **THEN** every agent rendered for that name, still matching its fingerprint, is
  removed and dropped from the record

#### Scenario: A profile dropped under a roster

- **WHEN** a project's roster names a specialist, the only chosen profile holding a
  fragment for it is dropped, and the command runs
- **THEN** the prefixed agent is removed and the generic agent of the same specialist
  is written in its place, both shown in the report

#### Scenario: A fresh clone of a project with a team

- **WHEN** a `shared` visibility project with rendered agents is cloned fresh and the
  command runs in the clone
- **THEN** every rendered agent is reported unchanged, since it was committed with the
  record
