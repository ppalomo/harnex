# playwright

The Playwright MCP server verifies a running UI application during `/harnex:verify`. In
this version, `verify_checks.py`'s own Playwright step is a stubbed placeholder — it
records that Playwright MCP is not yet configured, rather than driving this server against
a running app; the profile-gated wiring and the facts-file shape are real, the check itself
is future work.

## Ownership

This server is project-owned, not declared by the plugin. Its entry belongs in the
project's `.mcp.json`; the project owns every other entry in that file.

## When present

`/harnex:setup` shows the exact entry and writes it only after an explicit yes when the
project's recorded profiles include a UI stack. `/harnex:update` re-evaluates the same
condition on later runs. A project with no UI profile gets no entry.
