## ADDED Requirements

### Requirement: Update refreshes the rendered agents from the recorded profiles

The command SHALL re-render every agent the project's recorded profiles produce, write
those whose content changed, remove those the record lists but the profiles no longer
produce when they still match their fingerprint, and stop on a conflict for any that
was edited by hand — asking nothing, since the profiles were recorded at setup.

#### Scenario: A role or a fragment changed in the harness

- **WHEN** the harness's own role prompt or profile fragment changes and the command
  runs in a project that chose that profile
- **THEN** the affected agents are rewritten, the record is updated, and the project's
  recorded choices are unchanged

#### Scenario: A fresh clone of a project with a team

- **WHEN** a `shared` visibility project with rendered agents is cloned fresh and the
  command runs in the clone
- **THEN** every rendered agent is reported unchanged, since it was committed with the
  record
