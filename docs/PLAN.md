# harnex — development plan (v2.1)

harnex is a public, reusable **harness** for AI coding agents. It centralises everything
that turns a model into a working agent — instructions, tools, workflow, guardrails and
verification — so a new project gets it in one command instead of rebuilding it.

This is the second version of the plan. The first was reviewed by six independent
reviews ([REVIEW-2026-09-24.md](REVIEW-2026-09-24.md)) and a role study
([ROLES-2026-09-24.md](ROLES-2026-09-24.md)); this version applies their findings and the
owner's decisions. Version 2.1 applies a second, external review
([REVIEW-2026-09-25.md](REVIEW-2026-09-25.md)) taken after `C1b`: it closes the contracts
`C1c` depends on — adopting an existing project, where generation metadata lives, what
each guarantee really is — and moves forward the checks that could invalidate later
phases. It is a living document: every phase is delivered as one or more OpenSpec
changes, and when one lands this plan is updated to match.

**Diagrams** (open at https://excalidraw.com → *Open*, or with the VS Code Excalidraw
extension; regenerate with `python3 docs/diagrams/build.py`):

| Diagram | Shows |
|---|---|
| [01-overview](diagrams/01-overview.excalidraw) | Agent = Model + Harness; the five pillars and what each holds |
| [02-architecture](diagrams/02-architecture.excalidraw) | where things live: the repo, your machine, a project, the services |
| [03-workflow](diagrams/03-workflow.excalidraw) | the five commands, who plays each, the gates, the decision line |
| [04-apply](diagrams/04-apply.excalidraw) | the build loop, task by task |
| [05-guard](diagrams/05-guard.excalidraw) | what happens before any shell command runs |
| [06-roadmap](diagrams/06-roadmap.excalidraw) | the phases, what each delivers and how you try it |
| [07-layout](diagrams/07-layout.excalidraw) | the repository, pillar by pillar |

---

## 1. Philosophy

**Agent = Model + Harness.** The model is the brain: it reasons and decides. The harness is
the body and the workspace: it executes actions, manages memory, applies safety rules and
verifies results. Prompt engineering writes the best instruction; context engineering
chooses what enters the window; **harness engineering designs the deterministic system —
tools, rules, control loops, checks — in which the agent lives and works.**

A harness has five pillars. Every component in this repository belongs to exactly one, and
the layout of the plugin is the pillars.

| # | Pillar | Analogy | Holds in harnex |
|---|---|---|---|
| 1 | **Context & Memory** | eyes and memory | `AGENTS.md`, `.harnex/rules.md`, rule sets, the canary rule, OpenSpec config, progress conventions |
| 2 | **Action & Tools** | hands | the five commands, setup/update skills, profiles, MCP servers, the Codex plugin |
| 3 | **Orchestration** | nervous system | the workflow, the roles, the decision model's routing questions |
| 4 | **Control & Guardrails** | immune system | the permission floor, the shell guard, human approvals |
| 5 | **Feedback & Verification** | vitals | the check command, the verifier, the canary check, the decision journal |

Placement is by **topic**; `plugin/` is declarative (prompts, rules, questions) plus the
small scripts that execute them. Two doctrines:

- **A harness component knows nothing about any particular project.** It reads project
  facts from `AGENTS.md` at task time. A thin `AGENTS.md` gets an agent that asks instead
  of assuming.
- **A rule is stated once** (pillar 1). If it is also enforced, the enforcement lives in
  pillar 4 or 5 and the rule file names it. A rule that exists only as enforcement, with
  no statement the agent can read, is a bug.

## 2. Goals and non-goals

1. One public, centralised place for every generic harness component, organised by pillar.
2. A README a stranger understands, and installation in a few commands.
3. A `setup` that generates everything a project needs, and an `update` that refreshes
   what is the harness's without touching what is the project's.
4. Five commands — `explore`, `propose`, `apply`, `verify`, `ship` — that hide
   OpenSpec and let a **decision model pick which tool and model runs each delegated
   step**, saying so on screen. Where a phase runs in the main session the model can only
   recommend, and the line says so.
5. Every capability testable by the owner by hand, with instructions, on top of automated tests.

Non-goals: anything project-specific or confidential; replacing Claude Code or Codex;
an unattended mode (no `harnex run`); supporting tools other than Claude Code, with Codex
reached only through its official plugin.

## 3. How you work

You work in **Claude Code** (desktop or terminal). That is the cockpit. Everything else is
reached from there:

| Actor | Reached how | Role |
|---|---|---|
| **Claude** | the session itself, and subagents | architect (main session), verifier (fresh-context subagent), reviewer (fixed-model subagent), builder fallback |
| **Codex** | the official `codex@openai-codex` plugin: `/codex:rescue` delegates a task, `/codex:review` reviews. Codex CLI is installed but you never drive it. | builder |
| **Decision model** | a small Python client in the plugin, backend `jev` (via OpenRouter) or `mock` (asks you); swappable | picks tool + model per phase, judges command risk, gates progress |
| **You** | the commands, and the gates | choose direction, approve plan, approve commits and destructive commands |

Each command starts by asking the decision model who should run this phase with this
context, and prints one line before doing anything:

```
Decision: apply → Codex · gpt-6-sol · confidence 0.91
```

The decision is **binding** only where harnex delegates: routing to Codex means
`/codex:rescue --model <m>`, routing to Claude means a subagent with that `model:`. The
architect phases (`explore`, `propose`) and `ship` run in the main session, whose model
harnex cannot switch, so there the line is a **recommendation** and says so
(`Decision (advice): propose → Claude · fable · 0.78 — switch with /model`). When the
backend is `mock`, the line says so and asks you.

**Canary.** When a project enables the `canary` set, every answer must end with the word
declared in `.harnex.yml` (setup proposes `Hullaballoo!`) — stated for the model in
`AGENTS.md`, since the rendered `.harnex/rules.md` is a pure function of the chosen sets
and can only ever say "the word the project declares". A `Stop` hook reads the **main
session's** last answer and warns when the word is missing; it does not run on a
subagent's answer (`docs/decisions/`: a built-in subagent is not briefed on the project's
instructions, so a missing word there proves nothing). The warning is a **signal, not a
diagnosis**: a missing word proves that this one instruction was not followed in that
answer, which is the cheapest observable sign that the rules may have dropped out of the
context or been diluted — compacting or restarting is the usual remedy. Its presence
proves nothing about the other rules. It is the first rule that is both stated (pillar 1)
and checked (pillar 5).

## 4. Roles

Four roles in v0.1, from the role study. Prompts are tool-agnostic and follow one
skeleton (see the study). The orchestrator is you plus the commands.

| Role | Player | May write | Must refuse | Commands |
|---|---|---|---|---|
| `architect` | Claude, main session (`opus`; `fable` for hard designs) | the change's artifacts | source, tests, commits | explore, propose |
| `builder` | Codex via the plugin; Claude subagent as fallback | source and tests within the task's declared paths | ticking `tasks.md`, committing, editing specs, widening scope | apply |
| `verifier` | Claude subagent, fresh context, read-only | nothing | fixing, committing, reopening settled decisions | propose (design review), verify |
| `reviewer` | Claude subagent, fixed on `opus`, read-only | nothing | fixing, committing, judging spec coherence (the verifier's job) | review |

UI design is a `ui` profile the architect loads during `propose`, seeded from the
existing designer prompt; it produces `design.md`, the builder builds it, the verifier
checks it. Independence comes from **context separation**: the verifier never shares a
context with the builder. Commits happen only in `ship`, after your explicit yes.

### What holds a role to its boundary

A role's limits are held by one of three kinds of mechanism, and the plan names which,
because they promise different things:

- **Instruction (I)** — the rule is in the role's prompt and in `.harnex/rules.md`. It
  works as long as the model follows it; nothing stops a model that does not.
- **Prevention (P)** — something outside the model refuses the action before it happens.
- **Detection (D)** — a deterministic check after the fact notices the action, and the
  work is rejected or escalated before anything is accepted.

Two facts of the host bound what prevention can reach (verified against the Claude Code
docs for 2.1.267). Permission rules in `.claude/settings.json` apply to the **whole
session**, subagents included, so they cannot express "the builder may not, the architect
may"; per-role prevention comes only from a subagent's `tools` list and from a hook that
reads the `agent_type` field Claude Code adds to a subagent's tool calls. And a hook on
`Bash` does not see edits made through `Edit` or `Write`, nor anything Codex does inside
its own sandbox.

| Rule | architect (main session) | builder · Codex | builder · Claude subagent | verifier | reviewer |
|---|---|---|---|---|---|
| write only what the role may write | I · D: `propose` reports any change outside the change's directory | I · D: changed paths ⊆ the task's declared paths | I · D: same check | I · P: `tools` has no `Edit`, `Write` or `Bash` | I · P: `tools` has no `Edit`, `Write` or `Bash` |
| never tick `tasks.md`, never edit specs | — (the architect writes them) | I · D: protected paths (`openspec/`, `.harnex/`) unchanged after the delegation | I · D: same check | P: as above | P: as above |
| commit only in `ship` | I · P: guard asks, floor asks | I · D: `HEAD` and refs unchanged after the delegation | I · P: guard asks, floor asks | P: as above | P: as above |
| destructive commands, deletions, pushes ask | I · P: guard + floor | I only: `approvalPolicy` is hardcoded to `never` for every delegated call, so Codex itself never pauses to ask ([S1](decisions/2026-09-27-s1-delegating-to-codex.md)) — C4's guard hooks `Bash` in the main session and Claude subagents only, so it does not reach a command Codex runs inside its own sandbox; that ask still depends on Codex's own sandbox until a Codex-side hook is built, later, not in v0.1 · D: the diff is read before acceptance | I · P: guard + floor | P: as above | P: as above |
| credentials never leave the machine | I · P: floor denies reading secret files; guard asks | I · P: Codex CLI's own `read-only`/`workspace-write` sandbox toggle, as read from `codex.mjs` and, for `gpt-5.6-terra`, now confirmed by observation — [S1](decisions/2026-09-27-s1-delegating-to-codex.md)'s 2026-09-28 update: `read-only` refused a write the model itself reported, `--write` applied one, confirmed in `git status` | I · P: floor + guard | P: as above | P: as above |
| answers end with the canary word | I · D: Stop hook | I only | I · D: SubagentStop hook, when the set is on | I · D: SubagentStop hook | I · D: SubagentStop hook |

**What v0.1 honestly offers:** the builder's boundaries are instruction plus
deterministic detection before acceptance; prevention exists where Claude Code's
session-wide permissions, a subagent's `tools` list and the Bash guard reach, and on the
Codex side only as far as Codex's own sandbox goes. A Codex-side guard hook and
`Edit`/`Write` hooks keyed on `agent_type` are the later features that turn some D cells
into P. Rule files keep their `enforced_by` field and `**Enforced by:**` line, which name
the mechanism; their body says whether that mechanism prevents or detects (§7), and the
diagrams say the same, so nothing claims prevention where only detection exists.

## 5. Repository layout

```
harnex/
  README.md  LICENSE  AGENTS.md  CLAUDE.md
  .claude-plugin/marketplace.json     catalogue with one entry: the harnex plugin
  plugin/                             THE CLAUDE CODE PLUGIN — what a machine installs
    .claude-plugin/plugin.json          name, version
    commands/                           explore, propose, apply, verify, ship (pillar 2) — but see below
    skills/                             setup, update (pillar 2) — setup landed in C1c as a skill, no command
    agents/                             builder.md, verifier.md, reviewer.md (Claude adapters of the roles, pillar 3)
    hooks/hooks.json                    guard (PreToolUse Bash), canary (Stop, main session only) — inert without .harnex.yml
    context/                            1 · rules/ (one file per rule, grouped in sets), templates/ (AGENTS.md,
                                            CLAUDE.md, .harnex.yml, the pointer lines), memory.md
    tools/                              2 · mcp/ declarations, profiles/ (python-fastapi, react-vite)
    orchestration/                      3 · workflow.md, roles/ (prompts), decisions/ (typed questions, YAML)
    control/                            4 · floor.json (the permission floor), guard/ (patterns.yaml, guard.py), approvals.md
    feedback/                           5 · check-command.md, canary/canary.py, journal/format.md
    scripts/                            decide.py (backend interface), setup.py, update.py — Python, run with uv
  docs/                               PLAN.md, diagrams/, reviews, decisions/ (ADRs), smoke.md, observability.md (the owner's bench, not a component)
  openspec/                           harnex's own specs and changes
  tests/  pytest.ini                  harnex's own checks: the layout, the private names, the manifests
```

`C1c` learned that the host lists commands and skills in one inventory, so a command whose
only job is to invoke a skill of the same name is one component too many: the five workflow
commands are expected to land as skills for the same reason, and `commands/` stays in this
layout only for a command that would do something a skill cannot.

Rules that keep it honest: a component lives in exactly one pillar directory; technologies
are named only in `tools/profiles/`; nothing committed names a project, its vocabulary, a
private resource or a credential; agents and skills use the minimum frontmatter (`name`,
`description`, `tools` for agents) so a format change in Claude Code costs one field.

## 6. Delivery: install, setup, update

Two levels, one mechanism each. The **behaviour** (commands, skills, agents, hooks,
scripts, profiles, rule sources) lives in the plugin and is installed once per machine.
The **project's choices and facts** live in the project and are generated by `setup`.

Install, once per machine:

```bash
claude plugin marketplace add ppalomo/harnex
claude plugin install harnex@harnex
claude plugin install codex@openai-codex          # the official Codex plugin
export OPENROUTER_API_KEY=...                       # optional: real decision backend
```

Setup, once per project, from inside Claude Code: `/harnex:setup`. It asks for profiles,
rule sets, features, canary word and decision backend, and brings the project to this
state:

| Path | Owner | Committed | Notes |
|---|---|---|---|
| `AGENTS.md` | **project** | yes | created from a template only if missing; afterwards only you change it |
| `CLAUDE.md` | **project** | yes | created only if missing, with `@AGENTS.md` and `@.harnex/rules.md`; afterwards only you change it |
| `.harnex.yml` | **project** | yes | your answers: `project_name`, `profiles`, `sets`, `features`, `canary`, `decision_model`, `check_command` |
| `.harnex/rules.md` | harness | yes | rendered from the sets chosen |
| `.harnex/manifest.json` | harness | yes | generation metadata: every harness-owned path and entry, with its hash |
| `.claude/settings.json` | **shared, by entry** | yes | the harness owns the permission-floor entries it wrote, listed in the manifest; every other entry is yours |
| `.mcp.json` | **shared, by entry** | yes | the harness owns the Playwright MCP entry it writes (for a UI profile, on explicit yes), listed in the manifest; every other entry is yours |
| `openspec/config.yaml` | **project** | yes | created only if missing, with the harness's artifact rules; afterwards only you change it |
| `.harnex/state/` | runtime | no | decision journal and apply run state; ignored by a `.gitignore` inside the directory itself, so the project's own `.gitignore` is never touched |

**Local visibility (`C7`) replaces the table above entirely, never extends it.** Setup
also asks a `visibility` choice, `shared` (the table above, the default) or `local` — the
project is not being adopted by a team, only used by the person running it. Under
`local`, nothing is committed, and nothing above is created or modified, existing or not:

| Path | Owner | Committed | Notes |
|---|---|---|---|
| `AGENTS.md`, `CLAUDE.md`, `openspec/config.yaml`, `.claude/settings.json`, `.mcp.json` | **project** | — | never read for insertion, never written; exactly as they were before setup ran |
| `CLAUDE.local.md` | harness | no | one `@.harnex/rules.md` import; excluded via `.git/info/exclude`, never the project's own `.gitignore` |
| `.harnex/config.yml` | **project** | no | your answers, `.harnex.yml`'s own ten-key local cousin — a new path, not a rename; `.harnex.yml` itself is untouched |
| `.harnex/rules.md`, `.harnex/manifest.json`, `.harnex/state/` | harness / runtime | no | the whole of `.harnex/` ignores itself, not only `state/` |
| `.claude/settings.local.json` | **local, by entry** | no | the permission floor's entries, Claude Code's own personal/gitignored settings layer |
| an OpenSpec store | — | no | registered on the machine (`openspec store setup`), not a directory inside the project at all; `propose`/`apply`/`verify`/`ship` resolve `--store` from `.harnex/config.yml`'s `store_id` (`explore`/`review` never touch `openspec` at all) |
| `~/.claude/settings.json` | **you** | — | one global, one-time, explicit-yes offer so `CLAUDE.local.md` never silently stops `AGENTS.md` from loading; not a project path at all |

`git status` is clean immediately after setup and stays clean through every later harness
operation on that project. No promotion path from `local` to `shared` exists yet.

**Entry files belong to the project.** `AGENTS.md` and `CLAUDE.md` are the files each
tool opens first, and projects already have them. The harness needs exactly one thing
from each: a **pointer line** — in `AGENTS.md` a sentence telling Codex to read
`.harnex/rules.md` (Codex has no import syntax), in `CLAUDE.md` the two `@` imports. When
setup creates the file, the line is there. When the file exists, setup checks for the
line and, if it is missing, shows you the exact line and where it would go, and inserts it
only on your explicit yes. If you decline, setup finishes and says what does not work —
"Codex will not read the rules" — and every later setup or update repeats the notice. The
harness never writes a project-owned file without that yes, and never rewrites one.

**`.claude/settings.json` is the one shared file.** Claude Code reads a project's
permissions from that single file, and a plugin cannot ship permission rules (only hooks,
agents, skills, commands and MCP), so the permission floor of §9 has to live there. It is
merged as JSON by entry, never as text: setup adds the floor's entries to
`permissions.deny` and `permissions.ask`, records exactly those entries in the manifest,
and leaves every other entry alone. A project entry that covers what the floor asks about is
**reported, not resolved and not a conflict**: the host resolves deny, then ask, then
allow, and no allow carves an exception out of either, so the floor still applies and the
person is simply told their entry is inert for those commands
([the decision note](decisions/2026-09-25-the-permission-floor-in-the-hosts-syntax.md)).
This is the only exception to ownership by file, and it is ownership by entry, recorded,
not a merge by guesswork.

**Setup plans first, writes after your yes.** Setup never writes while it is still
learning what is there:

1. **Survey** every target path and classify it: absent; harness-generated (its hash is
   in the manifest); project-owned and present; or **foreign** — a harness-owned path that
   exists but that the harness did not write.
2. **Plan**: print, per path, create / keep / insert pointer line (asks) / merge entries /
   adopt / conflict. A foreign `.harnex/rules.md`, a settings file that cannot be read as
   JSON, or a harness-owned path present with no record accounting for it is a conflict.
3. **Stop on any conflict** before writing anything. You resolve it — move the file, or
   tell setup to adopt it, which replaces it after showing you the diff — and run setup
   again.
4. **Write**: each file to a temporary sibling, then an atomic rename; the manifest last.

This is also **adoption**: an existing project with its own `AGENTS.md`, `CLAUDE.md`,
settings and OpenSpec config goes through the same four steps, and ends with its own files
untouched except for lines you approved.

Update, whenever harnex changes: `claude plugin update harnex` refreshes the behaviour;
`/harnex:update` re-renders the harness-owned paths and entries. Its contract:

- **Reads** `.harnex.yml` (its input) and `.harnex/manifest.json`; reads the entry files
  only to report a missing pointer line. **Writes** only harness-owned paths and
  harness-owned entries. Never writes a project-owned file.
- A harness-owned file is overwritten only if its current hash matches the manifest; if
  you edited it, update stops and names the file.
- **Interrupted runs recover by content.** Update surveys and stops on conflict before
  writing, writes each file atomically, and writes the manifest last. Run it again after
  an interruption: a file whose hash matches either the manifest or the new rendering is
  safe — already old or already new — and anything else is an edit and stops it.
- **A fresh clone works**, because the manifest is committed: every committed path is
  recognised unchanged and nothing is asked. The one path a clone is missing is the runtime
  state location, which is deliberately not committed, so that is the one thing it restores.
  A project with harness files but no manifest — deleted, or harnessed by hand — is not guessed at: update refuses and
  points to setup, whose adoption shows each difference and asks.

**Outside a harnessed project the plugin does nothing.** The plugin is installed per
machine, so its hooks run in every project you open. Every harnex hook first looks for
`.harnex.yml` at the project root and exits silently, allowing, when there is none; and
each hook acts only when the project enabled its set or feature. A machine with harnex
installed behaves exactly as before in every project that has not run setup.

Codex reads the project's `AGENTS.md` and, through its pointer line, the rules file.

Why a plugin, after the first plan rejected marketplaces: that rejection assumed Codex
CLI as a second consumer. With Codex reached only through its own plugin, the Claude
plugin mechanism delivers hooks, agents, skills, commands and MCP in one versioned unit,
updates with one command, and leaves the project with a handful of small files. Copier was
evaluated and dropped: it has no notion of ownership, cannot merge `settings.json`, and
cannot adopt an existing project — the three things the contract above does.

## 7. Rules

A rule is a short statement of how work is done that every agent must follow. In harnex a
rule is one file under `plugin/context/rules/<set>/<rule>.md` with frontmatter `id`,
`set`, `applies_to` (always, or a profile), `enforced_by` (none, guard, hook, check,
decision). The body is the rule as an agent reads it, with its reason, in a few lines:
its first line is a level-one heading that *is* the rule, stated as one sentence, and a
rule whose `enforced_by` is not `none` carries an `**Enforced by:**` line naming the
component that enforces it — which is what lets a check walk from a rule to its code and
back. The format is stated in `plugin/context/rules/README.md`.

Sets in v0.1, all selectable in `setup` and recorded in `.harnex.yml`:

- `git`: branch per change, conventional commit messages, **no AI author or co-author
  lines ever**, commits only in `ship`.
- `code`: the check command runs before any claim of done, tests beside what they test,
  no scope beyond the task.
- `sdd`: the change's artifacts are the brief, re-read from disk; `proposal.md` is the
  scope; never tick `tasks.md` from a builder.
- `safety`: what always asks you (destructive commands, pushes, credentials, deletions).
- `canary`: every answer ends with the canary word. Its check is active only when this set
  is chosen; a project without the set, or without `.harnex.yml`, never sees the hook act.
- `language`: everything committed in English.

`setup` renders the chosen sets into `.harnex/rules.md`. A rule with `enforced_by: guard`
also feeds the guard's pattern lists and the permission floor; one with `enforced_by: hook`
has a hook in the plugin. `enforced_by` names the mechanism, and the rule's body says
what kind of guarantee it is — prevention or detection, per §4 — rather than claiming
more than the mechanism does. Project-specific rules stay in `AGENTS.md`; a rule is promoted into harnex only
when it has no project noun in it.

## 8. The decision model

One interface, in `plugin/scripts/decide.py`:

```
decide(question_id, state) -> Decision(choice | score | probability, probabilities, confidence, backend)
```

Backends: `jev` (TypeSafe Jev through OpenRouter's decisions endpoint, a small client on
the standard library's `urllib` with a timeout and retries — the vendor SDK cannot target
OpenRouter, and decision 15 rules out a third-party HTTP library) and `mock` (prints the
question and asks you, so the harness is complete without any key). Adding a backend is
one class. The backend is chosen in `.harnex.yml`.

Questions live as YAML in `plugin/orchestration/decisions/` and `plugin/control/guard/`,
each with its type, literal criteria, the state it receives, **its own decision rule on
the returned probabilities**, and its behaviour when the backend is `mock`:

| Question | Type | State (kept small) | Rule |
|---|---|---|---|
| `phase.route` | Choice: codex / claude-<model> / human | phase, task or brief summary, profiles | highest option if its probability ≥ 0.70, else ask you; binding for `verify`, advice for main-session phases (§3) |
| `task.route` | Choice: codex / claude / human | one task's text and file list | same |
| `task.scope` | Noul | task text, changed paths | asked only when the task declares no paths (§10); ≥ 0.85 in scope; ≤ 0.35 out of scope; between → ask you |
| `guard.risk` | Score: read_only / reversible / destructive | command, cwd, branch, is_worktree | P(destructive) ≥ 0.30 → ask; P(read_only) ≥ 0.85 → allow; else ask |

What is deliberately **not** a question: whether the check passed (an exit code), whether
the changed paths sit inside the task's declared paths (a set comparison), whether
the plan is complete (OpenSpec validation plus the verifier's review), whether a change is
ready (findings carry severities; any blocking finding blocks). Never send the model's own
description of its command: self-arguing text moves the answer.

Every decision is appended to `.harnex/state/journal.jsonl` with `question`,
`state_sha256`, `probabilities`, `confidence`, `decision`, `rule_applied`, `backend` and a
`resolution` field filled when you override or when the outcome is known, so thresholds
can be tuned on evidence. Screen line format is fixed: `Decision: <phase> → <tool> · <model> · <confidence>`.

**Routing happens only at subagent-spawn granularity, never mid-conversation.** `jev-router`
(a public proxy that routes Claude Code and Codex by intercepting an already-running
session and rewriting which model answers) shows why the alternative is worth avoiding: its
own benchmark finds routing *degrades* feature tasks in Claude Code (+16–61% input tokens,
up to +83% time), because once extended thinking is on, its proxy can only `hint` a cheaper
tool choice rather than force it — the model reads the hint, may ignore it, and the context
cost is spent either way. Codex fares better there because its protocol allows a forced
choice. `phase.route` and `task.route` never face this: they pick a model *before* a fresh
Claude subagent or a Codex job starts, so there is nothing running to hint at and nothing to
ignore. This is a deliberate consequence of §4's role boundaries, not an oversight — worth
keeping in mind if a later phase is ever tempted to route an in-flight session instead of a
fresh one.

**Three implementation notes for `decide.py` and the question YAML**, from how Jev's own
CLI and gateway are used in practice elsewhere:
- **Never key `state` by position.** Referencing items in an array by index (`candidates[i]`)
  degrades badly on a Noul/Choice/Score call over a long list (one measurement: 27% wrong
  answers at 150 items); keying the object (`candidates.k137`) or embedding the item directly
  in the question text measured 0% wrong up to 320 items. Any question whose `state` carries
  a list — `phase.route`'s file list, a future ranking of tasks — keys or embeds, never
  indexes.
- **Batch independent questions in one call where `apply` asks several at once.** Jev answers
  several typed questions (Noul, Choice, Score) in parallel within a single ~250 ms request
  at no extra latency. C3's loop asks `task.route` and, for paths-less tasks, `task.scope`
  once per task; when a change has several such tasks queued at once, one batched call beats
  one call per task. Worth a `decide_many()` alongside `decide()` when C3 is designed, not
  before.
- **Don't spend a decision call re-routing a task mid-retry just to save tokens.** A
  cross-project routing rule worth carrying even though harnex doesn't proxy live sessions:
  switching backend or model mid-task can cost more than it saves once meaningful context or
  prompt-cache is already built up for that task. §10's "a retry is a fix, not a re-check"
  already keeps the same builder for a retry; this is the reason that rule should hold even
  if a cheaper option would score well on `task.route` at retry time.

## 9. The shell guard and the permission floor

Two layers, because one hook cannot promise what it cannot deliver.

**The guard** is a PreToolUse hook on Bash in the plugin, `guard.py`, with the decision
table in diagram 05: parse the command; every part in the read-only allowlist → allow
silently; a deny pattern → deny with reason; an ask pattern → ask you; the residue →
`guard.risk` with a 3-second timeout and one retry. Deny never comes from the model alone.
Rules with `enforced_by: guard` feed the three lists. When a tool call comes from a
subagent, the hook input carries its `agent_type`, which lets the guard apply a role's
stricter list — the builder's, for instance — without touching the main session.

**The guard's failures are of two kinds, and only one is in its hands.**

- *Failures it catches*: backend unreachable, timeout, missing key, `mock` backend,
  unparseable command, any exception inside the script. The script answers **ask**, never
  allow. This is guaranteed by the script and tested.
- *Failures of the hook itself*: the interpreter is missing, the script does not start,
  it hangs past the hook's timeout, or it prints malformed output. Claude Code then treats
  the hook as a non-blocking error and **continues with its normal permission flow**; there
  is no fail-closed setting (verified against the Claude Code docs for 2.1.267). The
  script cannot answer, so the guarantee has to come from elsewhere.

**The permission floor** is that elsewhere. Setup writes the guard's deny and ask patterns,
in Claude Code's own permission syntax, into `.claude/settings.json` (§6): `deny` for what
the guard denies, `ask` for what it asks about, and deny rules on reading secret files. If
the guard is down, Claude Code still refuses or asks for everything on the floor, and any
command not already allowed goes through the session's permission mode, which asks. The
floor is coarser than the guard, but not for the reason this plan first assumed: deny and ask
rules **do** see every subcommand of a compound command, including inside a subshell or a
command substitution, and they match past a leading assignment. What escapes them is a program
named by an absolute path the floor does not list, a shell or environment runner that executes
its argument, `find` with `-exec` or `-delete`, an exec wrapper — and, above all, anything that
depends on the task, since a deletion inside the paths a task declares is ordinary work. Those
gaps are recorded in `floor.json` as `guard_only`, each with its reason. Setup reports any
project `allow` entry that covers a floor entry, and says that the floor still applies.

What is promised, then: **the guard never allows on its own error; when the hook itself
fails, protection falls to the floor and the permission mode, never to nothing** — unless
you run in a mode that bypasses permissions, which no harness can defend against and which
setup warns about. Two things keep hook failures rare: the script is standard library only
and started with a plain interpreter, and the hook's declared timeout is set well above the
script's own budget (3 s plus one retry), so Claude Code never has to kill it for being
slow.

Codex runs under its own sandbox through the Codex plugin, which the S1 spike
characterises. A Codex-side hook with the same script is a later feature, not v0.1.

## 10. The build loop

`apply` runs a change's tasks in order (`tasks.md` is linear in v0.1). Its contract holds
with you watching, and does not assume you are:

- **Who accepts and ticks.** Only the `apply` command, in the main session, ticks
  `tasks.md`. It accepts a task when all of these hold, each a fact rather than a
  judgement: the builder reported done; the check command exited 0; the changed paths sit
  inside the paths the task declares (or, for a task that declares none, `task.scope`
  says in scope); the protected paths (`openspec/`, `.harnex/`) are unchanged; `HEAD` and
  the refs did not move. Anything else is not accepted: it goes to a fix or to you.
- **Evidence is bound to the tree it describes.** Before the check runs, `apply` takes a
  fingerprint of the working tree — the hash of the diff against the change's base plus
  the untracked files — and takes it again after. Evidence records the fingerprint, the
  command, the exit code and the tail of its output. A task is accepted only if the
  fingerprint at acceptance equals the one the check ran on; if the tree moved, the check
  runs again.
- **A retry is a fix, not a re-check.** When the check fails, the same builder gets the
  task, the check's output and the current diff, and makes one fix; the check runs again.
  A second failure, or a scope or protected-path violation, escalates to the architect —
  rewrite the task or the design — and to you.
- **Interrupted work is resumed from recorded state, never redone blind.** Every
  transition — delegated, returned, checked, accepted, fixing, escalated — is written to
  `.harnex/state/apply/<change>.json`, atomically, before the next step starts. Running
  `apply` again reads it. A task left *delegated* is looked up in the Codex plugin's job
  status first; if its outcome cannot be recovered, `apply` shows you the diff since the
  task's base fingerprint and asks: keep it and check it, discard it (a destructive
  action, so it asks), or delegate again. It never re-delegates onto a dirty tree without
  asking. Two things [S1](decisions/2026-09-27-s1-delegating-to-codex.md) found narrow
  what "looked up first" can promise: a job's own record only ever says `running` or
  `done` — nothing checks whether its process is still alive — so `apply` needs its own
  staleness rule (no progress for some interval) before trusting `running`; and a job
  survives only past a session that ends **uncleanly**, since a normal session end kills
  its own background jobs outright. Recovery-by-lookup is therefore for a crash, not for
  quitting normally mid-task — a normal exit leaves nothing to look up.
- **Branch or worktree isolation is harnex's job, not Codex's.** `/codex:rescue` never
  creates one and has no option to target one; it runs wherever its `--cwd` points
  ([S1](decisions/2026-09-27-s1-delegating-to-codex.md)). Before delegating, `apply`
  checks out the change's branch (or a worktree of it) itself and passes that path.

## 11. Roadmap — one capability per phase

Each phase is one OpenSpec change with three parts: what it delivers, **how you try it**
by hand, and the automated tests that need no credentials. Phases are sliced by
capability so that every one of them leaves something you can use. A phase that would
deliver several independent capabilities is split into lettered changes, each one usable
on its own and landing in order; C1 is split that way. A **spike** — a timeboxed
experiment recorded in `docs/decisions/`, with no code under `plugin/` — runs before the
first phase whose design it could invalidate, not inside the phase that finally uses it.

### C1 · install and setup — four changes

C1 delivers the whole installation path, which is four independent capabilities: a plugin
that installs, rules that render, a setup that writes a project, and a canary that
enforces itself. Each is its own OpenSpec change, in this order.

#### C1a · an installable plugin — **delivered**, change `bootstrap-installable-plugin`
- **Delivers:** the catalogue `.claude-plugin/marketplace.json` with its single entry; `plugin/.claude-plugin/plugin.json` (name, version `0.1.0`); the five pillar directories, each with a `README.md` stating what belongs in it, what does not and which change fills it; `docs/smoke.md` with the format every later phase appends its manual check to; `tests/` and `pytest.ini`, the repository's own checks.
- **You try it:** `claude plugin marketplace add ./` from your checkout, `claude plugin install harnex@harnex`, then `claude plugin details harnex` (or `/plugin` in a session): harnex `0.1.0` is listed with **0 skills, 0 agents, 0 hooks, 0 MCP servers** and `~0 tok` added to every session. Nothing else happens yet, and that is the point. Full steps in [smoke.md](smoke.md).
- **Tests:** `uv run --with pytest pytest` — a structural test asserting every directory under `plugin/` is either a pillar or one of the directories Claude Code reads and that every pillar states what it holds; the private-name check in two halves, the committed shapes and a personal list found through `HARNEX_DENYLIST`, which skips itself and says so when the variable is unset; the manifest checks, which shell out to `claude plugin validate` for both manifests and skip when the CLI is absent.
- **Exit:** met. The plugin installs from a local checkout and validates strict, contributing nothing.
- **What it taught us**, verified against Claude Code `2.1.267`:
  - A plugin with **no components at all** passes `claude plugin validate --strict`; emptiness is not a warning. This is what makes an empty vehicle a change of its own.
  - `--strict` treats warnings as errors, and two fields are easy to lose: without `author` in `plugin.json` and `metadata.description` in `marketplace.json`, strict fails.
  - `claude plugin marketplace add .` is rejected — the source must be `owner/repo`, a URL, or a `./path`.

#### C1b · rule sets and their rendering — **delivered**, change `rule-sets-and-rendering`
- **Delivers:** the rule file format (frontmatter `id`, `set`, `applies_to`, `enforced_by`, and a body whose first line is the rule stated as one sentence) and the six sets of §7 — `git`, `code`, `sdd`, `safety`, `canary`, `language`, sixteen rules — one file per rule under `plugin/context/rules/<set>/`, with the format itself stated in `plugin/context/rules/README.md`; `plugin/scripts/render_rules.py`, which turns a list of sets and the project's profiles into `.harnex/rules.md` deterministically. Pillar 1, with the renderer as its only script.
- **You try it:** `uv run plugin/scripts/render_rules.py --sets git,code --out -` prints the rules file those two sets produce; add `safety` and the file grows by exactly that section, with one header line changed and nothing else moved. Full steps in [smoke.md](smoke.md).
- **Tests:** the format over every rule file, with fourteen seeded faults each proving the check catches it; the set checks; determinism against a permuted and a repeated set list; one committed snapshot of every set rendered, plus the subset property that a set renders the same beside any other; the private-names denylist over the rendered output as well as the tree.
- **Exit:** met. Every rule is stated exactly once, and the same set list always renders the same file, byte for byte.
- **What it taught us:**
  - The renderer needs **no dependency at all**. Four flat `key: value` fields are parsed by fifteen lines that refuse anything else, and refusing *is* the schema check. That keeps `uv run` instant, which matters once `C1d`'s hook has three seconds to live — and it is why the frontmatter is YAML-shaped rather than YAML.
  - Determinism is not "the same run twice" but "the same choice, from any direction". Alphabetical sets, alphabetical rules, no timestamp and no version stamp: anything else would make `.harnex/rules.md` look edited to `update` every time the plugin is released, and a harness-owned file that changes for reasons the project did not choose is one `update` can only refuse to touch.
  - One snapshot plus a property beats several snapshots. "A set renders the same beside any other" holds for every combination, not for the two someone recorded, and it is the property `setup` actually relies on when it offers sets freely.
  - The redundancy in the format is the check: `id` repeats the file name and `set` repeats the directory, so a rule moved or copied without care is caught before the duplicate statement reaches a project.

#### C1c · setup writes a project, new or existing — **delivered**, change `setup-writes-a-project`
- **Delivers:** `/harnex:setup` — one skill, `plugin/skills/setup/`, and `plugin/scripts/setup.py` with three verbs (`choices`, `plan`, `write`); the templates for `AGENTS.md`, `CLAUDE.md`, `.harnex.yml` and the OpenSpec config under `plugin/context/templates/`, the two pointer lines being files of their own that state where the line goes, what proves it is there and what is lost without it; the questions setup asks, offering only what the harness holds; the survey–plan–write sequence and adoption of §6, calling C1b's renderer for `.harnex/rules.md`; the permission floor (`plugin/control/floor.json`, pillar 4), every entry naming the rule it comes from, and its entry-level merge into `.claude/settings.json`; the committed record at `.harnex/manifest.json` and the self-ignoring `.harnex/state/`; the plan's own informational notice, printed when `decision_model` is `jev`, naming the project-root `.env` file, the `OPENROUTER_API_KEY=` line it must declare, and that it should stay out of version control — setup never reads, writes or gitignores `.env` itself, the same principle `.harnex/state/`'s own self-ignoring already established. The whole update contract of §6 is fixed here — record format, conflict rules, atomic writes, recovery by content — even though the `update` command arrives in C6. Pillar 4's README is restated in the terms of §9, and the five rules the guard enforces now name both layers and say what each one gives.
- **You try it:** in an empty scratch project, run `/harnex:setup`, read the plan it prints, say yes, read the files. Run it again: "nothing to do", and not a byte changes. Then take an existing project with its own `AGENTS.md`, `CLAUDE.md` and `.claude/settings.json`: it offers the pointer lines one at a time, merges the floor without touching your entries, and everything you declined is byte-identical afterwards. Clone the scratch project fresh: every committed path is unchanged and only the uncommitted state directory is restored. Full steps in [smoke.md](smoke.md).
- **Tests:** the survey's classes, the plan, the writes and the floor — snapshots of a whole project for two set choices; a second run byte-identical to the first, the record included; fixtures for an existing project, a foreign rules file, an unreadable settings file, and a record missing, unreadable or of an unknown format; a run interrupted before the first write and after each one, re-run to completion, asserting the same tree and no fragment left behind; the floor's coverage rule by rule, its merge, and the overlap notice; the private-name check extended to the templates, the floor, what setup writes and the committed snapshots; one run of the script as a real process, the way the host starts it.
- **Exit:** met. A new project and an existing one are both set up in one command each, a second setup changes nothing, and no project-owned byte changes without an explicit yes.
- **What it taught us**, verified against Claude Code `2.1.269`:
  - **A command in front of a skill is two components for one capability.** The host lists both in one inventory (`Skills (2)`), each paying its own always-on description, and a skill named `setup` is already invoked as `/harnex:setup`. The thin command bought the name it already had; dropping it left one component at ~81 always-on tokens.
  - **The host's rule order turns one of this plan's conflicts into a notice.** Deny, then ask, then allow, first match wins, and no allow carves an exception: a project `allow` cannot undercut the floor. §6 and §9 disagreed about this; the host settled it, and refusing to write over it would have been protection theatre.
  - **The floor sees more than assumed and less than hoped.** Deny and ask rules match every subcommand of a compound command; what escapes them is wrappers, absolute paths and anything that depends on the task. The residue is recorded in `floor.json` as `guard_only` rather than left implicit.
  - **Recovery by content has to cover entries, not only files.** An interruption after the settings merge and before the record left the harness unable to say which entries were its own. The fix is the rule the files already followed: what is already exactly what would be written is current. The interruption test found it, one write at a time.
  - **"Already harnessed" and "nothing to write" are not the same thing.** A fresh clone lacks the runtime state directory by design, so the honest promise is that nothing committed changes and nothing is asked — not "nothing to do".
  - **A project's permission file cannot be merged as text.** Parsing it, adding entries and writing only when the parsed result differs is what makes a second run byte-identical whatever formatting the project uses. The price is that the first merge reformats the file, which the plan prints before the yes.

#### C1d · the canary check — **delivered**, change `canary-enforces-itself`
- **Delivers:** three recorded Stop/SubagentStop payloads from a real Claude Code 2.1.267 session, sanitised, kept as test fixtures; `plugin/feedback/canary/canary.py` and a `Stop` hook — main session only — in `plugin/hooks/hooks.json`. The hook is inert unless `.harnex.yml` exists and chooses the `canary` set, and reads the word only from `.harnex.yml` — there is no fallback word in the hook. Its warning says the word is missing and that the rules may no longer be in effect, not that the context is lost. The `canary` rule's wording is revised to match (§3), and its enforcer line names the check by path. A new check walks from every hook the plugin declares back to the rule that claims it, the other half of C1b's rule-to-enforcer walk. `setup.py` renders a `## Canary` section into `AGENTS.md`, stating the word, when the set is chosen — found necessary only by trying the check by hand (see below). Pillars 5 and 1, plus pillar 2 for that one addition.
- **You try it:** in the scratch project, ask Claude anything: the answer ends with your word, read from `AGENTS.md`. Ask it to answer without the word on purpose: the hook warns, visible in an interactive session or the desktop app (not in `claude -p`'s plain output — confirm with `--debug-file` instead). Remove `canary` from the sets and ask again: silence. Open a project that never ran setup: silence. Full steps in [smoke.md](smoke.md).
- **Tests:** pytest over the recorded fixtures and cases derived from them in code — word present, in bold/italics/code, missing, mid-answer, in another case, a project word other than the one proposed, `.harnex.yml` absent, set not chosen, set chosen without a word, unreadable, field absent, field empty, malformed stdin — each asserting exit 0 and no block decision; the hook started as a real process with the command `hooks.json` declares, timed against its own budget; the two-way walk between rules and hooks, seeded with both faults it must catch.
- **Exit:** met. The canary is stated once and checked once; it acts only where it was chosen; removing the statement is detected.
- **What it taught us**, verified against Claude Code `2.1.267`:
  - **A rule and a working check are not the same thing as a check the model can pass.** `.harnex/rules.md` is a pure function of the chosen sets, so the rule can only say "the word the project declares" — never the word itself. Nothing else rendered into a fresh project ever stated it: it lived in `.harnex.yml` only, which nothing points a model at. Asked to quote and follow its own rule, the model correctly reported it had no way to know the word. The fix (a `## Canary` line in `AGENTS.md`, from the answer setup already held) touches pillar 2, which the change's own proposal had first declared unchanged — caught only by running the manual steps for real rather than trusting the design.
  - **A subagent's silence is not the same signal as the main session's.** A `general-purpose` subagent, briefed on the project's instructions, ended with the word; a built-in `Explore` subagent, never briefed on them, did not — recorded from the same session, so the only variable was which agent type answered. Hooking `SubagentStop` today would warn on every `Explore` call regardless of anything going wrong, training the person to ignore the signal. Decided and recorded in `docs/decisions/`; reopens with `C2`'s own subagents, whose prompts harnex writes.
  - **A hook's warning does not reach every surface the same way.** The `Stop` hook's `systemMessage` shows in an interactive session's transcript and in the desktop app, but `claude -p`'s plain-text output never prints it — only `--debug-file` does. A manual check written against headless output alone would have called a working hook silent.

### S1 · spike: delegating to Codex — before C2 — **run**, [decision note](decisions/2026-09-27-s1-delegating-to-codex.md)
- **Answers**, recorded in `docs/decisions/`: whether `/codex:rescue` takes a task reliably, on which branch or worktree it works and whether it can be pointed at one; how its job status and result are read back, and what survives an interruption (the recovery contract of §10 depends on it); what its sandbox lets it do to `.git` — commit, move refs — and to paths outside the workspace; what evidence comes back. Timeboxed to a day, run in parallel with C1c or C1d, against a scratch repository.
- **Why now:** C2 prints routing decisions that name Codex, and C3's loop is built on answers the plan currently assumes. If Codex cannot be pointed at the change's branch, or its jobs cannot be recovered, the design of §10 changes before any code depends on it.
- **Exit:** each question has an answer with the transcript that shows it, and §10 and the §4 matrix are corrected where the answers differ from the assumptions. **Met for §3 and §4, still partial for §2**: the original run found every model tried returning `400 invalid_request_error … not supported when using Codex with a ChatGPT account` and traced it to the account, not a stale token or a missing API key — all four answers came from `codex-companion.mjs`'s own source and its fake-fixture tests, not a live transcript. A 2026-09-28 live run corrected that: the restriction is per-model, not account-wide — `gpt-5.6-terra` negotiates successfully end to end (`codex exec` and the real `codex-companion.mjs task` path both work, read-only and `--write`, confirmed against `git status`), while `gpt-5.1-codex-max`, retried in the same session, still 400s. §3's sandbox claim and §4's evidence claim are now confirmed by observation; §2's job-status/interruption behaviour is still from source and the fake-fixture tests only, since the live run was foreground, not `--background`.

### C2 · explore and propose — **delivered**, change `explore-and-propose`
- **Delivers:** `plugin/scripts/decide.py` — `decide(question, state, backend)`, the `mock` and `jev` backends (the latter now falling back to a project-root `.env` for `OPENROUTER_API_KEY` when the environment does not carry it, the environment winning when both do), the decision journal at `.harnex/state/journal.jsonl` — plus the decision-question file format under `plugin/orchestration/decisions/` (YAML-*shaped*, like a rule) and its first question, `phase.route`; the `verifier` role, split as `orchestration/roles/verifier.md` (tool-agnostic) and `agents/verifier.md` (the Claude Code binding, read-only by its `tools` list); `plugin/feedback/scope_check.py`, the detection for the `sdd` rule `the-proposal-is-the-scope` (`enforced_by` now `check`, not `none`); `plugin/orchestration/workflow.md`, naming all five phases and what each may write; and the two skills, `plugin/skills/explore/` and `plugin/skills/propose/`, which drive the `openspec` CLI directly rather than depend on OpenSpec's own assistant skills being installed in the target project.
- **You try it:** `/harnex:explore "an idea"` in the scratch project, then `/harnex:propose`. You see the `Decision (advice):` line first, then the artifacts appear under `openspec/changes/`, then the scope check's report, then the verifier's review. With `mock`, the line says the advice is unavailable and moves on — it never asks you to pick a tool or model for a phase you cannot switch mid-session anyway; with `OPENROUTER_API_KEY` set and `decision_model: jev`, the line comes from Jev. Full steps in [smoke.md](smoke.md).
- **Tests:** the question-file parser and its faults; both backends' request-building and response-handling against the exact shapes read from OpenRouter's own docs; the `jev` backend's retry-once-within-budget behaviour against a stubbed hanging socket, a stubbed 5xx-then-success, a stubbed 4xx, and a missing key; the journal, one line per call; the scope check against a real git repository, including a rename and a path already dirty before the run; agent and skill frontmatter, asserting the verifier's `tools` and that its adapter's body is an exact copy of its role prompt.
- **Exit:** met by construction and by the automated tests; the live end-to-end try (`smoke.md`) needs a fresh Claude Code session, since a session resolves a plugin's skills once at start and this one was built inside the session that will report it — left for the next session to run.
- **What it taught us**, verified against Claude Code `2.1.269` and OpenRouter's own docs (2026-09-28):
  - **A decision that cannot be acted on should not be asked as a question.** §8's contract for `decide.py` — any failure degrades to the same shape as `mock`, and the caller then "asks the person" — is right for a question that binds, like `guard.risk` will be. For `phase.route` inside `explore`/`propose`, which only ever prints advice because the main session's model cannot be switched mid-conversation, asking the person to pick a tool they cannot use would be pure friction. The skills print "unavailable" and move on; nothing about `decide.py`'s own contract changed to make this possible — the distinction lives entirely in what the caller does with an unresolved outcome.
  - **A format described as "YAML" in the plan is YAML-*shaped*, the same call C1b made for rules, for the same reason (decision 15).** The decision-question file has one `---` line, not a rule's two, since there is nothing before the fields to close off — a small format decision worth recording so it is not re-litigated when `C3`/`C4` add `task.scope` and `guard.risk`.
  - **An agent's body cannot import another file.** Fetching Claude Code's own subagent documentation while designing the verifier confirmed there is no `@`-import for a subagent's system prompt, unlike `CLAUDE.md`. The role prompt and its Claude Code adapter are necessarily two files with the same content; a test walks the correspondence exactly the way `C1d` walks rule-to-hook, so the two cannot drift apart unnoticed.
  - **`git status --porcelain` collapses a brand-new directory to one entry.** The scope check's own test caught this: a change's directory, being new and untracked, was reported as `openspec/` rather than each file inside it, which would have hidden every file `propose` writes from the very check meant to watch them. `--untracked-files=all` is now part of both the snapshot and the live status call.
  - **`decide.py`'s own script filename does not match what this change's planning artifacts first called it.** `scope-check.py`, as first written in the proposal and design, would not be importable as a Python module and did not match every other script in the repository (`setup.py`, `canary.py`, `decide.py`); it is `scope_check.py`. Recorded here since the plan text above already uses the corrected name.
  - **The OpenRouter Decisions endpoint's contract was read from its own docs, not exercised live.** `decide.py`'s `jev` backend is built and tested against the exact request and response shapes OpenRouter's documentation shows (§8 already flags `jev` as alpha, §14); a live call, once a working key is available, is this change's one remaining "you try it" step, and any mismatch is a fix to `decide.py`, not to the docs.

### C3 · apply through Codex — **delivered**, change `apply-through-codex`
- **Delivers:** the `builder` role (`orchestration/roles/builder.md`) and its two bindings — `agents/builder.md`, the Claude fallback, and Codex reached through its own plugin — held to the same write and tick boundary; `task.route` (Choice) and `task.scope` (Noul, the format's first non-`choice` type, with a second threshold field `rule_threshold_low`); `decide_many()`, batching every queued task's `task.route` into one call at the start of a run, each task's own text and paths embedded in its own question rather than shared through `state` — a shape the Decisions API's docs actually confirm, unlike per-item state scoping; `plugin/feedback/task_scope_check.py` (the declared-path and protected-path checks, `openspec/` and `.harnex/` always refused whatever a task declares); `plugin/scripts/apply_loop.py` (fingerprinting, run state, acceptance as a conjunction of facts, ticking) and `/harnex:apply`; the two stack profiles (`fastapi`, `react`) moved into `plugin/tools/profiles/`. The `code` rule `no-scope-beyond-the-task` and the `sdd` rule `builders-never-tick-tasks` now name real enforcers (`enforced_by: check` for both, `none` and the vague "decision" wording gone).
- **You try it:** propose a two-task change whose tasks each name a file in backticks, run `/harnex:apply`: every task's routing decision prints before the first builder starts, then per task the check and its evidence, then the tick — never by the builder. Break the check on purpose: one fix attempt, then acceptance or escalation. Interrupt and resume: an already-accepted task is untouched, an in-flight one resumes from its recorded state. Full steps in [smoke.md](smoke.md).
- **Tests:** `noul` question-format and request/response fixtures for all three outcomes (resolved true, resolved false, between the thresholds); `decide_many` against a stubbed multi-question response, a stubbed hang, and `mock`; the declared-path and protected-path checks against synthetic and real `git` snapshots, including an already-dirty tree; the tree fingerprint against a real repository (identical trees, a one-byte change, an untracked file, a reverted edit); the acceptance conjunction refused by each single failing fact in turn; the resume classification (`accepted` → skipped, `delegated` → job lookup, `checked`/`returned` → resumed, otherwise fresh) for every recorded status; agent/skill frontmatter, including the builder role-to-binding correspondence.
- **Exit:** met by construction and by the automated tests, plus a hand-run walkthrough of every deterministic CLI verb against a real scratch repository (acting as the builder by hand) that landed both tasks, ticked, with evidence, on a clean tree, and correctly refused a protected-path write on a clean before-snapshot. **Not yet run:** `/harnex:apply` itself through a live session — like `C2`'s skills, it needs a fresh session after this version installs. The live Codex call S1 owed is no longer blocked: a 2026-09-28 run confirmed the Codex branch works end to end with `gpt-5.6-terra` ([S1](decisions/2026-09-27-s1-delegating-to-codex.md)'s update) — but `/harnex:apply` itself has not yet been run through it, and the account still 400s on every other model tried, so the loop's own config needs to name `gpt-5.6-terra` explicitly, rather than rely on the account's default, before this branch can be relied on. Same as `C2` left `jev`'s first live call as its own remaining step.
- **What it taught us**, verified against Claude Code 2.1.269, Python 3.13 through `uv`, and OpenRouter's `jev-tutorial` docs (2026-09-28, for the `noul` request/response shape — fetched while designing this change, since `C2`'s own research never needed it):
  - **`task.route` and `task.scope` cannot be batched together for one task.** The first proposal draft asked `decide_many` to combine them, sharing one state; a re-read of the loop's own order of operations caught that `task.scope`'s state (`changed_paths`) does not exist until after the builder it is judging has already run — the two questions are never simultaneously askable. `decide_many` batches `task.route` across every *queued task* instead, since every task's own text and paths are already known from `tasks.md` before any builder starts; `task.scope` stays a single call per paths-less task, after that task's own builder has written.
  - **A declared path is read from the task's own prose, not a new field.** Every task in this repository's own `tasks.md` files already names its target files in backticks; a task's declared paths are exactly the backtick spans that contain a `/` and are not a URL. No new authoring convention, and no change to the `tasks.md` template `C2` already fixed.
  - **The one-fix-attempt limit needs its own recorded fact, not the conversation's memory of it.** An interruption during a task's fix attempt would otherwise let a resumed run attempt a second fix, since nothing outside the (now-gone) conversation recorded that the first one had already happened. `apply_loop.py`'s run-state entries carry a `fixed` field the loop sets before handing a builder its one retry, checked on resume the same way every other acceptance fact is.
  - **`/codex:rescue` has no `--cwd` of its own** — S1 reads that flag from the `codex-companion.mjs task` command underneath it, not from the slash command's own surface, which only forwards `--model`, `--effort`, `--resume`/`--fresh`. `apply` therefore checks out the change's branch and ensures every builder call — Codex included — runs with it already checked out, rather than trying to pass a flag the command does not expose.
  - **A shipped skill cannot cite a private planning document.** An early draft of `/harnex:apply`'s own body linked to `docs/decisions/2026-09-27-s1-delegating-to-codex.md` — real in this checkout, absent from every installed copy of the plugin, since only `plugin/` ships. The facts S1 established are stated in the skill's own prose instead; the citation stays in this plan and in the change's own `design.md`, which are never installed.

### C4 · shell guard — **delivered**, change `shell-guard`
- **Delivers:** `plugin/control/guard/guard.py` (splitting via `shlex`, allow/deny/ask matching, per-role additions, the `guard.risk` residue call, the guard's own journal, an internal-error path distinct from a backend failure, and the `PreToolUse` hook's `main()`); `plugin/control/guard/patterns.yaml`, the single committed pattern source — one entry per rule, an optional `pattern` (present entries are matched, absent ones are pattern-less notes carried through only so the floor stays reproducible), `floor: yes`/`no`; `plugin/control/guard/generate_floor.py`, a maintainer-run script (like `docs/diagrams/build.py`, never called by setup or at runtime) that regenerates `floor.json` from `patterns.yaml`, skipping every role-scoped (`agent_type`) entry, which the floor has no concept of at all; `plugin/control/guard/guard-risk.yaml`, the `score`-typed question; `decide.py`'s new `score` type (§8's third question shape, request-building and per-option-threshold response resolution); the `PreToolUse` entry in `plugin/hooks/hooks.json`; a builder-only `deny` addition on `openspec/`/`.harnex/` writes, proving a role's list can escalate past the default's own `ask`; the five `enforced_by: guard` rule files corrected to name the guard's real path and to stop overclaiming task/phase awareness the guard was never handed.
- **You try it:** ask Claude to run `ls`: no prompt. Ask it to `rm -rf /tmp/harnex-test`: it asks you, with the reason — v1 carries no deny-severity pattern on the default list, only `ask` (diagram 05's deny box: "none today"). Ask it to `git push origin main`: it asks you. Unset the API key, set `decision_model: jev`, and ask something ambiguous (a `$(...)` substitution): it asks you and names the missing key. Then break the hook — rename the script — and ask for `git push` again: the hook fails to start and the floor, merged into `.claude/settings.json` by the same `patterns.yaml`, still asks. Full transcript: `openspec/changes/shell-guard/smoke.md`.
- **Tests:** pytest over recorded hook stdin payloads for each row of the decision table, including the internal-error path; the hook run as a real subprocess: backend stubbed to hang, script crashing before `main()`, interpreter missing, malformed patterns; floor and pattern lists compared entry by entry, both ways, including that a role-scoped entry never leaks into the floor.
- **Exit:** met. The table in diagram 05 holds for every fixture, with the backend on and off; for every way the hook itself can fail, the floor covers every ask pattern the guard's default list also covers (no deny-severity pattern exists on either side yet — see Non-Goals in the change's own `design.md`).
- **What it taught us**, from a real `apply` run against Codex (`gpt-5.6-terra`, confirmed live per S1's 2026-09-28 update) plus direct verification of every task:
  - **A role's own list needs severity-ranking, not list order, to actually restrict anything.** The first design of D5 ("default list first, then role additions, first match wins") meant a role's `deny` addition could never override a command the default list already matched as `ask` — exactly the case task 5.1 needed (a builder-only deny on `openspec/`/`.harnex/` writes, where `rm *` already matches the default `deletions-ask`). Caught by Codex itself refusing to fake the test rather than build against a mechanism it found couldn't produce the required outcome; fixed by resolving deny-vs-ask by severity across both lists, order-independent, keeping the allowlist check as its own first step.
  - **A generated artifact's generator needs to know what its own target format cannot express, not just what the source format holds.** `generate_floor.py`, extended for role-scoped entries without adjustment, would have written `agent_type`-keyed patterns into `floor.json`'s `guard_only` section — a format the floor's own host-native permission syntax has no way to represent a subagent role in at all. The regeneration test (task 1.3) would have caught this at the next run, not before.
  - **Writing real rule content exposes an over-claim writing it "ahead of the mechanism" (C1c) can't rule out.** Two of the five guard-enforced rules — `deletions-ask` and `commits-only-when-shipping` — claimed the guard "can tell a deletion inside the task's declared paths" and "can tell the shipping phase from any other." `guard.py`'s own signature never carries a task's declared paths or a phase; both claims were corrected to say what the guard actually receives (an ordinary ask, uniformly, with the person's own answer — not the script's knowledge — doing the telling).
  - **The host's own glob semantics need a trailing character.** `Bash(git push *)` does not match bare `git push` (no arguments) — the same prefix-glob behavior the floor's own committed patterns already have. A bare push still asks, via `guard.risk`'s fallback rather than the deterministic pattern; nothing allows silently, but the reason differs by path (`smoke.md`, step 3).
  - **`claude plugin update` is silently a no-op across an unversioned plugin.** Discovered live, mid-session: the marketplace clone updated past C3's own merge, but `claude plugin update harnex@harnex` reported "already at the latest version (0.1.0)" and left the cached plugin's `skills/` directory stale — because `plugin.json`'s version never bumped across C1–C3. Only `uninstall` + `install` rebuilt the cache. Real versioning is C6's own job; this is recorded here as the concrete evidence for why.
  - **A protected-path check that diffs git-status lines has a blind spot the moment its own subject starts dirty.** `openspec/changes/shell-guard/design.md` was corrected mid-`apply` (by the builder, at the orchestrator's explicit direction) without `check_protected` ever flagging it — because the file was already untracked before `apply`'s own run began, so its status line never changed between the before/after snapshots the check diffs. The gap is in this session's own practice (never committing a change's planning artifacts before starting `apply` on it), not in the check's logic against a normally-committed tree; worth carrying forward as a reason to commit `propose`'s output before `apply` runs against it.
  - **`decide.py`'s `score` request/response shapes, built against OpenRouter's docs alone, were wrong the moment a live key existed.** A live call (2026-10-01, change `jev-criteria-array`) returned HTTP 400 for every `score` question — the live API requires `criteria` as an array of plain option names, not the object shape `choice`/`noul` both accept and `score` was built to share; the response then keys `probabilities` by stringified index with a separate `legend`, not by option name, and the probabilities sum to 1 rather than being independent, contradicting the original spec text. Found by diagnosing why `guard.risk` (the only `score` question in the repository) never resolved, making the shell guard ask about nearly every command regardless of `jev` being configured — `C4`'s own exit note already flagged the request side as never exercised live; the response side and the independence claim were not caught until this change.
  - **`guard.py` never read `.harnex.yml`, so the `safety` set it is meant to gate could not be turned off.** Found while diagnosing the same symptom: `canary.py` already implements "inert without `.harnex.yml` or without the chosen set" for its own set (decision 19), but the guard had no equivalent — the default list ran unconditionally regardless of a project's own choice, or even in a project that never ran `/harnex:setup` at all. Fixed in the same change, gating only the default list (`classify_segments`'s own `default_patterns`, not role-scoped additions like `builder-never-touches-protected-paths`, which are not a `safety` concern) on a `safety_active` flag the hook computes once per call from `.harnex.yml`, mirroring `canary.py`'s own fail-safe: a missing or non-choosing `.harnex.yml` goes inert, an unreadable or malformed one stays active (the guard's "never allow on its own error" rule, applied to a new failure mode this change introduced).

### C5 · verify and ship — **delivered**, change `verify-and-ship`
- **Delivers:** a fourth role, `reviewer` (`orchestration/roles/reviewer.md`, `agents/reviewer.md`), read-only and always started on a fixed model (`opus`), independent of who or what built the code under review — this change reopens decision 4 (§12) rather than routing a second opinion through Codex's own `/codex:review`, after the verifier itself caught a real bug in an earlier draft that tried to compute the reviewer's binding from who built the code (design.md D4); `/harnex:review`, a non-blocking, independent command runnable at any point a diff exists, never required by `verify` or `ship`; the verifier extended to a `/harnex:verify` mode — reads a diff and a check-and-facts file from disk rather than running either itself, reports where the diff fails a delta spec, and carries a `blocking`/`advisory` severity on every finding; `plugin/scripts/verify_checks.py`, which runs the project's `check_command` (and, for a UI profile, a stubbed Playwright step) and writes the facts, with an internal-error path distinct from a failing check command (a stderr sentinel, since both cases can share an exit code); `plugin/scripts/ship_gate.py`, which reads the verifier's own stable review record and refuses `ship` with a named reason (no run, a stale fingerprint, or a blocking finding) or passes non-blocking findings through; `/harnex:ship`, the only phase that may run `git commit`, and only after the person's explicit yes, then pushes, opens a pull request via `gh`, and archives the change with its delta specs synced into `openspec/specs/`.
- **You try it:** finish a change through `/harnex:apply`, then `/harnex:review` (shows code-quality findings, never blocks anything), `/harnex:verify` (runs the check command and, for a UI profile, Playwright; shows every finding with its severity), then `/harnex:ship` — it refuses if `verify` never ran or the tree moved since, shows any advisory finding, asks once, then commits, pushes, opens the pull request, archives the change, and syncs its specs. Check the resulting commit has no AI author or co-author line. Full steps in `openspec/changes/verify-and-ship/smoke.md`.
- **Tests:** the verifier's two modes and its severity field; the reviewer's tool list (no `Edit`, `Write`, `Bash`) and its correspondence with its own adapter; `verify_checks.py`'s facts, its internal-error path, and its Playwright step (stubbed) for a UI and a non-UI profile; `ship_gate.py`'s four gate outcomes (no run, stale, blocking, go), with a record/check round trip; `setup.py`'s Playwright `.mcp.json` entry, proposed only for a UI profile and only on explicit yes, every other entry left alone.
- **Exit:** met — a real change ran `explore → propose → apply → review → verify → ship` on a scratch project (`smoke.md`): review never affected ship's own decision, verify's severity-carrying findings were shown, ship refused with a named reason before a fresh `verify` run existed and again after the tree was dirtied, then proceeded once a clean run and an explicit yes stood, and the resulting commit carried no AI author or co-author line. The Playwright/UI path itself is exercised separately, by the person, against a real UI-profile project (proposal's Non-Goals).
- **What it taught us**, from a real hand-run walkthrough on a scratch project — `review`, `verify`, and `ship` are too new to be installed in any live Claude Code session yet, the same bootstrapping gap `C2`'s and `C3`'s own first runs had, so the walkthrough manually simulated them by handing each role's own current prompt to a generic subagent rather than a named subagent type:
  - **A task's declared paths can undershoot what its own prose requires.** `apply`'s own router only reads a task's first line for both routing and its declared-path extraction (`extract_declared_paths` runs over one line, not the full multi-line bullet); several tasks in this very change's own `tasks.md` named a file inline (`apply_loop.py`, a companion test file) in a continuation line, never captured as declared scope, so the mechanical scope check flagged real, task-authorized work as a violation more than once during this change's own `apply` run. Recognized case by case, by judgement, rather than by widening the router (out of scope for this change) — worth fixing in the router itself later.
  - **A check command's own build artifacts must be included in its evidence.** Running `pytest` leaves `__pycache__/` behind; a scratch project with no `.gitignore` sees those directories as untracked. `verify_checks.py` therefore fingerprints after the command completes, so `ship` sees the same tree immediately afterward; the record becomes stale only if the tree changes after verification.
  - **`ship`'s archive step leaves its own writes uncommitted.** `openspec archive` writes the archived copy and the synced spec, but `ship/SKILL.md` does not commit again afterward — a real project carries that as its own follow-up commit, which the walkthrough surfaced but this change did not change, since neither the task's own text nor the delta specs asked for a second commit.
  - **`available_profiles()` only recognised profile directories, not files.** `C3` shipped both stack profiles (`fastapi.md`, `react.md`) as flat files, but `setup.py`'s own discovery only checked `path.is_dir()` — so neither profile was actually choosable since `C3` landed (`validate_answers` refused both). This change's own Playwright feature needed a real, choosable UI profile to test against, which surfaced the gap; fixed by also matching `.md` files. Found by a `/harnex:verify` run reading the diff against `docs/PLAN.md`'s own settled decisions, not named in this change's own `design.md` or `tasks.md` beforehand — recorded here per the same convention `C1c`, `C1d`, and `C4` already established for an incidental discovery.

### C6 · update and release — **code delivered, tag and migration owed**, change `update-and-release`
- **Delivers:** `/harnex:update` (`plugin/skills/update/`, `plugin/scripts/update.py`) implementing the contract C1c fixed — `build_plan` gains a `mode: Literal["setup", "update"]` parameter so update never creates or inserts into a project-owned file, a standard-library-only reader for `.harnex.yml`'s own flat shape, and the two refusal cases (no `.harnex.yml`, or one with no manifest) checked before any plan is built; a `pytest` check that the two plugin manifests' `version` fields agree; two CI workflows, `.github/workflows/check.yml` (every push and pull request, mirroring `AGENTS.md`'s own "Before committing" list) and `.github/workflows/release.yml` (a pushed `vX.Y.Z` tag, re-running the same checks, then asserting the tag matches both manifests before publishing a GitHub release); `docs/releasing.md`, the manual steps a person runs to cut a release, linked from `AGENTS.md`; the README rewritten for a stranger, with a "verified against" table (Claude Code `2.1.285`, the Codex plugin and `codex-cli`, OpenSpec) and `setup`/`update` documented alongside the five commands.
- **You try it:** change a rule in your harnex checkout, bump the version, `claude plugin update harnex`, `/harnex:update` in the project: only `.harnex/rules.md` and the manifest change. Edit `.harnex/rules.md` by hand and update again: it stops and tells you. Kill it halfway and run it again: it completes. Full steps, against a scratch project, in `docs/smoke.md`'s own "update-and-release (C6)" section.
- **Tests:** the reader against this repository's own `.harnex.yml`, a malformed fixture, and a render→read round trip against `setup.py`'s own template; `build_plan`'s update-mode branch, asserted both by fixture and by the general guarantee ("no `Step` with `owner == "project"` ever carries `data is not None`" across a matrix of survey states); both refusal cases; a clean run that rewrites only what a changed rule touches; an interrupted run resumed to completion; a simulated fresh clone restoring only `.harnex/state/.gitignore`; the manifest-version-agreement check.
- **Exit:** met for everything this change's own session could finish. `uv run --with pytest pytest`, both `claude plugin validate --strict` calls and `openspec validate --all` all pass (task 9.1). Two steps in `tasks.md` are deliberately unchecked, left for the owner to do by hand, not part of this change's own session: migrating one real project off the old private marketplace and deregistering it there (8.1/8.2 — `design.md`'s D6 names this as the change's own exit proof, still owed); and tagging `v0.1.0` and confirming the release workflow against the pushed tag (9.2) — nothing on this branch is committed yet, `apply` never commits, and cutting the tag is the owner's own call in `ship`, not `apply`'s. The README and CI exist and validate; "a stranger can install it from the README" holds for the install and setup/update steps, not yet for a tagged release to point at.
- **What it taught us**, from this change's own `apply` run and from re-reading the diff for this plan sync (8.1's migration itself did not run in this session — see Exit):
  - **`apply_loop.py`'s own `route` and `scope` verbs never picked up the `.env` fallback C2 just gave `decide.py`.** `resolve_api_key(project)` (added in "jev falls back to a project-local `.env` for its key", landing just before this change) checks the environment first and a project-root `.env` second; `apply_loop.py`'s `main()` still calls `os.environ.get("OPENROUTER_API_KEY")` directly at both of its call sites (`route`, `scope`), so a project whose key lives only in `.env` — this repository's own, during this change's `apply` run — gets every task's routing decision degraded to "ask" even with a valid key on disk. Real, observed, and out of scope here (it is `apply`'s own mechanics, not `update`/`release`); worth a task of its own, the same way C5 named the router's declared-paths gap without fixing it.
  - **The declared-paths gap C5 already named recurred.** `extract_declared_paths` still reads only a task's first line (`TASK_LINE` matches one line at a time), so a task whose own prose names its test file on a continuation line, or only in its "Verify:" sentence, still declares less than it writes. Several tasks in this change's own `tasks.md` did exactly that — the `.harnex.yml` reader and `update.py` tasks (2.1, 3.1) each declared only the script they added, with `tests/test_update_reader.py` and `tests/test_update_run.py` arriving undeclared; the CI task (6.1) declared only `check.yml` and not the workflow's own best-effort validation steps. Each was recognised as in-scope by judgement, same as C5, not by widening the router — still out of scope for this change.
  - **An apply-time verify step must never be briefed to run a harness-refreshing script against the apply session's own working repository.** Task 4.1's own verify text asked for "a fixture run against this repository's own `.harnex.yml`" producing "nothing to do." Taken literally — `update.py --project .` against this actual checkout — it was not a no-op: this repository's own `.harnex/rules.md` and `.harnex/manifest.json` had drifted out of date against `.harnex.yml`'s current `sets` (the `safety` set is commented out there but was still rendered in), so the run rewrote both. `.harnex/` is a protected path no task's scope can widen into, so that write was reverted and task 4.1 accepted on its own diff alone, the drift left as found. The lesson for any future verify step that would exercise `update.py` for real: point it at a fixture or a copy, never at the real `.harnex/` of the repository the session is running in. (Separately, this repository's own `.harnex/rules.md`/`manifest.json` staleness against `.harnex.yml` is real, pre-existing, and still unfixed — worth the owner running `/harnex:update` for real, outside any change's own scope.)
  - **A task's own "add a test" can already be satisfied by prior work.** Task 5.1 asked for a new test asserting the two manifests' `version` fields agree; `tests/test_manifests.py` has asserted exactly that (`entry["version"] == plugin["version"]`) since `C1a`. No new test was needed — the task's verify criterion was already met, and nothing in the diff for 5.1 changes that file.

### C7 · a personal, local-only setup — **delivered**, change `personal-local-setup`

- **Delivers:** a `visibility` choice (`shared`/`local`, default `shared`) in
  `/harnex:setup`'s questions; under `local`, `AGENTS.md` and `CLAUDE.md` are never
  created or modified, existing or not — `CLAUDE.local.md` is written instead (one
  `@.harnex/rules.md` import), excluded through `.git/info/exclude` rather than the
  project's own ignore file; `.harnex/`'s self-ignoring `.gitignore` widens from
  `state/` to the whole directory, which now also holds `.harnex/config.yml` (a new
  path, `.harnex.yml`'s own ten-key local cousin — decision 11 is not reopened, that
  file keeps its shape); the permission floor goes to `.claude/settings.local.json`
  instead of `.claude/settings.json`; an MCP entry is recommended via
  `claude mcp add --scope local` rather than written into `.mcp.json`; a local OpenSpec
  store is registered (`openspec store setup`, keyed like Claude Code's own auto-memory)
  instead of creating `openspec/` in the project, and `propose`/`apply`/`verify`/`ship`
  resolve `--store`/`--changes-root` from it (`explore` and `review` never do — neither
  touches `openspec` at all, under either visibility); a guided question list including
  which
  builder tools are active, stating plainly that Codex cannot read this project's rules
  under `local` visibility; and a one-time, explicit-yes `~/.claude/settings.json` offer
  (`instructionFiles: claude-md-and-agents-md`) so a project's own `CLAUDE.local.md`
  never silently stops its `AGENTS.md` from loading. `shared` visibility — everything
  C1c through C6 built — is untouched.
- **You try it:** `/harnex:setup`, choose `local`, on an empty scratch project and on one
  with its own committed `AGENTS.md`: `git status` is clean immediately after and after
  every later command. Run setup again: nothing changes, the recorded `store_id` is
  reused. Decline the global settings offer: the notice returns on the next run. Full
  steps in `docs/smoke.md`'s own section for this change.
- **Tests:** every new path's survey/plan/write classes, mirroring `test_setup_survey.py`
  and `test_setup_write.py`'s own style; `git status --porcelain` asserted empty with a
  real git repository, both fresh and over an existing team repo; the global offer's four
  outcomes (missing, already correct, shown-not-written, written-after-yes); the guided
  question list and the Codex disclosure, asserted as skill content the same way the
  reviewer's fixed `opus` model already is; `apply_loop.py`'s `--changes-root`,
  `update.py`'s and `verify_checks.py`'s now-dual-path config reading.
- **Exit:** met for the hand-run walkthrough in `docs/smoke.md` and for everything
  `uv run --with pytest pytest`, both `claude plugin validate --strict` calls and
  `openspec validate --all` check (task 9.1); every one of the change's 17 tasks is
  checked. **Not yet confirmed live**, the same kind of gap C5 and C6 each named for
  their own open items: exactly which file `claude mcp add --scope local` writes its
  entry to (the smoke walkthrough uses no UI profile, so the command never runs there),
  and whether `instructionFiles: claude-md-and-agents-md` keeps a real Claude Code
  session reading `AGENTS.md` alongside `CLAUDE.local.md` end to end, rather than only
  by the file comparison the walkthrough and the tests both rely on.
- **What it taught us**, from this change's own `apply` run:
  - **A task list's own file list can be wrong, and only implementation catches it.**
    Task 5.2, as written, named `plugin/skills/explore/` and `plugin/skills/review/`
    among the skills needing store resolution; neither ever calls `openspec` at all —
    there was nothing to resolve. The task also missed that `apply_loop.py`,
    `scope_check.py` and `verify_checks.py` read or write `openspec/changes/<name>/`
    paths directly, never through the `openspec` CLI, so a `--store` flag could not have
    reached them regardless — they needed their own `--changes-root` parameter (or, for
    `verify_checks.py`, a `.harnex/config.yml`-first read, the same gap `update.py` had).
    Surfaced to the owner mid-run rather than absorbed silently, since it changed the
    task's own scope (`design.md`'s own discipline, §4's "surface the added scope and
    ask").
  - **`scope_check.py` needed no change, for a reason worth recording.** It looked, at
    first, like a fourth script needing store-awareness. It does not: under `local`
    visibility a change's artifacts never appear in the *project's* own `git status` at
    all, so everything `scope_check.py` already treats as "outside the change" is
    correctly outside it — the check's existing logic was already right for a case it
    was never written with in mind.
  - **A machine's own global git configuration can make a test pass for the wrong
    reason.** The first version of the "`git status` is clean" test used
    `--ignored` and asserted the output was empty; it passed, but only because this
    owner's own `~/.config/git/ignore` already excluded `.claude/settings.local.json` —
    a convention this change was supposed to establish, not assume. Caught by checking
    *why* a `.claude/` line was being reported as ignored rather than trusting the green
    test; fixed by adding `.claude/settings.local.json` to `.git/info/exclude` itself,
    not relying on anything outside the project, and re-verified with
    `GIT_CONFIG_GLOBAL=/dev/null`.
  - **A registered OpenSpec store already contains its own ordinary `openspec/`
    subdirectory.** `openspec store setup <id> --path <root>` creates `<root>/openspec/
    changes/`, `<root>/openspec/specs/` and `<root>/openspec/config.yaml` — the same
    shape a project's own `openspec/` already has. `apply_loop.py`'s existing
    `tasks_md_path` needed only a second root to resolve against, not a new path scheme.
  - **Correcting a mid-run discovery in the code and the tests is not the same as
    correcting it everywhere a planning artifact restates it.** The `explore`/`review`
    correction above landed cleanly in `design.md`, the `local-visibility` delta spec,
    and this change's own `tasks.md` — but the first `/harnex:verify` pass still found
    the earlier, broader claim ("every one of the five commands resolves `--store`")
    standing in `proposal.md`'s own Impact section, and a *second* `/harnex:verify` pass,
    on the tree the first pass's fixes produced, found the same claim still standing in
    `proposal.md`'s "What Changes" section and in this very table's own OpenSpec-store
    row. Two independent, fresh-context passes were needed to clear every copy — one
    phrase, repeated across five documents by hand, drifted out of sync with itself
    twice before it was found everywhere. A single search across every artifact for the
    exact phrase being corrected, the moment it is first corrected anywhere, would have
    caught both in one pass. It would have caught a third occurrence too: a *third*
    fresh `/harnex:verify` pass, briefed not to trust either earlier fix, found the same
    self-contradiction standing a third time — in this very "Delivers" bullet above (not
    only in `proposal.md`), and, worse, shipped past planning prose entirely into
    `setup.py`'s own `_plan_local_store` notice (the string actually shown to a person
    running `/harnex:setup`) and into `plugin/context/templates/local-config.yml`'s own
    header comment, the one template that renders into every `local`-visibility
    project's own `.harnex/config.yml`, forever. Neither of those two was planning prose
    reviewed as such — they were source and a shipped template, found only because the
    third pass was told to re-derive everything from the diff rather than lean on what
    the first two passes said they had already fixed. The fix this time was the
    exhaustive one the note above already named: one `grep` for the exact phrase across
    every touched file, not another targeted read.

Later, not scheduled: tuning thresholds from the journal's resolutions; a Codex-side guard
hook; a `security-reviewer` for projects with an attack surface; promoting a `local` setup
to `shared`. Never: an unattended mode.

## 12. Decisions taken

1. Organised by the five pillars; placement by topic; stacks are profiles.
2. Claude Code is the only cockpit. Codex is reached through its official plugin only.
3. Delivery is a Claude Code plugin for behaviour plus a handful of small files per project (§6). Ownership is by file, with a committed hash manifest; the one exception, `.claude/settings.json`, is owned by entry. Copier and the old marketplace are dropped.
4. Four roles: architect, builder, verifier, reviewer. The orchestrator is the human. Commits only in `ship`.
5. The decision model sits behind one interface; `jev` and `mock` backends in v0.1; each question carries its own rule on probabilities; `mock` behaviour is defined for every question.
6. The guard is deterministic first and never allows on its own error; deny never comes from the model alone. Because a hook that crashes or times out cannot answer, a permission floor in `.claude/settings.json` carries the same deny and ask patterns (§9).
7. The canary is a rule plus a `Stop` hook on the **main session's answers only**, active only in a project that chose the `canary` set; setup proposes `Hullaballoo!`, the word lives in `.harnex.yml`, and setup also states it in `AGENTS.md` since a rendered rules file cannot. Its warning is a signal of non-compliance, not a diagnosis of lost context.
8. Everything committed is English, command names included: `explore`, `propose`, `apply`, `verify`, `ship`.
9. Python with `uv` for scripts; minimum frontmatter for agents and skills.
10. No AI author or co-author lines in commits or PRs, in harnex and in every harnessed project (`git` rule set).
11. Names fixed now: `.harnex.yml` keys `project_name`, `profiles`, `sets`, `features`, `canary`, `decision_model`, `check_command`; rules at `.harnex/rules.md`; generation metadata at `.harnex/manifest.json`, committed; runtime state under `.harnex/state/`, not committed; tags `vX.Y.Z` from `v0.1.0`.
12. `docs/` and `openspec/` are public; `.claude/` and `.agents/` at the repo root stay local.
13. Phases are sliced by capability, each with a manual try and automated tests.
14. A phase delivering several independent capabilities is split into lettered changes
    that land in order. C1 is four: `C1a` an installable plugin, `C1b` rule sets and
    their rendering, `C1c` setup writing a project, `C1d` the canary enforcing itself.
15. Harness scripts depend on the standard library only, so that a hook or a setup step
    pays nothing to resolve a dependency before it runs. A format that would need a
    library is the signal to simplify the format, not to take the dependency.
16. A harness-owned generated file is a pure function of the project's choices: no
    timestamp, no version stamp, and no dependence on the order an argument was given.
    Ownership by hash is only workable if the file changes when, and only when, the
    project's choices or the harness's content change.
17. Adoption is part of setup, not a later migration: setup surveys, prints a plan, stops
    on any conflict before writing, and writes only after your yes. `AGENTS.md`,
    `CLAUDE.md` and `openspec/config.yaml` belong to the project; the harness asks for its
    pointer lines and never rewrites them.
18. Every guarantee is named by kind — instruction, prevention or detection — and every
    component states what happens when it fails. v0.1 holds the builder by instruction
    plus deterministic detection before acceptance; prevention is claimed only where a
    mechanism exists (§4).
19. Every harnex hook is inert in a project without `.harnex.yml`, and each acts only when
    the project enabled its set or feature.
20. Only `apply` ticks `tasks.md`, on facts: check exit code, path containment, protected
    paths, refs unmoved, evidence bound to a tree fingerprint. A retry is one builder
    fix; interrupted work resumes from recorded state.
21. A spike runs before the first phase whose design it could invalidate. The Codex
    delegation spike (S1) runs before C2; the minimal verifier ships with C2, which
    needs it; adoption is proven in C1c.

## 13. Open questions

- Whether the decision backend for the guard should be allowed in `mock` mode at all, since it would ask on every ambiguous command (default: yes, with the allowlist doing most of the work).
- Which additional MCP servers, if any, the profiles should declare.
- Whether Codex, started through its plugin, honours the `TRACEPARENT` Claude Code passes to Bash, so its spans join the session's trace (S1); and C2's `decide.py` forwarding the session id to OpenRouter as `session_id`. Both serve the owner's [observability bench](observability.md), which is local configuration on the owner's machine and never ships in the plugin.
- Whether the owner's Codex/ChatGPT account can negotiate any of the other five current flagship models — `gpt-6-astra`, `gpt-6-sol`, `gpt-6-luna`, `gpt-5.6-sol`, `gpt-5.6-luna` — the way it now does `gpt-5.6-terra` ([S1](decisions/2026-09-27-s1-delegating-to-codex.md)'s 2026-09-28 update): untested either way, each a one-line `codex exec --model <name> --sandbox read-only "reply pong"` check before the harness relies on it.

Answered since v2: the Stop hook receives the last assistant message directly, in `last_assistant_message` (Claude Code docs, 2.1.267); C1d records a real payload to confirm it. Whether the host's permission syntax can express every deny and ask pattern: yes, for every rule the harness states, with the residue recorded in `floor.json` as `guard_only` — [the decision note](decisions/2026-09-25-the-permission-floor-in-the-hosts-syntax.md), answered in C1c; C4 checks its regenerated floor against those entries one by one. Whether the canary should also hook `SubagentStop`, as §5 first assumed: no, not for the host's own built-in subagents — [the decision note](decisions/2026-09-27-the-canary-checks-the-main-session-only.md), answered in C1d with a real recording of both a briefed and an unbriefed subagent; reopens when `C2` gives harnex its own subagent types. Whether `/codex:rescue` can be pointed at a branch or worktree, how its jobs are recovered after an interruption, and what its sandbox lets it do to `.git`: no targeting of its own (harnex's `apply` must checkout or worktree first and pass `--cwd`), a job record that never distinguishes a stale pid from a live one, and — as of a 2026-09-27 reading of source only — a sandbox toggle not yet observed; §10 and §4 were corrected on that basis — [the decision note](decisions/2026-09-27-s1-delegating-to-codex.md), from S1, run before C2 as planned. Whether the owner's Codex/ChatGPT account can negotiate any model at all: yes, but model-specific, not account-wide — a 2026-09-28 live run in that same note confirmed `gpt-5.6-terra` end to end, through both `codex exec` and the real `codex-companion.mjs task` path (read-only and `--write`, the written file confirmed in `git status`), while `gpt-5.1-codex-max`, retried in the same session, still returns the identical 400; this also confirms §3's sandbox claim and §4's evidence claim by observation for the first time. §2's job-status/interruption behaviour remains unconfirmed live, since that run was foreground only — see the open question above for the five flagship models still untested.

## 14. Risks

- **Codex plugin behaviour** is outside our control and evolving; the C3 spike and a pinned "verified against" version mitigate.
- **Jev is alpha** on OpenRouter, with observed hangs; the `mock` backend, the 3-second timeout and the fail-to-ask rule keep the harness usable without it.
- **Claude Code formats** (hooks payload, agent frontmatter, settings) change monthly; recorded fixtures per version and minimum frontmatter keep the blast radius to one field.
- **Scope creep** toward a runtime; the non-goal is explicit and every phase must be usable on its own.
- **Enforcement gaps on the Codex side**: in v0.1 the builder's limits there are instruction plus detection, and prevention is whatever Codex's sandbox provides. §4 says so; S1 measures it; a Codex-side hook closes part of it later.
- **The floor is coarser than the guard** — not on compound commands, which its deny and ask rules do see, but on wrappers, absolute program paths and anything that depends on the task — so with the hook down some commands the guard would judge are only asked about, and a few are not seen at all. What it cannot express is recorded in `floor.json` as `guard_only`; the floor is tested rule by rule; setup reports project `allow` entries that cover it and warns about modes that bypass permissions.
- **CI's two manifest-validation steps are best-effort, not required.** Whether `claude plugin validate` runs non-interactively in a bare GitHub runner could not be confirmed from a session (`C6`); `check.yml` and `release.yml` install the CLI and run both validate calls with `continue-on-error: true` rather than block on them. If the CLI needs an interactive login there, those two checks silently stop gating anything, while `pytest` and `openspec validate --all` keep gating normally — worth a real CI run confirming which case it is, before trusting the green check alone the way `AGENTS.md`'s own "Before committing" list does locally.
