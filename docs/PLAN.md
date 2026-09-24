# harnex — development plan (v2)

harnex is a public, reusable **harness** for AI coding agents. It centralises everything
that turns a model into a working agent — instructions, tools, workflow, guardrails and
verification — so a new project gets it in one command instead of rebuilding it.

This is the second version of the plan. The first was reviewed by six independent
reviews ([REVIEW-2026-09-24.md](REVIEW-2026-09-24.md)) and a role study
([ROLES-2026-09-24.md](ROLES-2026-09-24.md)); this version applies their findings and the
owner's decisions. It is a living document: every phase is delivered as one or more
OpenSpec changes, and when one lands this plan is updated to match.

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
| 4 | **Control & Guardrails** | immune system | permissions per role, the shell guard, human approvals |
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
   OpenSpec and let a **decision model pick which tool and model runs each phase**, saying
   so on screen.
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

Routing to Codex means `/codex:rescue --model <m>`; routing to Claude with a given model
means a subagent with that `model:`; the architect phases run in the main session and the
line is advisory. When the backend is `mock`, the line says so and asks you.

**Canary.** Every answer from any model must end with the canary word declared in
`.harnex.yml` (default `Hullaballoo!`). A Stop hook checks the last answer and warns when
the word is missing. A missing canary means the model has lost its instructions: compact
or restart. This is the first rule that is both stated (pillar 1) and enforced (pillar 5).

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

## 5. Repository layout

```
harnex/
  README.md  LICENSE  AGENTS.md  CLAUDE.md
  .claude-plugin/marketplace.json     catalogue with one entry: the harnex plugin
  plugin/                             THE CLAUDE CODE PLUGIN — what a machine installs
    .claude-plugin/plugin.json          name, version
    commands/                           explore, propose, apply, verify, ship (pillar 2)
    skills/                             setup, update (pillar 2)
    agents/                             builder.md, verifier.md (Claude adapters of the roles, pillar 3)
    hooks/hooks.json                    guard (PreToolUse Bash), canary (Stop)
    context/                            1 · rules/ (one file per rule, grouped in sets), templates/ (AGENTS.md,
                                            CLAUDE.md, .harnex.yml, rules.md), memory.md
    tools/                              2 · mcp/ declarations, profiles/ (python-fastapi, react-vite)
    orchestration/                      3 · workflow.md, roles/ (prompts), decisions/ (typed questions, YAML)
    control/                            4 · permissions.json, guard/ (patterns.yaml, guard.py), approvals.md
    feedback/                           5 · check-command.md, canary/canary.py, journal/format.md
    scripts/                            decide.py (backend interface), setup.py, update.py — Python, run with uv
  docs/                               PLAN.md, diagrams/, reviews, decisions/ (ADRs), smoke.md
  openspec/                           harnex's own specs and changes
```

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
features, canary word and decision backend, and writes:

| Path | Owner | Notes |
|---|---|---|
| `AGENTS.md` | **project** | created only if missing, from a template; never touched again |
| `CLAUDE.md` | harness | `@AGENTS.md` and `@.harnex/rules.md` |
| `.harnex.yml` | project | your answers: `project_name`, `profiles`, `features`, `canary`, `decision_model`, `check_command` |
| `.harnex/rules.md` | harness | rendered from the rule sets chosen; first line of `AGENTS.md` tells Codex to read it |
| `.claude/settings.json` | harness | permissions per role, the project's extras from `.harnex.yml` |
| `openspec/config.yaml` | shared | harness rules for artifacts, project context from you; created only if missing |
| `.harnex/state/` | runtime | decision journal, gitignored |

Update, whenever harnex changes: `claude plugin update harnex` refreshes the behaviour;
`/harnex:update` re-renders the harness-owned project files from `.harnex.yml`. Ownership
is by **file**, never by section: a manifest with hashes in `.harnex/state/manifest.json`
lets `update` overwrite a harness-owned file whose hash still matches what it wrote, and
stop with a message when you edited it. Project-owned files are never read or written by
`update`. Codex reads the project's `AGENTS.md` and, through its first line, the rules file.

Why a plugin, after the first plan rejected marketplaces: that rejection assumed Codex
CLI as a second consumer. With Codex reached only through its own plugin, the Claude
plugin mechanism delivers hooks, agents, skills, commands and MCP in one versioned unit,
updates with one command, and leaves the project with six small files. Copier was
evaluated and dropped: it has no notion of ownership, cannot merge `settings.json`, and
cannot adopt an existing project.

## 7. Rules

A rule is a short statement of how work is done that every agent must follow. In harnex a
rule is one file under `plugin/context/rules/<set>/<rule>.md` with frontmatter `id`,
`set`, `applies_to` (always, or a profile), `enforced_by` (none, guard, hook, check,
decision). The body is the rule as an agent reads it, with its reason, in a few lines.

Sets in v0.1, all selectable in `setup` and recorded in `.harnex.yml`:

- `git`: branch per change, conventional commit messages, **no AI author or co-author
  lines ever**, commits only in `ship`.
- `code`: the check command runs before any claim of done, tests beside what they test,
  no scope beyond the task.
- `sdd`: the change's artifacts are the brief, re-read from disk; `proposal.md` is the
  scope; never tick `tasks.md` from a builder.
- `safety`: what always asks you (destructive commands, pushes, credentials, deletions).
- `canary`: every answer ends with the canary word.
- `language`: everything committed in English.

`setup` renders the chosen sets into `.harnex/rules.md`. A rule with `enforced_by: guard`
also feeds the guard's pattern lists; one with `enforced_by: hook` has a hook in the
plugin. Project-specific rules stay in `AGENTS.md`; a rule is promoted into harnex only
when it has no project noun in it.

## 8. The decision model

One interface, in `plugin/scripts/decide.py`:

```
decide(question_id, state) -> Decision(choice | score | probability, probabilities, confidence, backend)
```

Backends: `jev` (TypeSafe Jev through OpenRouter's decisions endpoint, a small httpx
client with retries, since the vendor SDK cannot target OpenRouter) and `mock` (prints the
question and asks you, so the harness is complete without any key). Adding a backend is
one class. The backend is chosen in `.harnex.yml`.

Questions live as YAML in `plugin/orchestration/decisions/` and `plugin/control/guard/`,
each with its type, literal criteria, the state it receives, **its own decision rule on
the returned probabilities**, and its behaviour when the backend is `mock`:

| Question | Type | State (kept small) | Rule |
|---|---|---|---|
| `phase.route` | Choice: codex / claude-<model> / human | phase, task or brief summary, profiles | highest option if its probability ≥ 0.70, else ask you |
| `task.route` | Choice: codex / claude / human | one task's text and file list | same |
| `task.scope` | Noul | task text, changed paths | ≥ 0.85 in scope; ≤ 0.35 out of scope; between → ask you |
| `guard.risk` | Score: read_only / reversible / destructive | command, cwd, branch, is_worktree | P(destructive) ≥ 0.30 → ask; P(read_only) ≥ 0.85 → allow; else ask |

What is deliberately **not** a question: whether the check passed (an exit code), whether
the plan is complete (OpenSpec validation plus the verifier's review), whether a change is
ready (findings carry severities; any blocking finding blocks). Never send the model's own
description of its command: self-arguing text moves the answer.

Every decision is appended to `.harnex/state/journal.jsonl` with `question`,
`state_sha256`, `probabilities`, `confidence`, `decision`, `rule_applied`, `backend` and a
`resolution` field filled when you override or when the outcome is known, so thresholds
can be tuned on evidence. Screen line format is fixed: `Decision: <phase> → <tool> · <model> · <confidence>`.

## 9. The shell guard

A PreToolUse hook on Bash in the plugin, `guard.py`, with the decision table in diagram 05:
parse the command; every part in the read-only allowlist → allow silently; a deny pattern →
deny with reason; an ask pattern → ask you; the residue → `guard.risk` with a 3-second
timeout and one retry; any error, timeout, missing key or `mock` backend → **ask**. Deny
never comes from the model alone. Rules with `enforced_by: guard` feed the three lists.

Codex runs under its own sandbox through the Codex plugin. A Codex-side hook with the same
script is a later feature, not v0.1.

## 10. Roadmap — one capability per phase

Each phase is one OpenSpec change with three parts: what it delivers, **how you try it**
by hand, and the automated tests that need no credentials. Phases are sliced by
capability so that every one of them leaves something you can use. A phase that would
deliver several independent capabilities is split into lettered changes, each one usable
on its own and landing in order; C1 is split that way.

### C1 · install and setup — four changes

C1 delivers the whole installation path, which is four independent capabilities: a plugin
that installs, rules that render, a setup that writes a project, and a canary that
enforces itself. Each is its own OpenSpec change, in this order.

#### C1a · an installable plugin
- **Delivers:** the catalogue `.claude-plugin/marketplace.json` with its single entry; `plugin/.claude-plugin/plugin.json` (name, version `0.1.0`); the five pillar directories, each with a `README.md` stating what belongs in it and what does not; `docs/smoke.md` with the format every later phase appends its manual check to.
- **You try it:** `claude plugin marketplace add .` from your checkout, `claude plugin install harnex@harnex`, then `/plugin`: harnex is listed with its version. Nothing else happens yet, and that is the point.
- **Tests:** `claude plugin validate plugin --strict`; a structural test asserting every directory under `plugin/` is either a pillar or one of the directories Claude Code reads; the private-names grep denylist over the whole plugin.
- **Exit:** the plugin installs from a local checkout and validates strict, on a machine that has never seen harnex.

#### C1b · rule sets and their rendering
- **Delivers:** the rule file format (frontmatter `id`, `set`, `applies_to`, `enforced_by`) and the six sets of §7 — `git`, `code`, `sdd`, `safety`, `canary`, `language` — one file per rule under `plugin/context/rules/<set>/`; `plugin/scripts/render_rules.py`, which turns a list of sets into `.harnex/rules.md` deterministically. Pillar 1, with the renderer as its only script.
- **You try it:** `uv run plugin/scripts/render_rules.py --sets git,code --out -` prints the rules file those two sets produce; add `safety` and the file grows by exactly that set.
- **Tests:** frontmatter schema validation over every rule file; rendering snapshots for several set combinations; an assertion that a rule whose `enforced_by` is not `none` names its enforcer in its body; the private-names denylist over the rendered output.
- **Exit:** every rule is stated exactly once, and the same set list always renders the same file, byte for byte.

#### C1c · setup writes a project
- **Delivers:** `/harnex:setup` (pillar 2) and `plugin/scripts/setup.py`; the templates for `AGENTS.md`, `CLAUDE.md`, `.harnex.yml`, `.claude/settings.json` and the OpenSpec config; the questions it asks (profiles, features, canary word, decision backend) and the six files it writes, calling C1b's renderer for `.harnex/rules.md`; the hash manifest at `.harnex/state/manifest.json`, written as it writes, which `update` will read in C6.
- **You try it:** open a scratch project, run `/harnex:setup`, answer the questions, read the six files. Run it a second time: nothing changes. Write your own `AGENTS.md` first and run it: yours is left untouched.
- **Tests:** render with defaults for each profile combination against committed snapshots; a second run is byte-identical to the first; an existing `AGENTS.md` and an existing OpenSpec config are never overwritten; the manifest records a hash for every harness-owned path.
- **Exit:** a scratch project is set up in one command, and a second `setup` changes nothing.

#### C1d · the canary enforces itself
- **Delivers:** first the spike that answers §12's second open question — whether a Stop hook receives the last assistant message or must read the transcript — recorded in `docs/decisions/`; then `plugin/feedback/canary/canary.py` and the Stop hook in `plugin/hooks/hooks.json`, reading the word from `.harnex.yml` and falling back to `Hullaballoo!` when there is none. Pillar 5, enforcing the `canary` rule that C1b states.
- **You try it:** ask Claude anything in the scratch project: the answer ends with your canary word. Delete the canary line from `.harnex/rules.md` and ask again: the hook warns that the model has lost its instructions.
- **Tests:** pytest over recorded Stop payloads — word present, word missing, `.harnex.yml` absent, transcript unreadable — and the hook returning within its timeout in each; a check that every rule with `enforced_by: hook` resolves to a hook that exists, which fails on C1b alone and passes here.
- **Exit:** the canary is stated once and enforced once, and removing the statement is detected.

### C2 · explore and propose
- **Delivers:** the two architect commands wrapping OpenSpec's explore and propose invisibly; the decision client with `mock` and `jev` backends; `phase.route` and its screen line; the verifier's design review inside `propose`.
- **You try it:** `/harnex:explore "an idea"` in the scratch project, then `/harnex:propose`. You see the `Decision:` line first, then the artifacts appear under `openspec/changes/`. With `OPENROUTER_API_KEY` set and `decision_model: jev`, the line comes from Jev; with `mock`, it asks you.
- **Tests:** unit tests of `decide.py` against recorded OpenRouter responses and the mock; the journal gets one line per decision; command frontmatter.
- **Exit:** a change is proposed end to end without you ever typing `openspec`.

### C3 · apply through Codex
- **Delivers:** a one-day spike first, recorded in `docs/decisions/`: how reliably `/codex:rescue` takes a task, works on a branch and returns evidence. Then the `builder` role, the Claude fallback subagent, the two profiles moved from the old kits, `task.route`, `task.scope`, and the loop of diagram 04.
- **You try it:** propose a two-task change, run `/harnex:apply`, watch each task's `Decision:` line, watch Codex work through the plugin's job status, see the check command run and the evidence reported. Break a test on purpose: the loop retries once with the output, then escalates.
- **Tests:** a fake `codex-companion` on `PATH` that records what it was asked and returns a canned diff; the loop's state after accept, retry and escalate; scope check with the mock backend.
- **Exit:** both tasks land on the change's branch with a green check and evidence, without you writing code.

### C4 · shell guard
- **Delivers:** `guard.py`, `patterns.yaml`, the PreToolUse hook, `guard.risk`, the journal for guard decisions, the `safety` rules feeding the lists.
- **You try it:** ask Claude to run `ls`: no prompt. Ask it to `rm -rf /tmp/harnex-test`: denied, with the reason. Ask it to `git push`: it asks you. Unset the API key and ask something ambiguous: it asks you and says the backend was unreachable.
- **Tests:** pytest over recorded hook stdin payloads for each row of the decision table; the hook exits within its timeout with the backend stubbed to hang.
- **Exit:** the table in diagram 05 holds for every fixture, with the backend on and off.

### C5 · verify and ship
- **Delivers:** the `verifier` subagent with Playwright MCP, the `verify` command, optional `/codex:review` as second opinion, the `ship` command (commit after your yes, PR, archive, sync specs), the disagreement rule (any blocking finding blocks).
- **You try it:** finish the C3 change: `/harnex:verify` reports findings with evidence, `/harnex:ship` asks before committing, opens the PR, archives the change. Check the commit has no AI author line.
- **Tests:** verifier frontmatter has no `Bash`; `ship` refuses without an explicit yes in a recorded transcript; the archive step runs OpenSpec's sync.
- **Exit:** one change goes explore → ship on the scratch project.

### C6 · update and release
- **Delivers:** `/harnex:update` with the hash manifest; plugin versioning and `vX.Y.Z` tags; the README rewritten for a stranger; a "verified against" table (Claude Code, Codex, OpenSpec versions); one existing project migrated and the old private marketplace deprecated; CI.
- **You try it:** change a rule in your harnex checkout, bump the version, `claude plugin update harnex`, `/harnex:update` in the project: only `.harnex/rules.md` changes. Edit `.harnex/rules.md` by hand and update again: it stops and tells you.
- **Tests:** update between two tags in CI on a rendered project; manifest mismatch detection; README links resolve.
- **Exit:** `v0.1.0` tagged; a stranger can install it from the README.

Later, not scheduled: tuning thresholds from the journal's resolutions; a Codex-side guard
hook; a separate `reviewer` role; a `security-reviewer` for projects with an attack
surface. Never: an unattended mode.

## 11. Decisions taken

1. Organised by the five pillars; placement by topic; stacks are profiles.
2. Claude Code is the only cockpit. Codex is reached through its official plugin only.
3. Delivery is a Claude Code plugin for behaviour plus six generated files per project. Ownership is by file, with a hash manifest. Copier and the old marketplace are dropped.
4. Three roles: architect, builder, verifier. The orchestrator is the human. Commits only in `ship`.
5. The decision model sits behind one interface; `jev` and `mock` backends in v0.1; each question carries its own rule on probabilities; `mock` behaviour is defined for every question.
6. The guard is deterministic first and never fails open; deny never comes from the model alone.
7. The canary is a rule plus a Stop hook; default word `Hullaballoo!`, set per project in `.harnex.yml`.
8. Everything committed is English, command names included: `explore`, `propose`, `apply`, `verify`, `ship`.
9. Python with `uv` for scripts; minimum frontmatter for agents and skills.
10. No AI author or co-author lines in commits or PRs, in harnex and in every harnessed project (`git` rule set).
11. Names fixed now: `.harnex.yml` keys `project_name`, `profiles`, `features`, `canary`, `decision_model`, `check_command`; rules at `.harnex/rules.md`; state under `.harnex/state/`; tags `vX.Y.Z` from `v0.1.0`.
12. `docs/` and `openspec/` are public; `.claude/` and `.agents/` at the repo root stay local.
13. Phases are sliced by capability, each with a manual try and automated tests.
14. A phase delivering several independent capabilities is split into lettered changes
    that land in order. C1 is four: `C1a` an installable plugin, `C1b` rule sets and
    their rendering, `C1c` setup writing a project, `C1d` the canary enforcing itself.

## 12. Open questions

- Whether `/codex:rescue` can be pointed at a specific branch or worktree, or whether `apply` must create the branch first (answered by the C3 spike).
- Whether the Stop hook receives the last assistant message directly or must read the transcript (answered by the C1d spike, before any canary code is written).
- Whether the decision backend for the guard should be allowed in `mock` mode at all, since it would ask on every ambiguous command (default: yes, with the allowlist doing most of the work).
- Which additional MCP servers, if any, the profiles should declare.

## 13. Risks

- **Codex plugin behaviour** is outside our control and evolving; the C3 spike and a pinned "verified against" version mitigate.
- **Jev is alpha** on OpenRouter, with observed hangs; the `mock` backend, the 3-second timeout and the fail-to-ask rule keep the harness usable without it.
- **Claude Code formats** (hooks payload, agent frontmatter, settings) change monthly; recorded fixtures per version and minimum frontmatter keep the blast radius to one field.
- **Scope creep** toward a runtime; the non-goal is explicit and every phase must be usable on its own.
