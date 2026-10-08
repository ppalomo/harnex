## MODIFIED Requirements

### Requirement: Visibility is a per-project choice, read by every harness operation

The project's recorded choices SHALL include a `visibility` value of either `shared` or
`local`, defaulting to `shared`. Every harness operation that decides where to write a
path, which file to share a permission entry with, or where to run an OpenSpec command
SHALL read this value rather than infer it from what it finds on disk.

#### Scenario: The default

- **WHEN** a project's recorded choices do not set `visibility`
- **THEN** every harness operation treats it as `shared`, matching behaviour before this
  value existed apart from the deliberate additions `shared` itself later received (the
  `.env` exclusion and setup's clean working tree requirement, in `project-setup`)

#### Scenario: Local visibility recorded

- **WHEN** a project's recorded choices set `visibility` to `local`
- **THEN** every harness operation that would otherwise write a project-shared path
  writes its local-visibility equivalent instead
