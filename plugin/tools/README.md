# Pillar 2 · Action & Tools

The hands: what the agent can actually do, and what it needs installed to do it.

## What belongs here

- **MCP server declarations** under `mcp/`: which servers a harnessed project gets, and
  what each is for.
- **Stack profiles** under `profiles/`: one per stack, holding its check command, its
  conventions and the tools it expects. A profile is a flat `<name>.md`, or (`C10`) a
  directory `<name>/` whose `profile.md` is the profile and whose other `<specialist>.md`
  files are the team's fragments — what the stack adds to one specialist role under
  `../orchestration/roles/`. A flat profile is still valid; it simply has no team.
  Since `C11` a project may record a roster — `team:` and `bench:` in `.harnex.yml` —
  and then the roster decides who is on the team and a profile only supplies fragments
  for the specialists it names; a named specialist no chosen profile holds a fragment for
  is rendered as the generic agent, `.claude/agents/<specialist>.md`. Without a roster,
  a profile's fragments are its team, as `C10` left them.
  **`plugin/tools/profiles/` and `plugin/tools/mcp/` are the only places in the plugin
  where a technology may be named.** A profile is chosen per project, not assumed.

## What does not

- **The commands and the skills themselves.** They live at the plugin root, where Claude
  Code looks for them, and they say which pillar they belong to. Most belong to this one.
- **Rules.** A profile may state a convention that applies only to its stack, but a rule
  that holds everywhere is stated once in pillar 1.
- **Routing.** Which tool or model runs a phase is a decision, and decisions live in
  pillar 3.
- **Credentials.** A profile names the tool, never the key that reaches it.

## What is here

- `../skills/setup/` — the one command that brings a project to a harnessed state,
  `/harnex:setup`, and the procedure it follows: what to ask, in what order, and what
  counts as a yes.
- `../scripts/setup.py` — every step of that procedure that touches the filesystem. It
  surveys, plans, refuses while a conflict stands, and writes atomically with the record
  last. The questions belong to the session; the writes belong to the script.
- `profiles/fastapi/` — the first stack profile (`C3`), a directory since `C10`:
  `profile.md` holds the check command, conventions and tools expected, with project
  facts read from `AGENTS.md` rather than assumed; its team is `api-designer`,
  `migration-reviewer` and `security-reviewer`.
- `profiles/rails/` — a stack profile with the same three specialists, `C10`.
- `profiles/flutter/` — a UI profile whose team is `designer`, `accessibility-reviewer`
  and `security-reviewer`, `C10`. It is deliberately absent from `ui.json`, since the
  browser step does not apply to it; `profile.md` says what evidence `verify` reads
  instead.
- `profiles/react.md` — a flat stack profile, `C3`, with no team yet.
- `profiles/ui.json` — the registry of UI profiles; a name listed there means "Playwright
  applies" in `verify`.
- **The fragment convention**, `C10`: a fragment has no frontmatter and is written in the
  role's voice. `../scripts/render_agents.py` renders it as the `## For this stack:
  <profile>` section after the role's body, into `.claude/agents/<profile>-<specialist>.md`
  in a harnessed project. A fragment for a role the harness does not hold, or for an
  `apply`- or `verify`-phase role, is refused, not skipped — with or without a roster,
  every fragment of every chosen profile is read and checked, even one the roster does not
  name.
- **The roster's two keys**, `C11`: `setup` asks for them on a first setup, offering every
  specialist grouped by its role's `department` and proposing the chosen profiles'
  specialists as the team, and records both; `update` renders from them asking nothing.
  A project set up before `C11` gains them only by its owner adding them by hand.

## Still to come

`C6` adds the update command, which implements the contract `C1c` fixed.
