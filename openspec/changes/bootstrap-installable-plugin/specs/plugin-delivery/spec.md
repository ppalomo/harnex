## Purpose

How the harness reaches a machine: the catalogue and manifest that make it an
installable Claude Code plugin, the layout that plugin must keep so every component has
exactly one home, and what must never be published inside it.

## ADDED Requirements

### Requirement: The harness installs as a Claude Code plugin

The repository SHALL publish a plugin catalogue at its root that lists exactly one
plugin, and that plugin SHALL install into Claude Code from a checkout of the
repository without any further build step.

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

- **WHEN** the plugin is installed and a session is started
- **THEN** no command, skill, agent or hook is contributed by it, and the session
  behaves as it did before the installation

### Requirement: The plugin declares its identity

The plugin SHALL declare its name and a semantic version in its manifest, and the
catalogue entry SHALL resolve to that manifest.

#### Scenario: Version is visible after installation

- **WHEN** the user lists installed plugins
- **THEN** the harness plugin is shown with the version declared in its manifest

#### Scenario: Strict validation passes

- **WHEN** the plugin is validated in strict mode
- **THEN** validation succeeds with no error and no warning

### Requirement: The plugin's layout is the five pillars

Every directory inside the plugin SHALL be either one of the five pillar directories —
context, tools, orchestration, control, feedback — or one of the directories Claude Code
itself reads. Each pillar directory SHALL state, in a file an agent can read, what
belongs in it and what does not.

#### Scenario: A directory that is neither a pillar nor a Claude Code directory

- **WHEN** the plugin's layout is checked and a directory is found that is neither a
  pillar nor a directory Claude Code reads
- **THEN** the check fails and names the offending directory

#### Scenario: A pillar directory without its statement

- **WHEN** the plugin's layout is checked and a pillar directory has no statement of
  what it holds
- **THEN** the check fails and names that pillar

#### Scenario: All five pillars are present

- **WHEN** the plugin's layout is checked on a correct plugin
- **THEN** the check passes and reports all five pillars present

### Requirement: The plugin names no project and no private resource

Nothing published inside the plugin SHALL contain the name of a particular project, its
domain vocabulary, a private resource or a credential. A component that needs a project
fact SHALL read it from the importing project at task time.

#### Scenario: A private name reaches the plugin

- **WHEN** the plugin's contents are checked against the denylist of private names
- **AND** any file under the plugin contains one of them
- **THEN** the check fails, naming the file and the term found

#### Scenario: A clean plugin

- **WHEN** the plugin's contents are checked against the denylist and no file matches
- **THEN** the check passes

### Requirement: Every capability records how it is tried by hand

The repository SHALL keep one document listing the manual checks, with one section per
change, each giving the steps to run and the result to expect. A change that delivers a
capability SHALL add its section to that document.

#### Scenario: Reading the manual check for a change

- **WHEN** the owner opens the manual checks document looking for a landed change
- **THEN** they find a section named after that change, with its steps and its expected
  result, and can run it without reading any other document
