# harnex — working instructions

harnex is a public, reusable harness for AI coding agents, delivered as a Claude Code
plugin and organised by the five pillars of a harness. Read `docs/PLAN.md` before
proposing anything: it holds the philosophy, the layout, the roadmap and the decisions
already taken.

## Language

Everything committed is written in **English**: code, docs, rules, roles, commit
messages, OpenSpec artifacts, diagrams, and the command names (`explore`, `propose`,
`apply`, `verify`, `ship`).

## Method

Spec-driven development with OpenSpec. A change gets a proposal, a design, delta specs
and a task list before any file under `plugin/` is written. When a change lands, sync its
deltas into `openspec/specs/` and update `docs/PLAN.md` to match.

## Layout rules

- Every component lives in **exactly one pillar** directory under `plugin/`: `context/`,
  `tools/`, `orchestration/`, `control/`, `feedback/`. If it seems to belong to two, it
  is two components.
- `plugin/commands/`, `skills/`, `agents/`, `hooks/` and `scripts/` are where Claude Code
  looks; what they contain still belongs to one pillar and says which.
- Technologies are named only in `plugin/tools/profiles/`.
- Nothing committed names a project, its domain vocabulary, a private resource or a
  credential. A component that needs a project fact reads it from the importing
  project's `AGENTS.md` at task time, and says so.
- A rule is stated once, in `plugin/context/rules/`. If it is enforced, the enforcement
  lives in `control/` or `feedback/` and the rule file names it.
- Agents and skills use the minimum frontmatter: `name`, `description`, and `tools` for
  agents. Skills use the cross-tool `SKILL.md` format; `name` equals the directory name.

## Git

No AI author or co-author lines in commits or pull requests, ever. Commit messages are
conventional and in English.

## Tests

Run the repository's own checks with `uv run --with pytest pytest`. They check the
plugin's layout, that nothing private reached it, and that both manifests validate; the
manifest check skips itself when the Claude Code CLI is absent.

## Before committing

- `uv run --with pytest pytest` passes.
- `claude plugin validate plugin --strict` and `claude plugin validate . --strict` pass,
  and `openspec validate --all` passes.
- Nothing under `plugin/` names a project or a private resource.
- `docs/PLAN.md` still describes the repository as it is; diagrams regenerated if the
  layout or the workflow changed (`python3 docs/diagrams/build.py`).
