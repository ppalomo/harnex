## ADDED Requirements

### Requirement: Every stack reviewer is as read-only as the core reviewer

Every agent rendered from a `review`-phase role SHALL run with a declared tool list
that includes no capability to edit a file, write a file or run a shell command, by the
same mechanism that holds the core reviewer, and SHALL NOT carry a model override: the
core reviewer's fixed model is its own, not the team's.

#### Scenario: A rendered stack reviewer is inspected

- **WHEN** the tool list of an agent rendered from a `review`-phase role is read from
  its definition
- **THEN** it names no file-editing, file-writing or command-execution capability, and
  the agent is started without a model override
