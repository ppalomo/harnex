## Purpose

What `/harnex:update` is: the command that re-renders a harnessed project's harness-owned
paths and entries from its already-recorded choices, without asking a question, without
touching anything the project owns, and what it does when the project cannot be refreshed
this way.

## ADDED Requirements

### Requirement: One command refreshes harness-owned content, without asking

The harness SHALL provide a single command that reads a project's recorded choices and its
generation record, and brings every harness-owned path and entry up to date with those
choices and the harness's own current content. The command SHALL ask no question: every
input it needs SHALL already be recorded.

#### Scenario: The harness changed since setup

- **WHEN** the harness's own content changes after a project was set up — a rule edited, a
  rendering changed — and the command is run in that project
- **THEN** every harness-owned path or entry affected by the change is re-rendered and
  written, and the project's recorded choices are unchanged

#### Scenario: Nothing to refresh

- **WHEN** the command is run and no harness-owned path or entry differs from what the
  project's recorded choices and the harness's current content would produce
- **THEN** it reports nothing to do and no path changes

### Requirement: Update shares setup's regeneration sequence, scoped to harness-owned content only

The command SHALL use the same survey → plan → stop-on-conflict → write sequence setup
uses, applied only to harness-owned paths and entries. It SHALL NOT create a project-owned
file, SHALL NOT insert a line into one, and SHALL NOT offer to adopt an unaccounted-for
file — each of those stays an explicit choice made through setup. Where setup's own plan
would propose such a write, the command's plan SHALL instead only report what is missing,
the same way it already reports a missing pointer line.

#### Scenario: A project-owned file is missing something

- **WHEN** the command runs and a project-owned file is missing a pointer line or an
  entry setup would otherwise propose
- **THEN** the plan reports what is missing and why it matters, and the file is left
  untouched

#### Scenario: An unaccounted-for harness file

- **WHEN** the command finds a harness-owned path present whose content matches neither
  its recorded fingerprint nor the content about to be written
- **THEN** it stops before writing anything, names the file, and says to run setup, which
  can adopt it — the command itself offers no adoption

### Requirement: Update requires a project that has already been set up

The command SHALL refuse, without writing anything, in a project holding no record of the
project's choices, and SHALL refuse, without writing anything, in a project whose choices
are recorded but whose generation record is absent. Each refusal SHALL name the command
that can resolve it.

#### Scenario: Never set up

- **WHEN** the command is run in a project with no record of the project's choices
- **THEN** it refuses, says the project has not been set up, and names setup as the
  command to run instead

#### Scenario: Choices recorded, generation record missing

- **WHEN** the command is run in a project whose choices are recorded but whose
  generation record is absent — deleted, or the project was harnessed by hand
- **THEN** it refuses, says it will not guess what the harness owns, and names setup as
  the command that can adopt the project

### Requirement: A fresh clone updates unaided

The command SHALL complete in a project freshly cloned from one that was set up, reading
only what is committed, asking nothing and refusing nothing on account of the clone being
fresh.

#### Scenario: Cloned, then updated

- **WHEN** a harnessed project is cloned on another machine and the command is run before
  anything else touches it
- **THEN** every committed harness-owned path is recognised from the committed record, the
  runtime state location is restored, and the command asks nothing
