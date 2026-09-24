# harnex — working instructions

harnex is a public, reusable harness for AI coding agents, organised by the five pillars of
a harness. This file holds the rules for working in this repository.

## Language

Everything committed is written in **English**: code, docs, skills, roles, commit messages.
Reports to the maintainer are in **Spanish**.

## Layout rules

- Every component lives in **exactly one pillar** under `harness/`. If it seems to belong
  to two, it is two components.
- `harness/` is tool-independent: no `.claude/` or `.agents/` directories inside it. The
  tool-specific shape is produced by `template/` at import time.
- `profiles/` is the only place a technology may be named. `harness/` is stack-agnostic.
- Nothing committed names a project, its domain vocabulary, a private resource or a
  credential. If a component needs a project fact, it reads it from the importing
  project's `AGENTS.md` at task time, and says so.
- Skills use the cross-tool `SKILL.md` format: `name` equals the directory name,
  `description` says when to use it.

## Before committing

- Nothing under `harness/` names a tool directory, a project or a stack.
