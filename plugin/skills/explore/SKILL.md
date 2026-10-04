---
name: explore
description: Think an idea through before proposing it — a conversation, not a procedure. Use when the person wants to explore, clarify, or sanity-check something before committing it to a change, or hasn't decided yet whether it is worth one.
---

# Exploring an idea

You write nothing here. This phase is a conversation that helps the person clarify what
they want before they turn it into a proposal — never a change directory, never a file
under `openspec/`, never the verifier, since there is nothing yet for either to act on.

## 1. Print the advice line, once, before anything else

Build a small state document:

```json
{"phase": "explore", "task": "<the person's own framing of the idea, one paragraph>", "profiles": []}
```

`profiles` comes from the project's recorded choices — `.harnex/config.yml` if it exists
(`local` visibility), otherwise `.harnex.yml` — if either exists (its `profiles` list);
otherwise leave it empty. Then run:

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/decide.py" ask --question phase.route --state <file> --project .
```

Read the one JSON object it prints:

- If `"resolved": true`, print `Decision (advice): explore → <decision> · confidence
  <confidence>`.
- Otherwise, print `Decision (advice): explore → unavailable (<reason>)`.

Either way, **do not ask the person to pick a tool or model.** This phase runs in the main
session, whose model you cannot switch mid-conversation; the line is information, not a
question, because there is nothing here for them to act on. Then move straight on.

## 2. Hold the conversation

Ask what the person is trying to do, and think it through with them: what problem it
solves, what it would touch, what could make it harder than it looks, whether it is one
change or several. Use `docs/PLAN.md` (or the equivalent project context) to ground the
discussion in what already exists, rather than treating the idea in a vacuum. If the
person points at something already written down in `docs/ideas.md` — by its title or by
description — read that entry first and start from what it already says, rather than
asking them to restate it.

## 3. Leave it to the person

There is no artifact that marks this phase done. When the idea feels clear enough, say so
and suggest `/harnex:propose`; if it still needs more thought, say that instead. Either way
the decision to move on is theirs, not something this skill decides for them.

## What this skill never does

- Create a file under `openspec/`, or run any `openspec` command.
- Start the verifier — there is no change yet for it to review.
- Ask the person to choose a tool or model for this phase.
