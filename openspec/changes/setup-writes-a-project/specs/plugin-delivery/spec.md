## MODIFIED Requirements

### Requirement: The harness installs as a Claude Code plugin

The repository SHALL publish a plugin catalogue at its root that lists exactly one
plugin, and that plugin SHALL install into Claude Code from a checkout of the
repository without any further build step. Installing it SHALL change nothing about how a
project behaves until that project has been set up: in a project that has not, every
component the plugin contributes SHALL be inert.

#### Scenario: Installing from a local checkout

- **WHEN** a user adds the repository root as a plugin marketplace and installs the
  harness plugin by name
- **THEN** the installation succeeds and the plugin is listed as installed, with its
  name and version

#### Scenario: Installing on a machine that has never seen the harness

- **WHEN** the installation is performed on a machine with no prior harness state, no
  API key for the decision model and no other plugin installed
- **THEN** the installation succeeds and no step asks for a credential

#### Scenario: The plugin does nothing on its own

- **WHEN** the plugin is installed and a session is started in a project holding no record of
  the harness's choices
- **THEN** the session behaves as it did before the installation: nothing the plugin
  contributes acts, nothing is read from the project beyond looking for that record, and no
  component reports anything

#### Scenario: A session in a harnessed project

- **WHEN** the plugin is installed and a session is started in a project that has been set up
- **THEN** the components the plugin contributes are available, and each acts only where the
  project's recorded choices enabled it
