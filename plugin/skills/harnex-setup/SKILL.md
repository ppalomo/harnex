---
name: harnex-setup
description: Bring a project to a harnessed state — ask what it needs, show the plan, and write only after an explicit yes. Use when setting a project up with the harness for the first time, or when re-running setup after changing the project's choices.
---

# Setting a project up

You ask the questions and show what would happen. Every filesystem step is the script's,
so that the whole sequence can be checked without a session. You never write a file the
script would write, and you never approve anything on the person's behalf.

The script is at `${CLAUDE_PLUGIN_ROOT}/scripts/setup.py`. Run it with `uv run`.

## 1. Learn what is on offer, and what the project already answered

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" choices
```

It prints the rule sets, profiles and features the harness holds, the decision backends,
and the canary word setup proposes. Offer nothing that is not in that output: when a list
is empty, there is nothing to ask about, and the answer is an empty list.

Then read `.harnex.yml` in the project root. If it is there, those are the project's
answers: take them as given and do not ask again. Setup never rewrites that file.

## 2. Ask, in this order, only what you cannot derive

1. **Project name** — propose the directory's name.
2. **Rule sets** — list the sets on offer with one line each on what the set is for, and
   propose all of them. A project can drop any of them later by editing `.harnex.yml`.
3. **Profiles**, then **features** — ask only if the harness holds any.
4. **Canary word** — only if the `canary` set was chosen. Propose the word from `choices`
   and say what it is for: every answer ends with it, and a missing word is the cheapest
   sign that the rules may have dropped out of the context.
5. **Decision backend** — `mock` asks the person on every decision, `jev` calls the model
   and needs a key in the environment. Propose `mock`.
6. **Check command** — the command that must pass before anything is called done. You
   cannot derive it and there is no default: ask, and if the person does not know, find
   the project's own check and propose it for confirmation.

## 3. Show the plan before anything is written

Write the answers to a file outside the project — the session's temporary directory —
shaped like this, then plan:

```json
{
  "project_name": "…",
  "profiles": [], "sets": ["…"], "features": [],
  "canary": "…", "decision_model": "mock", "check_command": "…",
  "approvals": {"pointer_agents": false, "pointer_claude": false, "adopt": []}
}
```

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" plan --answers <file> --project <project root>
```

Show the person the plan as the script printed it, every line of it. Do not summarise the
conflicts away and do not reorder the lines.

## 4. Approvals are the person's, one by one

The approvals in the answers document start `false` and an empty list. Set one only after
the person has said yes to that exact thing, in this turn:

- **`pointer_agents` / `pointer_claude`** — the plan's notices show the exact line and
  where it goes. Ask for each file separately. If the person declines, say what does not
  work — the notice says it — and carry on: the rest of setup is unaffected, and the
  notice returns on every later run until the line is there.
- **`adopt`** — only for a path the plan reports as a conflict, and only after you have
  shown the difference between what is there and what the harness would write. Adoption
  replaces the file.

A silence, a "sounds good" about something else, or your own judgement that it is
obviously fine are not a yes. If you are unsure whether the person agreed, ask again.

## 5. Write

A conflict left standing means nothing is written, by design: say which conflicts remain
and what resolves each. Otherwise, once the person has approved the plan:

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" write --answers <file> --project <project root>
```

The script surveys again before it writes, so an approval given against a plan that has
since gone stale writes nothing and says why. Report the paths it wrote, and tell the
person what to do next: read `AGENTS.md` and fill in what only they know, since the
harness deliberately knows nothing about their project.

## What this skill never does

- Write, edit or create any of the project's files itself. The script writes; you ask.
- Set an approval the person did not give, or adopt a file to get past a conflict.
- Re-render `.harnex.yml`, `AGENTS.md`, `CLAUDE.md` or the OpenSpec config. They belong to
  the project: setup creates them when they are absent and never rewrites them.
