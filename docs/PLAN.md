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
| **Claude** | the session itself, and subagents | architect (main session), verifier (fresh-context subagent), builder fallback |
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

Three roles in v0.1, from the role study. Prompts are tool-agnostic and follow one
skeleton (see the study). The orchestrator is you plus the commands.

| Role | Player | May write | Must refuse | Commands |
|---|---|---|---|---|
| `architect` | Claude, main session (`opus`; `fable` for hard designs) | the change's artifacts | source, tests, commits | explore, propose |
| `builder` | Codex via the plugin; Claude subagent as fallback | source and tests within the task's declared paths | ticking `tasks.md`, committing, editing specs, widening scope | apply |
| `verifier` | Claude subagent, fresh context, read-only; `/codex:review` as optional second opinion | nothing | fixing, committing, reopening settled decisions | propose (design review), verify |

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

| Rule | architect (main session) | builder · Codex | builder · Claude subagent | verifier |
|---|---|---|---|---|
| write only what the role may write | I · D: `propose` reports any change outside the change's directory | I · D: changed paths ⊆ the task's declared paths | I · D: same check | I · P: `tools` has no `Edit`, `Write` or `Bash` |
| never tick `tasks.md`, never edit specs | — (the architect writes them) | I · D: protected paths (`openspec/`, `.harnex/`) unchanged after the delegation | I · D: same check | P: as above |
| commit only in `ship` | I · P: guard asks, floor asks | I · D: `HEAD` and refs unchanged after the delegation | I · P: guard asks, floor asks | P: as above |
| destructive commands, deletions, pushes ask | I · P: guard + floor | I only, in practice: `approvalPolicy` is hardcoded to `never` for every delegated call, so Codex itself never pauses to ask ([S1](decisions/2026-09-27-s1-delegating-to-codex.md)) — the ask has to come from harnex's own guard, once C4 lands · D: the diff is read before acceptance | I · P: guard + floor | P: as above |
| credentials never leave the machine | I · P: floor denies reading secret files; guard asks | I · P: Codex CLI's own `read-only`/`workspace-write` sandbox toggle, as read from `codex.mjs` — [S1](decisions/2026-09-27-s1-delegating-to-codex.md) could not confirm this by observation; a live run is owed before C3 treats it as measured | I · P: floor + guard | P: as above |
| answers end with the canary word | I · D: Stop hook | I only | I · D: SubagentStop hook, when the set is on | I · D: SubagentStop hook |

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
    agents/                             builder.md, verifier.md (Claude adapters of the roles, pillar 3)
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
| `openspec/config.yaml` | **project** | yes | created only if missing, with the harness's artifact rules; afterwards only you change it |
| `.harnex/state/` | runtime | no | decision journal and apply run state; ignored by a `.gitignore` inside the directory itself, so the project's own `.gitignore` is never touched |

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
- **Delivers:** `/harnex:setup` — one skill, `plugin/skills/setup/`, and `plugin/scripts/setup.py` with three verbs (`choices`, `plan`, `write`); the templates for `AGENTS.md`, `CLAUDE.md`, `.harnex.yml` and the OpenSpec config under `plugin/context/templates/`, the two pointer lines being files of their own that state where the line goes, what proves it is there and what is lost without it; the questions setup asks, offering only what the harness holds; the survey–plan–write sequence and adoption of §6, calling C1b's renderer for `.harnex/rules.md`; the permission floor (`plugin/control/floor.json`, pillar 4), every entry naming the rule it comes from, and its entry-level merge into `.claude/settings.json`; the committed record at `.harnex/manifest.json` and the self-ignoring `.harnex/state/`. The whole update contract of §6 is fixed here — record format, conflict rules, atomic writes, recovery by content — even though the `update` command arrives in C6. Pillar 4's README is restated in the terms of §9, and the five rules the guard enforces now name both layers and say what each one gives.
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
- **Exit:** each question has an answer with the transcript that shows it, and §10 and the §4 matrix are corrected where the answers differ from the assumptions. **Partially met**: every model tried returns `400 invalid_request_error … not supported when using Codex with a ChatGPT account`, unchanged after updating the CLI and after a fresh `codex login` — the plugin's own `setup --json` diagnostic reports the login verified, so this traces to the account's own Codex entitlement, not to a stale token or a need for an API key. All four answers therefore come from `codex-companion.mjs`'s own source and its fake-fixture tests, not a live transcript. §10 and §4 are corrected below on that basis; C3 budgets one live run to confirm §3's sandbox claim and §2's interruption behaviour before treating them as measured.

### C2 · explore and propose — **delivered**, change `explore-and-propose`
- **Delivers:** `plugin/scripts/decide.py` — `decide(question, state, backend)`, the `mock` and `jev` backends, the decision journal at `.harnex/state/journal.jsonl` — plus the decision-question file format under `plugin/orchestration/decisions/` (YAML-*shaped*, like a rule) and its first question, `phase.route`; the `verifier` role, split as `orchestration/roles/verifier.md` (tool-agnostic) and `agents/verifier.md` (the Claude Code binding, read-only by its `tools` list); `plugin/feedback/scope_check.py`, the detection for the `sdd` rule `the-proposal-is-the-scope` (`enforced_by` now `check`, not `none`); `plugin/orchestration/workflow.md`, naming all five phases and what each may write; and the two skills, `plugin/skills/explore/` and `plugin/skills/propose/`, which drive the `openspec` CLI directly rather than depend on OpenSpec's own assistant skills being installed in the target project.
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

### C3 · apply through Codex
- **Delivers:** the `builder` role, the Claude fallback subagent, the two profiles moved from the old kits, `task.route`, the path and protected-path checks, `task.scope` for tasks without declared paths, and the loop of §10 with its run state, fingerprinted evidence, one fix per failure and recovery — built on the answers of S1. The `sdd` and `code` rules the loop now checks (`builders-never-tick-tasks`, `no-scope-beyond-the-task`) are restated to name the path and protected-path checks as their detection.
- **You try it:** propose a two-task change, run `/harnex:apply`, watch each task's `Decision:` line, watch Codex work through the plugin's job status, see the check run and the evidence reported, and see the task ticked by `apply`. Break a test on purpose: the builder gets the output and makes one fix; break it so the fix cannot work: it escalates. Interrupt `apply` while Codex works, run it again: it recovers the job or asks you.
- **Tests:** a fake `codex-companion` on `PATH` that records what it was asked and returns a canned diff; the run state after accept, fix, escalate and interruption at each transition; a builder that touches `tasks.md`, commits, or writes outside its paths is refused; evidence with a stale fingerprint is refused; scope check with the mock backend.
- **Exit:** both tasks land on the change's branch with a green check and evidence, ticked by `apply`, without you writing code; an interrupted run resumes without redoing or losing work.

### C4 · shell guard
- **Delivers:** `guard.py`, `patterns.yaml`, the PreToolUse hook with a declared timeout above the script's budget, `guard.risk`, the journal for guard decisions, the `safety` rules feeding the lists, per-role lists keyed on `agent_type`; the floor from C1c regenerated from the same patterns, so the two layers cannot drift.
- **You try it:** ask Claude to run `ls`: no prompt. Ask it to `rm -rf /tmp/harnex-test`: denied, with the reason. Ask it to `git push`: it asks you. Unset the API key and ask something ambiguous: it asks you and says the backend was unreachable. Then break the hook — rename the script — and ask for `git push` again: Claude Code reports the hook error and the floor still asks.
- **Tests:** pytest over recorded hook stdin payloads for each row of the decision table; the hook run as a real process: backend stubbed to hang (answers ask within its budget), script crashing (answers nothing: the test asserts the floor has an entry for every deny and ask pattern), interpreter missing, and a hook killed at its timeout; floor and pattern lists compared entry by entry.
- **Exit:** the table in diagram 05 holds for every fixture, with the backend on and off; for every way the hook itself can fail, the floor covers every deny and ask pattern.

### C5 · verify and ship
- **Delivers:** the verifier of C2 extended with Playwright MCP and verification of a diff against the specs and the running app, the `verify` command, optional `/codex:review` as second opinion, the `ship` command (commit after your yes, PR, archive, sync specs), the disagreement rule (any blocking finding blocks).
- **You try it:** finish the C3 change: `/harnex:verify` reports findings with evidence, `/harnex:ship` asks before committing, opens the PR, archives the change. Check the commit has no AI author line.
- **Tests:** verifier frontmatter still has no `Bash`, `Edit` or `Write`; `ship` refuses without an explicit yes in a recorded transcript; the archive step runs OpenSpec's sync.
- **Exit:** one change goes explore → ship on the scratch project.

### C6 · update and release
- **Delivers:** `/harnex:update` implementing the contract C1c fixed; plugin versioning and `vX.Y.Z` tags; the README rewritten for a stranger; a "verified against" table (Claude Code, Codex, OpenSpec versions); one real project migrated and the old private marketplace deprecated; CI.
- **You try it:** change a rule in your harnex checkout, bump the version, `claude plugin update harnex`, `/harnex:update` in the project: only `.harnex/rules.md` and the manifest change. Edit `.harnex/rules.md` by hand and update again: it stops and tells you. Kill it halfway and run it again: it completes.
- **Tests:** update between two tags in CI on a rendered project and on an adopted one; manifest mismatch detection; interruption after each write; README links resolve.
- **Exit:** `v0.1.0` tagged; a stranger can install it from the README.

Later, not scheduled: tuning thresholds from the journal's resolutions; a Codex-side guard
hook; a separate `reviewer` role; a `security-reviewer` for projects with an attack
surface. Never: an unattended mode.

## 12. Decisions taken

1. Organised by the five pillars; placement by topic; stacks are profiles.
2. Claude Code is the only cockpit. Codex is reached through its official plugin only.
3. Delivery is a Claude Code plugin for behaviour plus a handful of small files per project (§6). Ownership is by file, with a committed hash manifest; the one exception, `.claude/settings.json`, is owned by entry. Copier and the old marketplace are dropped.
4. Three roles: architect, builder, verifier. The orchestrator is the human. Commits only in `ship`.
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
- Whether the owner's Codex/ChatGPT account can negotiate any model at all: S1 found every model tried, including a plain non-Codex one, returning "not supported when using Codex with a ChatGPT account" with a "model metadata not found" warning first, and a fresh `codex login` mid-spike changed nothing — ruling out a stale token, and ruling out needing an API key (the plugin's own README and its `setup --json` diagnostic both say the ChatGPT-subscription login this account has is sufficient, and that login is verified). What's left points at the account's own Codex entitlement or an OpenAI-side rollout gap, resolvable only outside harnex. C3 cannot deliver a working builder role on the Codex side until one live run succeeds.

Answered since v2: the Stop hook receives the last assistant message directly, in `last_assistant_message` (Claude Code docs, 2.1.267); C1d records a real payload to confirm it. Whether the host's permission syntax can express every deny and ask pattern: yes, for every rule the harness states, with the residue recorded in `floor.json` as `guard_only` — [the decision note](decisions/2026-09-25-the-permission-floor-in-the-hosts-syntax.md), answered in C1c; C4 checks its regenerated floor against those entries one by one. Whether the canary should also hook `SubagentStop`, as §5 first assumed: no, not for the host's own built-in subagents — [the decision note](decisions/2026-09-27-the-canary-checks-the-main-session-only.md), answered in C1d with a real recording of both a briefed and an unbriefed subagent; reopens when `C2` gives harnex its own subagent types. Whether `/codex:rescue` can be pointed at a branch or worktree, how its jobs are recovered after an interruption, and what its sandbox lets it do to `.git`: no targeting of its own (harnex's `apply` must checkout or worktree first and pass `--cwd`), a job record that never distinguishes a stale pid from a live one, and a sandbox toggle read from source only, not observed — [the decision note](decisions/2026-09-27-s1-delegating-to-codex.md), from S1, run before C2 as planned but blocked from a live transcript by a model-negotiation fault this spike traced to the account's own Codex entitlement, not to the ChatGPT-subscription design (a fresh login, mid-spike, changed nothing, and no API key is expected to be needed); §10 and §4 are corrected on that basis and C3 owes one live run before treating §3's sandbox claim as measured.

## 14. Risks

- **Codex plugin behaviour** is outside our control and evolving; the C3 spike and a pinned "verified against" version mitigate.
- **Jev is alpha** on OpenRouter, with observed hangs; the `mock` backend, the 3-second timeout and the fail-to-ask rule keep the harness usable without it.
- **Claude Code formats** (hooks payload, agent frontmatter, settings) change monthly; recorded fixtures per version and minimum frontmatter keep the blast radius to one field.
- **Scope creep** toward a runtime; the non-goal is explicit and every phase must be usable on its own.
- **Enforcement gaps on the Codex side**: in v0.1 the builder's limits there are instruction plus detection, and prevention is whatever Codex's sandbox provides. §4 says so; S1 measures it; a Codex-side hook closes part of it later.
- **The floor is coarser than the guard** — not on compound commands, which its deny and ask rules do see, but on wrappers, absolute program paths and anything that depends on the task — so with the hook down some commands the guard would judge are only asked about, and a few are not seen at all. What it cannot express is recorded in `floor.json` as `guard_only`; the floor is tested rule by rule; setup reports project `allow` entries that cover it and warns about modes that bypass permissions.
