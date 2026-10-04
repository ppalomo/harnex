---
name: flash
description: Implement a small, already-understood change directly in this session — no proposal, no specs, no task list, no builder handoff. Use when the person wants something done now and the change is small enough that the full explore → propose → apply → verify → ship pipeline would be pure overhead.
---

# Flashing a small change

You implement a small, already-understood change yourself, in this session, right now —
no `openspec/` change directory, no `tasks.md`, no builder, no decision model routing a
build step anywhere. `/harnex:flash` is the deliberate escape hatch from the five-command
pipeline for work too small to be worth it: a doc fix, a one-file tweak, the kind of change
`/harnex:explore` would spend more words describing than it takes to make.

If the person's own description turns out, once you look at the code, to touch several
unrelated files or need real design judgement, say so and suggest `/harnex:propose`
instead — do not quietly turn `/harnex:flash` into an undeclared `/harnex:apply`.

## 1. Print the advice line, once, before anything else

Build a small state document:

```json
{"phase": "flash", "task": "<the person's own framing of the change, one paragraph>", "profiles": []}
```

`profiles` comes from the project's recorded choices — `.harnex/config.yml` if it exists
(`local` visibility), otherwise `.harnex.yml` — if either exists (its `profiles` list);
otherwise leave it empty. Then run:

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/decide.py" ask --question phase.route --state <file> --project .
```

Read the one JSON object it prints:

- If `"resolved": true`, print `Decision (advice): flash → <decision> · confidence
  <confidence>`.
- Otherwise, print `Decision (advice): flash → unavailable (<reason>)`.

Either way, **do not ask the person to pick a tool or model.** `/harnex:flash` always runs
in this session, on this model, by design — the line is a signal to the person, not a
switch: a low-confidence or `human` answer here is a hint that this change may be bigger
than `/harnex:flash` is for, not an instruction to delegate it. Then move straight on.

## 2. Branch before the first edit

Same git rule as every other change: one change, one branch, created before anything is
touched. Check the current branch and, if it is the project's default branch, create and
check out a new one named for the change before editing anything.

## 3. Make the change

Edit the code directly. Keep it to what the person asked for — nothing under `openspec/`,
no proposal, no specs, no task list. Read the project's own check command from
`AGENTS.md` (or the profile it names), the same place `/harnex:apply` reads it from, and
run it before calling the change done. If it fails, fix it or say plainly that it still
fails — never report the change as finished on a tree that was not checked.

`/harnex:review` is still there if the person wants an independent read on the diff before
going further; offer it, do not run it unasked.

## 4. Hand off to `/harnex:ship`

Do not commit, push, or open a pull request yourself. Tell the person the change is made
and checked, and that `/harnex:ship` will commit it, push the branch, and open the pull
request whenever they are ready — `/harnex:ship` recognises a branch with no `openspec/`
change behind it and takes care of it the same way, deriving the commit message and the
pull-request title and body from the diff itself, since there is no proposal to read one
from. Keeping that one path in `/harnex:ship` instead of a second copy here is deliberate:
a branch `/harnex:flash` touched and a branch a person edited by hand look identical to
`/harnex:ship`, and should.

## What this skill never does

- Create, read, or write anything under `openspec/`, or run `openspec`.
- Route the implementation to a builder, Codex or otherwise — it is always this session's
  own work.
- Commit, push, or open a pull request — that is `/harnex:ship`'s job, not this skill's.
- Silently grow into a multi-file redesign — it says so and points at `/harnex:propose`
  instead.
