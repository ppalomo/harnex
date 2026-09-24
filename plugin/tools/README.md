# Pillar 2 · Action & Tools

The hands: what the agent can actually do, and what it needs installed to do it.

## What belongs here

- **MCP server declarations** under `mcp/`: which servers a harnessed project gets, and
  what each is for.
- **Stack profiles** under `profiles/`: one file per stack, holding its check command, its
  conventions and the tools it expects. **This is the only place in the plugin where a
  technology may be named.** A profile is chosen per project, not assumed.

## What does not

- **The commands and the skills themselves.** They live at the plugin root, where Claude
  Code looks for them, and they say which pillar they belong to. Most belong to this one.
- **Rules.** A profile may state a convention that applies only to its stack, but a rule
  that holds everywhere is stated once in pillar 1.
- **Routing.** Which tool or model runs a phase is a decision, and decisions live in
  pillar 3.
- **Credentials.** A profile names the tool, never the key that reaches it.

## Filled by

`C1c` — the setup skill and the templates it writes. Then `C3`, which moves the first two
stack profiles in and adds what the build loop needs.
