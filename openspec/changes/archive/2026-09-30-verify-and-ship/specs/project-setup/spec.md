## ADDED Requirements

### Requirement: Setup proposes the Playwright MCP entry only for a UI profile, and only on explicit yes

When the project's recorded profiles include a UI stack, setup SHALL show the exact entry
it would add to the project's own `.mcp.json` for Playwright MCP verification, and SHALL
write it only after an explicit yes — the same pattern already governing a missing pointer
line in an entry file. When no UI profile is chosen, setup SHALL NOT propose or write this
entry. The entry setup writes SHALL be recorded in the manifest, by entry, the same way the
permission floor's entries in `.claude/settings.json` are recorded; every other entry
already present in `.mcp.json` SHALL be left alone.

#### Scenario: A UI profile is chosen

- **WHEN** setup runs in a project whose recorded profiles include a UI stack and no
  Playwright entry exists yet in `.mcp.json`
- **THEN** the plan shows the exact entry it would add, and it is written only after an
  explicit yes

#### Scenario: No UI profile is chosen

- **WHEN** setup runs in a project whose recorded profiles include no UI stack
- **THEN** no Playwright entry is proposed or written, and `.mcp.json` is untouched by this
  requirement

#### Scenario: The person declines

- **WHEN** setup shows the Playwright entry it would add and the person declines
- **THEN** `.mcp.json` is left unchanged, setup finishes the rest of its work, and the
  decision is not recorded as if it had been accepted

#### Scenario: The entry already exists

- **WHEN** `.mcp.json` already carries the Playwright entry setup would otherwise propose
- **THEN** the file is left byte-identical and the plan says so, the same way an entry file
  that already carries the pointer line is left alone

### Requirement: A changed profile re-evaluates the Playwright entry

Running setup or update again after the project's recorded profiles changed SHALL
re-evaluate whether the Playwright entry belongs in `.mcp.json`: proposing it if a UI
profile was newly chosen and it is not yet present, and leaving an already-written entry in
place if the profile was later dropped, rather than silently removing something the person
may still rely on.

#### Scenario: A UI profile is added later

- **WHEN** a project's recorded profiles gain a UI stack after an earlier setup run without
  one
- **THEN** the next setup or update run proposes the Playwright entry, the same as a first
  run would have

#### Scenario: A UI profile is later dropped

- **WHEN** a project's recorded profiles drop the UI stack after the Playwright entry was
  already written
- **THEN** the entry is left in `.mcp.json` rather than removed on the person's behalf
