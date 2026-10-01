## MODIFIED Requirements

### Requirement: One interface, two backends, chosen by the project

The harness SHALL expose one decision interface, `decide(question_id, state)`, with
exactly two backends: `mock`, which never contacts a network, and `jev`, which calls
OpenRouter's Decisions endpoint. The backend used SHALL be the one recorded at the
project's `.harnex.yml` `decision_model` key, and the interface SHALL behave identically
to every caller regardless of which backend answers.

Before treating `OPENROUTER_API_KEY` as absent, the `jev` backend SHALL look for it in
two places, in order: the process environment first, then an `OPENROUTER_API_KEY=` line
in a `.env` file at the project root (the same project the interface's `--project`
already names). The process environment SHALL always win when both carry a value. The
`.env` file SHALL be read as flat `KEY=VALUE` lines only — no shell expansion, no
`export` prefix, no interpolation — and a `.env` that does not exist, cannot be read, or
does not declare the key SHALL be treated exactly as if it were absent.

#### Scenario: A project with no backend chosen

- **WHEN** a project's `.harnex.yml` does not record `decision_model`
- **THEN** the interface behaves as `mock`

#### Scenario: A project with `jev` chosen and no key

- **WHEN** `decision_model` is `jev`, the `OPENROUTER_API_KEY` environment variable is not
  set, and the project's `.env` does not declare it either (or no `.env` exists)
- **THEN** the interface never attempts a network call and answers as it would on any
  other `jev` failure

#### Scenario: The key comes from the project's `.env`

- **WHEN** `decision_model` is `jev`, the `OPENROUTER_API_KEY` environment variable is not
  set, and the project's `.env` declares `OPENROUTER_API_KEY=<value>`
- **THEN** the interface uses that value to call OpenRouter, exactly as if it had been
  exported

#### Scenario: Both the environment and `.env` carry a value

- **WHEN** `decision_model` is `jev`, the `OPENROUTER_API_KEY` environment variable is
  set, and the project's `.env` also declares the key with a different value
- **THEN** the interface uses the environment variable's value and never reads the
  `.env` file's value for the key

### Requirement: Every call is recorded, whether or not it resolves

Every call to `decide()` SHALL append one line to the project's decision journal, naming
the question, a hash of the state, the probabilities returned (if any), the confidence (if
any), the outcome, the rule that produced it, and the backend that answered — whether or
not the call resolved. The journal line SHALL NOT include the `OPENROUTER_API_KEY` value,
regardless of whether it came from the environment or from the project's `.env`.

#### Scenario: An unresolved call is still journaled

- **WHEN** the backend cannot answer and the interface returns an unresolved outcome
- **THEN** one journal line is still appended, recording that no decision resolved and why

#### Scenario: A call resolved with a key read from `.env`

- **WHEN** a call resolves using a key the interface read from the project's `.env`
- **THEN** the journal line records the call exactly as it would for a key read from the
  environment, and carries no trace of the key's value or its source
