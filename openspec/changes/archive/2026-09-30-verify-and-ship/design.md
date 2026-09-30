## Context

See `proposal.md` for why. What exists today, and what this design builds on:

- The verifier (`plugin/orchestration/roles/verifier.md`, adapted at
  `plugin/agents/verifier.md`) is read-only (`tools: Read, Grep, Glob`), reads planning
  artifacts from disk, and is started once by `propose`. Its review never blocks anything
  — `propose` shows it and finishes regardless of what it found. This design extends the
  same role rather than forking it, so a person reading `verifier.md` learns one review
  discipline that happens to run at two points in the workflow.
- `apply_loop.py` (`C3`) already keeps "did the check pass" a fact the loop derives itself
  — never the builder's self-report — and fingerprints evidence to the working tree it was
  produced against, refusing stale evidence. `/harnex:verify` reuses both ideas: a script
  runs the check outside any agent, and `ship` refuses a `verify` review that is not
  fingerprinted to the tree being shipped.
- `docs/PLAN.md` §9's shell guard already treats `git commit`, `git push`, and PR-adjacent
  commands as `ask`-severity by default, with no deny-severity pattern on either the guard
  or the floor (`C4`). `ship`'s commit is a second, independent gate on top of that —
  the skill's own "ask the person" step does not replace or widen the guard's own ask.
- §6's setup contract already establishes the pattern this design reuses for the Playwright
  MCP entry: survey, plan, ask only for what cannot be derived, write only on explicit yes,
  own a shared file by entry rather than by whole-file ownership (`.claude/settings.json`'s
  floor entries are the precedent). `project-setup`'s own spec states this generally
  ("Setup offers only what the harness holds"); this design's addition to it follows the
  same shape rather than inventing a new one.
- **This design reopens `docs/PLAN.md` §12 decision 4** ("Three roles: architect, builder,
  verifier") and §11's "later, not scheduled" line naming a deferred `reviewer` role, on the
  project owner's explicit instruction during this change's own `explore`/`propose`
  conversation: a fourth role is wanted now, not deferred, and it replaces C5's original
  "optional `/codex:review`" line. The verifier that reviewed an earlier draft of this
  change flagged that draft for reopening decision 4 silently; this version states it
  openly instead, here and in `proposal.md`, and task 10 in `tasks.md` updates
  `docs/PLAN.md` itself to match once this change lands — the normal way any change already
  brings the plan in sync with what it built, applied to a settled decision instead of an
  open one.

## Goals / Non-Goals

**Goals:**

- `verify` and `ship` share one fact: whether the last verify run, fingerprinted to the
  current tree, found a blocking finding. Nothing else decides whether `ship` may proceed.
- The reviewer's fixed model is a constant the caller starts it with — never a judgement the
  reviewer itself makes, and never a lookup that can vary run to run for the same kind of
  input (the bug an earlier, journal-driven draft of this design had — see D4).
- `review` stays fully decoupled from `verify`/`ship`: no state written by `review` is read
  by either, and nothing about `ship`'s disagreement rule changes whether `review` has run.
- The Playwright MCP entry setup proposes is owned by entry, on explicit yes, and re-
  evaluated on every later setup/update run — the same three properties every other
  setup-written entry already has (§6).

**Non-Goals:** see `proposal.md`. In addition, at the design level: no new field is added
to `.harnex.yml` (decision 11's key list is unchanged); no new `decide.py` question type is
added (the reviewer's model is a fixed constant, not a decision); making the reviewer
actually exclude the tool that built the code under review (see D4).

## Decisions

### D1 · The verifier stays one role; `verify`'s extensions are additive, not a fork

Rather than a second role for spec-vs-code review, the existing `verifier` role gains two
new inputs it may receive (a diff, a facts file) and one new output shape (severity per
finding). `propose`'s call to it is unaffected: no diff, no facts file, same unstructured
prose review it already produces, still never blocking. `verify`'s call adds both inputs
and severity. This keeps "the verifier reviews for coherence" one discipline, defined once,
rather than two prompts that could drift.

*Alternative considered:* a distinct `code-coherence-verifier` role for `verify`. Rejected
— it would duplicate the "reads from disk, reports, never writes, never blocks by default"
discipline the current `verifier.md` already states once, for a difference that is really
just "which inputs it was handed this run."

### D2 · A deterministic script owns the check command and Playwright, never the agent

`/harnex:verify` runs a new script (sibling to `apply_loop.py`, in `plugin/scripts/`) that:
1. Reads `check_command` from `.harnex.yml` and runs it, capturing exit status and output.
2. If the project's profile is a UI stack, runs a Playwright MCP step and captures its
   findings. In this version that step is a stubbed placeholder (proposal's Non-Goals): it
   records that Playwright MCP is not yet configured, rather than actually driving it
   against a running app — the facts-file shape and the profile-gated wiring are real and
   tested; the check itself is future work.
3. Writes both to a facts file under `.harnex/state/` (runtime, not committed, same as the
   decision journal and apply's run state).
4. Only then starts the verifier, pointing it at the facts file and the diff.

If step 1–3 fails before the facts file is written — the script crashes, the interpreter is
missing, `check_command` itself is absent from `.harnex.yml` — `/harnex:verify` SHALL
refuse to start the verifier at all and report the failure directly, the same
internal-error-distinct-from-backend-failure split `C4`'s guard already established for its
own script. A `check_command` that runs and exits non-zero is a different case: the script
succeeded at its job (running the command and capturing the result), so the facts file is
written normally and the verifier reports the failure as a finding (already specified).

### D3 · `ship`'s freshness check reuses `apply`'s fingerprint, not a new mechanism

The "diff against the change's base commit plus untracked files" fingerprint `apply_loop.py`
already computes for task evidence (`apply-command` spec) is reused unchanged for `verify`'s
review: the review is written with the fingerprint of the tree it reviewed, and `ship`
recomputes the current tree's fingerprint and compares. This is the same reason `apply`
already refuses stale evidence — a script's job, not a judgement.

### D4 · The reviewer's model is a fixed constant, not computed from who built the code

An earlier draft of this design computed the reviewer's binding from the `task.route`
journal, excluding whichever tool built the code under review. The verifier reviewing that
draft caught a real bug in it: `/harnex:review` reviews a whole change's diff in one run
(`review-command` spec), but a change whose tasks used *both* builder bindings has no
single "the other one" to exclude — the tie-break the draft proposed (prefer the less-used
binding) could still end up starting the reviewer on a tool that built part of the diff,
contradicting the role's own "never reviews code its own tool built" guarantee for exactly
the tasks that binding did build.

The project owner's direction, given that bug, is to simplify rather than patch the
tie-break: **the reviewer always runs as a Claude subagent on a fixed model, `opus`**,
regardless of which builder or model built the code under review. This is different from
the model the Claude fallback builder itself runs on: `task.route`'s own type is `Choice:
codex / claude / human` (§8) — it has no per-Claude-model granularity, unlike
`phase.route`'s `claude-sonnet` / `claude-opus` / `claude-fable` options — and
`plugin/agents/builder.md` declares no `model:` of its own, so a "claude" resolution always
runs on the host's ordinary default (`sonnet`-class), never `opus`. So "the reviewer's
model always differs from the Claude fallback builder's" is unconditional today, not merely
the common case; it would need revisiting only if `task.route` itself ever grew
per-model options. It does **not** exclude Codex from being reviewed by a tool-adjacent
model, or guarantee anything about the mixed-binding case beyond "the reviewer is
consistent" — a deliberate, named regression from the original "never the same tool"
goal, not an oversight (`proposal.md`'s Non-goals). Revisiting this to read the journal
again, correctly this time — per task rather than per change, or refusing to run when no
single excludable tool exists — is left for later.

This keeps the reviewer's model a fixed value in its own definition, not a computed lookup:
nothing about starting it reads the journal, `.harnex/state/`, or any other run-time state,
so there is no case left for a future bug in that computation to hide in.

### D5 · `ship`'s pull request uses the `gh` CLI

`ship` pushes the branch and runs `gh pr create` for the pull-request step. `gh` is not a
new dependency this design introduces to the person's machine — it is the same tool this
project's own contributors already use to open pull requests — but `ship` does depend on it
being installed and authenticated. See Risks for what happens when it is not.

### D6 · Playwright MCP is project-owned, written by setup only for a UI profile

Rather than declare Playwright MCP at the plugin level (present in every harnexed project
regardless of profile, since a plugin manifest has no per-project switch), this design
follows §6's existing ownership-by-entry pattern instead: `/harnex:setup` proposes an entry
in the project's own `.mcp.json` — the project-scoped MCP configuration file Claude Code
already reads — only when the project's recorded `profiles` include a UI stack, shows the
exact entry first, and writes it only on an explicit yes, exactly like a missing pointer
line in an entry file. `/harnex:update` re-evaluates the same condition on every later run
(`project-setup` spec's new requirements). A project with no UI profile gets no Playwright
entry at all, and the server is never present in a project that never chose one.

*Alternative considered and rejected:* declaring it at the plugin level and leaving only
`/harnex:verify`'s own *use* of it conditional. Rejected on the project owner's explicit
direction — a plugin-wide MCP server would add its tool schema's context cost to every
harnexed project, UI or not, which is exactly the kind of "assumed for everyone" cost
`docs/PLAN.md` §2's profile philosophy ("a profile is chosen per project, not assumed")
already argues against for a named technology.

## What setup and update write

One new path, added to §6's ownership table: `.mcp.json`, **shared, by entry** — the same
ownership model `.claude/settings.json` already has. Setup (and update, re-evaluating on
every run) writes exactly one entry to it, the Playwright MCP server, and only when the
project's recorded `profiles` include a UI stack and the person said yes; every other entry
in `.mcp.json` is the project's own and is never touched. No new `.harnex.yml` key is
needed — the condition is derived from the already-recorded `profiles` list, the same way
every other profile-driven choice already works. `.harnex.yml`, `.harnex/rules.md`,
`.harnex/manifest.json`, `.claude/settings.json`, and every other path §6 already lists are
otherwise unchanged.

## Guarantees

| Guarantee | Kind | What happens when it fails |
|---|---|---|
| The verifier and the reviewer cannot write anything | Prevention (no tool grants the capability) | If the host's own subagent tool-restriction mechanism itself failed, this would degrade to the role prompt's own instruction not to write — the same caveat `C4`'s guard already states for its deterministic-first design |
| "Did the check pass" is a fact, never the verifier's self-report | Detection (a script-derived fact, read, not asked) | If the script crashes before writing the facts file, `/harnex:verify` refuses to start the verifier at all (D2) rather than let it review without facts |
| `ship` refuses on a blocking finding, or on a stale/missing `verify` run | Detection + prevention (a fingerprint comparison gates the write) | If the fingerprint cannot be computed or compared, `ship` treats this the same as a blocking finding — refuses rather than guesses (already specified) |
| `ship` commits only after an explicit yes | Instruction (the skill asks), reinforced by an independent prevention layer (the guard's own default `ask` pattern on `git commit`/`git push`, unchanged since `C4`) | If the skill's own ask were ever skipped by a bug, the guard's own ask still stands between the session and the commit — two independent gates, neither aware of the other |
| The reviewer runs on a different model than the Claude fallback builder's own default | Prevention by construction (the reviewer's model is a fixed constant in its own definition, not computed at run time — D4) | Cannot fail at run time the way a computed lookup could; a wrong value would be a config error in the role's own definition, caught the same way any other wrong constant would be |
| Playwright MCP is present only in a project that chose a UI profile and said yes | Instruction + prevention (setup writes the entry only on explicit yes, by entry — D6, `project-setup` spec) | A project that never runs setup, or declines the entry, has no Playwright server at all; `/harnex:verify` skipping its use when no UI profile is declared (already specified) is a second, independent reason the same outcome holds |

## Risks / Trade-offs

- **[Risk] `gh` is missing or unauthenticated on the person's machine** (D5) →
  **Mitigation:** `ship`'s commit already happened and stands locally; the pull-request
  step is reported as failed, not silently skipped, and `ship` stops there rather than
  archiving or syncing specs against a change with no PR — the person resolves `gh` and
  re-runs `ship`, which is safe since the commit already exists and will not be duplicated.
- **[Risk] The fixed reviewer model does not actually exclude a Codex-built change's own
  tool from reviewing it, or resolve which binding to prefer in a mixed-binding change**
  (D4) → **Mitigation:** named explicitly here and in `proposal.md`'s Non-goals as a
  deliberate simplification, not a guarantee that quietly does less than it claims; the
  spec's own requirement text states only what the fixed rule actually does.
- **[Risk] The check-command/Playwright facts file could go stale the same way task
  evidence could before `apply` added fingerprinting** → **Mitigation:** reusing the exact
  same fingerprint mechanism (D3) rather than inventing a second one closes this the same
  way `apply` already closed it.
- **[Risk] A project's `.mcp.json` cannot be parsed as JSON, or the Playwright entry key
  already exists with different content** → **Mitigation:** treated as a conflict by the
  same survey-then-plan-then-stop discipline `project-setup`'s existing requirements
  already use for every other harness-owned entry; setup does not guess or overwrite.

## Migration Plan

Additive for a project that never touches the new paths: an existing harnexed project's
files are unchanged until it next runs `/harnex:setup` or `/harnex:update`, at which point
a UI-profile project is offered the new Playwright entry (on explicit yes, per D6) and every
other project sees nothing new. `plugin/orchestration/workflow.md`'s `verify` and `ship`
entries move from "not yet implemented" to real, and its `apply` entry is corrected in the
same pass (proposal's Why). No rollback concern beyond the plugin's own version; a project
that never runs `/harnex:verify` or `/harnex:ship` is unaffected, and one that declines the
Playwright entry keeps working exactly as before.

## Open Questions

None. The mixed-binding and Codex-exclusion gaps D4 leaves open are named as deliberate
simplifications in the design itself and in `proposal.md`'s Non-goals, not deferred
unknowns — revisiting them would change the approach, so they are decided (simplify now,
revisit later) rather than left open.
