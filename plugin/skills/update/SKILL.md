---
name: update
description: Refresh a harnessed project's harness-owned paths and entries from its own recorded choices, asking nothing. Use when the harness's own content has changed since the project was set up, or after a fresh clone, and the project should catch up.
---

# Updating a project

Update refreshes `.harnex/rules.md`, the permission-floor entries in `.claude/settings.json`,
the Playwright entry in `.mcp.json` if one is already there, and the rendered agents under
`.claude/agents/` — from the choices the project already recorded in `.harnex.yml` when it
ran `/harnex:setup`. Each rendered agent is rewritten when the harness's own role or
profile fragment changed and left byte-stable otherwise; an agent the record lists that a
dropped profile no longer renders is removed. It asks no question: every input the script
needs is already recorded, so there is nothing for you to ask the person and nothing for
you to decide on their behalf — the removal included, since everything in an update plan
was already approved when the project ran setup.

Update re-renders from the recorded roster and profiles: the `team` and `bench` lists, when
the project recorded them, and the profiles recorded alongside. A name added to or removed
from the roster takes effect on the next update — an added name is rendered, a removed one's
agent is removed. A dropped profile turns a prefixed agent into the generic one: the agent
that profile rendered is removed and the same specialist is rendered as
`.claude/agents/<specialist>.md` instead, if the roster still names it. A project with no
recorded roster is rendered from its profiles alone, as before.

The script is at `${CLAUDE_PLUGIN_ROOT}/scripts/update.py`. Run it with `uv run`.

## What this skill never does

- Create or write into a project-owned file — `AGENTS.md`, `CLAUDE.md`, `.harnex.yml`, or
  `openspec/config.yaml`. Those stay `/harnex:setup`'s alone, including inserting a pointer
  line into one or creating one that is missing.
- Approve a pointer-line insertion or the Playwright MCP entry on the person's behalf. Those
  are `/harnex:setup`'s own approvals; update only reports what is missing or not yet
  approved, it never writes it.
- Ask a question, or offer to adopt an unaccounted-for file. A conflict stops the run and
  names `/harnex:setup`'s own adoption path instead.
- Add a roster to the choices file. Update never adds `team` or `bench` to `.harnex.yml` (or
  `.harnex/config.yml`); a roster is recorded only by `/harnex:setup`.

## 1. Run it

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/update.py" --project <project root>
```

`--project` defaults to the current directory. It plans and writes in one pass — there is no
separate plan step and no approval to collect, since everything in an update plan was already
approved when the project ran setup.

## 2. Present the report plainly

Show the person what the script printed, as it printed it — every notice, not a summary of
the ones you judge interesting:

- **A missing pointer line** — the script names the file and says the line is missing; it
  was left alone. Point to `/harnex:setup` if the person wants it inserted.
- **A missing project-owned file** — `AGENTS.md`, `CLAUDE.md`, or similar, reported and
  skipped, never created. Point to `/harnex:setup`.
- **A Playwright entry not yet approved** — reported the same way, with what it would add;
  point to `/harnex:setup` for the approval.
- **A `Removed:` line** — names each stale agent the run deleted, by path, because a
  dropped profile no longer renders it; show it as printed, asking nothing.
- **Nothing to do** — the project is already current; say so plainly, there is nothing else
  to report.

Two refusals write nothing at all:

- **No `.harnex.yml`** — the project has never been set up. Point to `/harnex:setup`.
- **`.harnex.yml` present, no manifest** — there is no record of what the harness owns here,
  so update will not guess. Point to `/harnex:setup`'s own adoption path, which can build
  that record.

A conflict — a harness-owned file whose content matches neither the recorded fingerprint nor
what the harness would write now, meaning it was edited by hand — also stops the run before
anything is written. A rendered agent, current or stale, is such a file: a conflict on an
agent path stops the run like any other. Name the file the script names, and point to
`/harnex:setup`'s adoption, the same as any other conflict; update itself never adopts one.
