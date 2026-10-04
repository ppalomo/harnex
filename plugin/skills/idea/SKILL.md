---
name: idea
description: Capture a one-line idea into the project's running backlog, docs/ideas.md, for later exploration. Use when the person wants to jot an idea down without starting a change.
---

# Capturing an idea

You add one idea to the project's own running backlog, `docs/ideas.md` — a place to put
things down before they're ready for `/harnex:explore`, not a change, not a task, nothing
under `openspec/`.

## 1. Read or create the backlog

Read `docs/ideas.md` if it exists. If it does not, create it with this header, verbatim:

```markdown
# Ideas

A running backlog of ideas for this project. Add one with `/harnex:idea "..."`; think one
through with `/harnex:explore` when you're ready.
```

## 2. Write the entry

Take the person's own framing of the idea — never invent scope they did not ask for — and
turn it into one entry:

- A short, descriptive `##` heading: not "idea 1", not the literal sentence verbatim if it
  runs long — a title someone could scan and recognise later, and grep for.
- One line under it: `*<today's date, YYYY-MM-DD> · tags: <one or more free-text tags>*`.
  Pick tags from what the idea is actually about (area, component, kind of change); there
  is no fixed taxonomy to maintain.
- One short paragraph: the idea itself, in the person's own words, lightly cleaned up for
  clarity. Do not expand it into a proposal, a plan, or a list of steps — that is what
  `/harnex:explore` and `/harnex:propose` are for.

Insert the new entry directly below the header, above every entry already there — newest
first, so the backlog reads like an inbox, not a changelog.

## 3. Finish

Show the person the entry you just added, exactly as written, and where it landed. Do not
commit it — like any other edit to a project-owned file, that is their call, on their own
schedule.

## What this skill never does

- Create or touch anything under `openspec/`, or run `openspec`.
- Turn the idea into a plan, a task list, or a decision about tools or models.
- Commit the file it just edited.
- Invent scope, detail, or next steps the person did not say.
