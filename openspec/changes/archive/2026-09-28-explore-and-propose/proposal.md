## Why

`C1` brings a project to a harnessed state but gives it nothing that *does* architect work:
the five commands are only names until something plays them. `C2` is where the harness
starts wrapping OpenSpec invisibly (README: "Specs are kept by OpenSpec underneath; you
never call it") and where the decision model — named throughout `docs/PLAN.md` since v1,
and the reason `.harnex.yml` already reserves a `decision_model` key — gets its first real
interface and its first real question. Without it, `/harnex:explore` and `/harnex:propose`
are not buildable, and neither is the minimal verifier every later phase's design review
depends on.

Phase: **C2** of `docs/PLAN.md` §11. Exit criterion: a change is proposed and
design-reviewed end to end without the person ever typing `openspec` themselves.

Pillars: **3 · Orchestration** (the decision client and its `phase.route` question, the
verifier's tool-agnostic role prompt, the Claude Code adapter that binds it, per the
existing `agents/` layout note and the role table in §4), **2 · Action & Tools** (the
`explore` and `propose` skills themselves), **5 · Feedback & Verification** (the scope
check that detects an architect writing outside the change's own directory, enforcing the
existing `sdd` rule `the-proposal-is-the-scope`, whose `enforced_by` has been `none` since
`C1b`).

## What Changes

- Add `plugin/scripts/decide.py`: the interface `decide(question_id, state) ->
  Decision(choice | score | probability, probabilities, confidence, backend)` from §8,
  with two backends — `mock` (prints the question, asks the person, so the harness is
  complete with no key) and `jev` (TypeSafe Jev through OpenRouter's decisions endpoint, a
  small `urllib` client with a timeout and one retry, standard library only per decision
  15). The backend is read from the project's `.harnex.yml` `decision_model` key.
- Add `plugin/orchestration/decisions/phase-route.yaml`: the `phase.route` question
  (Choice: `codex` / `claude-<model>` / `human`), its literal criteria, the small state it
  receives, and its own rule on the returned probabilities (highest option if ≥ 0.70, else
  ask) — the first entry in what §8 calls a table of typed questions, not code.
- Every call through `decide.py` appends one line to `.harnex/state/journal.jsonl`
  (`question`, `state_sha256`, `probabilities`, `confidence`, `decision`, `rule_applied`,
  `backend`, an empty `resolution`), and prints the fixed screen line from §3. Because
  `explore` and `propose` run in the main session, whose model harnex cannot switch, the
  line is a recommendation: `Decision (advice): <phase> → <tool> · <model> · <confidence>`,
  never binding here.
- Add `plugin/orchestration/roles/verifier.md`: the tool-agnostic role prompt from the role
  study referenced in §4 — what it reads first (the change's artifacts, re-read from disk),
  what it reports (a review, with findings), what it must refuse (fixing, committing,
  reopening a settled decision, per the role table). Add `plugin/agents/verifier.md`, the
  Claude Code adapter that binds it: minimum frontmatter (`name`, `description`, `tools`),
  and a `tools` list with no `Edit`, `Write` or `Bash` — read-only by construction (P in
  §4's table), not by instruction.
- Add `plugin/feedback/scope_check.py`: given a change name and the repository's working
  tree, reports any path written or modified outside `openspec/changes/<name>/`. This is
  **detection**, not prevention — the architect can still write anywhere; the check reports
  it before the person sees the artifacts. Update `plugin/context/rules/sdd/the-proposal-is-the-scope.md`
  from `enforced_by: none` to `enforced_by: check`, with a `**Enforced by:**` line naming
  the script, closing the gap C1b's own format rule calls a bug when left open.
- Add `plugin/skills/explore/` (`/harnex:explore`) and `plugin/skills/propose/`
  (`/harnex:propose`), landing as skills rather than commands per the finding recorded
  against `C1c` (§11, "a command in front of a skill is two components for one capability").
  `propose` drives the `openspec` CLI directly — the same `new change` / `instructions` /
  `status` sequence OpenSpec's own tooling uses — so a harnessed project needs only the
  `openspec` CLI on its `PATH`, never OpenSpec's own assistant skills; asks the person in
  plain language, never surfaces an artifact id or a schema name; prints the advice line
  before starting; and calls the verifier once every required artifact exists, presenting
  its review before handing control back.
- Add `plugin/orchestration/workflow.md`: the phases, what each may write, and the
  criteria to enter and leave one — the "What belongs here" item the orchestration README
  has named since `C1a` and marked "Filled by `C2`". Only `explore` and `propose` are
  built; `apply`, `verify` and `ship` are named with their entry criteria and marked not
  yet implemented, so the document does not overclaim ahead of `C3` and `C5`.
- Complete `plugin/orchestration/README.md`'s missing "What is here" section (the pattern
  `plugin/tools/README.md` already uses for `../skills/setup/` and `../scripts/setup.py`),
  naming `../scripts/decide.py` and `../agents/verifier.md` as pillar 3 despite living at
  the plugin root, where Claude Code looks for them.
- Update `plugin/feedback/README.md` ("Filled by") and `docs/smoke.md`, and record the
  phase in `docs/PLAN.md`.

## Capabilities

### New Capabilities

- `decision-model`: the `decide()` interface, its `mock` and `jev` backends, the journal
  entry every call appends, the fixed screen line and when it is advice versus binding,
  and the `phase.route` question's own rule.
- `verifier`: the read-only role — what it may read, what it must never do, how its Claude
  Code adapter enforces read-only by its `tools` list rather than by instruction alone.
- `architect-commands`: what `/harnex:explore` and `/harnex:propose` do, in what order,
  what they never do without the person's `openspec` CLI being present, how `propose`
  invokes the verifier and reports the scope check, and the workflow document both read.

### Modified Capabilities

None. `rule-sets` (`C1b`) is unaffected in its requirements — this change only flips one
rule's `enforced_by` field and adds the enforcer the rule already names as missing, which
`rule-sets`' own spec already requires be possible without a new requirement.

## Impact

- New: `plugin/scripts/decide.py` and its tests; `plugin/orchestration/decisions/phase-route.yaml`;
  `plugin/orchestration/roles/verifier.md`; `plugin/agents/verifier.md`;
  `plugin/feedback/scope_check.py` and its tests; `plugin/skills/explore/`,
  `plugin/skills/propose/`; `plugin/orchestration/workflow.md`; `.harnex/state/journal.jsonl`
  as a runtime path (uncommitted, under the existing self-ignoring `.harnex/state/`).
- Changed: `plugin/context/rules/sdd/the-proposal-is-the-scope.md` (`enforced_by` and its
  enforcer line) and the rendering snapshots that include the `sdd` set;
  `plugin/orchestration/README.md`, `plugin/feedback/README.md`; `docs/smoke.md`;
  `docs/PLAN.md` (§11 C2, §13 if any open question is touched).
- Unchanged: `.harnex.yml`'s shape — `decision_model` is already a reserved key since
  decision 11; no new key. Setup's survey/plan/write contract from `C1c` is untouched.
- Dependencies: none added to harnex's own scripts (stdlib only, decision 15). A
  harnessed project must have the `openspec` CLI on `PATH` for `propose` to run — an
  existing, documented expectation (README, `openspec/config.yaml` in §6), not a new one
  this change introduces, but the first change that actually exercises it from inside a
  skill rather than by the person's own hand.
- Host surface: the plugin now declares two skills and one agent; `claude plugin details
  harnex` reflects both.
- Downstream: `docs/decisions/2026-09-27-the-canary-checks-the-main-session-only.md`
  records that a `SubagentStop` canary hook becomes sound once harnex has its own briefed
  subagent types, which the verifier now is. This change does not add that hook — it is
  not part of `C2`'s exit criterion and needs its own recorded evidence, the way `C1d`
  recorded a real payload before trusting a hook's behaviour. Left as a clearly unblocked
  follow-up, not silently done here.

## Non-goals

- No `builder` role, no Codex delegation, no `apply` loop — that is `C3`, and depends on
  `S1`'s answers plus a live Codex run this repository does not have yet.
- No `verify` or `ship` command — `C5`. `workflow.md` names their entry criteria without
  implementing them.
- No `SubagentStop` canary hook for the verifier (see "Downstream" above) — a deliberate,
  named exclusion, not an oversight.
- No change to `guard.risk` or anything under `plugin/control/` — that is `C4`, and
  orchestration's own README already excludes risk questions from pillar 3.
- No version bump or release — `C6`.
