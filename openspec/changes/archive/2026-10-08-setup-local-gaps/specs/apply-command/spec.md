## ADDED Requirements

### Requirement: Under local visibility the Codex builder is handed the rules

Under `local` visibility, where no `AGENTS.md` carries a pointer to the project's rules,
the apply loop SHALL start the Codex binding with a prompt whose first instruction is to
read `.harnex/rules.md` in the project and follow it, before the task's own text. Under
`shared` visibility the prompt SHALL be the task's own text, unchanged.

#### Scenario: A Codex task under local visibility

- **WHEN** `apply` starts a task routed to Codex in a project with `visibility: local`
- **THEN** the prompt it passes to Codex begins with the instruction to read
  `.harnex/rules.md` and follow it, followed by the task's text

#### Scenario: A Codex task under shared visibility

- **WHEN** `apply` starts a task routed to Codex in a `shared` project
- **THEN** the prompt is the task's own text and nothing else is added
