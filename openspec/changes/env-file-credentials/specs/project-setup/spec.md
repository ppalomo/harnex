## ADDED Requirements

### Requirement: Setup notices the `.env` convention only when `jev` is chosen

When the project's answer for `decision_model` is `jev`, setup's plan SHALL show a
notice naming the `.env` file the `jev` backend reads (`decision-model`'s `.env`
fallback), the key it expects (`OPENROUTER_API_KEY=`), and that the person is
responsible for keeping that file out of version control. Consistent with the existing
rule that setup never modifies the project's own version-control exclusions, this
notice SHALL be purely informational: setup SHALL NOT read, write, or otherwise touch
`.env` or the project's `.gitignore` to produce or act on it. When `decision_model` is
not `jev`, setup SHALL NOT show this notice.

#### Scenario: `jev` is chosen

- **WHEN** setup runs in a project whose answer for `decision_model` is `jev`
- **THEN** the plan shows the notice naming `.env` and `OPENROUTER_API_KEY=`, and
  neither `.env` nor `.gitignore` is read or written as a result

#### Scenario: `mock` is chosen

- **WHEN** setup runs in a project whose answer for `decision_model` is `mock`
- **THEN** no `.env` notice is shown

#### Scenario: The choice changes from `jev` to `mock`

- **WHEN** a project's recorded `decision_model` changes from `jev` to `mock` and setup
  or update is run again
- **THEN** the notice is no longer shown; no earlier run of this requirement ever wrote
  anything for it to leave in place
