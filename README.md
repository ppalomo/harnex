# harnex

A public, reusable **harness** for AI coding agents.

**Agent = Model + Harness.** The model reasons; the harness is everything around it that
lets it act safely and verifiably: instructions and memory, tools, the agentic loop,
guardrails, and verification. harnex centralises the generic parts of that so a project
imports them in one command instead of rebuilding them.

> Status: **planning**. The plan is in [`docs/PLAN.md`](docs/PLAN.md). Nothing is
> importable yet.

## The five pillars

The repository is organised by the five pillars of a harness, one directory each under
`harness/`:

| Pillar | Directory | Holds |
|---|---|---|
| 1 · Context & Memory | `harness/context/` | instruction files, importable rule sets, persistent state, compaction rules |
| 2 · Action & Tools | `harness/tools/` | skills, MCP integrations, sandboxes |
| 3 · Orchestration | `harness/orchestration/` | the SDD loop, roles, routing |
| 4 · Control & Guardrails | `harness/control/` | permissions, shell guard, human approvals |
| 5 · Feedback & Verification | `harness/feedback/` | checks, hooks, reviewer, logs |

## Division of labour

| Actor | Role |
|---|---|
| **Claude** | plans and architects: explores, proposes, designs, decomposes, reviews |
| **Codex** | builds: implements, tests, designs interfaces |
| **Jev** | decides: typed `Choice` / `Score` / `Noul` answers for routing, risk and confidence gates |
| **Human** | approves what is irreversible |

## Importing it into a project

Planned shape, one command each:

```bash
uvx copier copy gh:ppalomo/harnex .   # first import
uvx copier update                     # pull later harness changes
```

The template writes `AGENTS.md` with the rule sets you chose, `CLAUDE.md`, the skills for
Codex and Claude, hooks, permissions and the OpenSpec configuration. Harness-owned files are updated in place;
project-owned sections are never touched.

## Developing harnex

harnex develops itself with its own harness: spec-driven development with
[OpenSpec](https://github.com/Fission-AI/OpenSpec). Every phase in the plan is one change.
Working instructions for agents are in [`AGENTS.md`](AGENTS.md).

## Licence

MIT.
