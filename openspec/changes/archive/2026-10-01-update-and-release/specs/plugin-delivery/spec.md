## MODIFIED Requirements

### Requirement: The plugin declares its identity

The plugin SHALL declare its name and a semantic version in its manifest, and the
catalogue entry SHALL resolve to that manifest. The repository SHALL state, in the
document a new user reads first, the versions of Claude Code, Codex and OpenSpec the
current release was verified against, and installation and setup steps sufficient for
someone with no prior context on the project to reach a harnessed project without reading
any other document.

#### Scenario: Version is visible after installation

- **WHEN** the user lists installed plugins
- **THEN** the harness plugin is shown with the version declared in its manifest

#### Scenario: Strict validation passes

- **WHEN** the plugin is validated in strict mode
- **THEN** validation succeeds with no error and no warning

#### Scenario: Reading what a release was verified against

- **WHEN** someone reads the repository's README
- **THEN** it states the versions of Claude Code, Codex and OpenSpec the current release
  was verified against

#### Scenario: A stranger installs from the README alone

- **WHEN** someone with no prior context on the project follows the README's
  installation and setup steps in order
- **THEN** they reach a harnessed project, with every step they needed stated in the
  README itself
