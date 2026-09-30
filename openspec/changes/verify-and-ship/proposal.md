**Pillar:** 3 · Orchestration (the `verifier` and new `reviewer` roles, the workflow's
`verify`/`ship` entries) and 2 · Action & Tools (`setup`'s new Playwright MCP entry) — no
`plugin/control/` change, since `ship`'s commit and PR commands fall under the guard's
existing default patterns (see Impact).

**Phase:** `docs/PLAN.md` §11, `C5 · verify and ship`. Exit criterion: "one change goes
explore → ship on the scratch project."

**This change deliberately reopens decision 4** (§12: "Three roles: architect, builder,
verifier") and removes "a separate `reviewer` role" from §11's "later, not scheduled" list,
on the project owner's explicit direction: a fourth role, `reviewer`, is wanted now rather
than deferred, and its own command replaces the "optional `/codex:review`" C5's original
roadmap entry named. `docs/PLAN.md` is updated to match once this change lands (last task).

## Why

A change can go `explore` → `propose` → `apply`, but nothing after that: `apply` leaves
every task ticked and the tree uncommitted, with no phase that checks the result against
its specs and the running app, and no phase allowed to commit, open a PR, or archive the
change. `docs/PLAN.md` §11 names this gap `C5 · verify and ship`, the next unscheduled
phase after `C4 · shell guard` (delivered). Its own exit criterion — "one change goes
explore → ship" — cannot be met without both phases existing.

## What Changes

- Extend the existing `verifier` (today: read-only, planning-artifacts-only, invoked once
  by `propose`) to also read a change's diff against its specs, and to receive — as facts
  handed to it, never as its own judgement — the exit status of the project's own
  `check_command` and, when the project declares a UI profile, a Playwright MCP step (a
  stubbed placeholder in this version — see Non-Goals) for the running app. Both run
  deterministically outside the verifier's own subagent, the same way `apply_loop.py`
  already keeps "did the check pass" a fact rather than a builder's self-report.
- Give the verifier's findings a severity of either `blocking` or `advisory`, and scope its
  existing "never blocks" rule to the callers where it still applies (`propose`'s use of
  it): a `blocking` finding now can stop `ship`, which no earlier caller could do.
- Add `/harnex:verify`: runs the checks above and presents the verifier's review with
  severity.
- Add `/harnex:ship`: the first command allowed to `git commit` (after the person's
  explicit yes), open a pull request, archive the change, and sync its deltas into
  `openspec/specs/`. It refuses when `/harnex:verify`'s last run found a blocking finding
  — the disagreement rule `docs/PLAN.md` §11 names for this phase.
- Add a new role, `reviewer`, and `/harnex:review`: a read-only, code-quality review (bugs,
  simplification, efficiency) of the diff, distinct from the verifier's spec-coherence
  review. The reviewer always runs as a Claude subagent on a fixed model distinct from the
  builder fallback's own fixed model, regardless of whether the code under review was built
  by Codex, by the Claude fallback, or by a person — a deliberately simple rule for now,
  not the journal-driven exclusion an earlier draft of this change tried and the verifier
  caught as buggy in the mixed-builder case; revisiting it to actually exclude Codex-built
  code from a Codex reviewer, or vice versa, is left for later. `/harnex:review` never
  blocks `ship`; it is a recommended, independent step the person runs when they choose.
- Extend `/harnex:setup` (and `/harnex:update`) to propose a Playwright MCP entry in the
  project's own `.mcp.json`, shown and written only when the project's chosen profiles
  include a UI stack, and only after an explicit yes — the same pattern setup already uses
  for a missing pointer line in an entry file. No MCP server is declared at the plugin
  level; a project with no UI profile gets nothing.
- Correct `plugin/orchestration/workflow.md`'s `apply` entry, still marked "not yet
  implemented, arrives in `C3`" though `C3` delivered and archived it — caught while
  rereading the file this change also has to extend.

## Capabilities

### New Capabilities
- `reviewer-role`: the read-only role definition for code-quality review — what it may and
  may not do, and its fixed-model guarantee.
- `review-command`: what `/harnex:review` does for the person — starts the reviewer against
  the change's diff, presents the findings, and never blocks `ship`.
- `verify-and-ship-commands`: what `/harnex:verify` and `/harnex:ship` do for the person, in
  order — running the checks, presenting severity-carrying findings, and the disagreement
  rule that lets a `blocking` finding stop `ship` before its first-ever commit, PR, archive,
  and spec sync.

### Modified Capabilities
- `verifier`: adds reading the diff against specs and receiving check-command/Playwright
  facts as input; findings now carry a severity of either `blocking` or `advisory`; the
  existing "the review never blocks the person from proceeding" requirement is scoped to
  callers other than `ship`, since `ship` now can refuse to proceed on a `blocking` finding.
- `project-setup`: adds proposing and, on explicit yes, writing the Playwright MCP entry in
  the project's own `.mcp.json` when a UI profile is chosen — offered and withheld by the
  same rules already governing every other setup choice.

## Impact

- `plugin/orchestration/roles/verifier.md` and its adapter `plugin/agents/verifier.md`
  (modified); `plugin/orchestration/roles/reviewer.md` and `plugin/agents/reviewer.md`
  (new).
- `plugin/skills/verify/`, `plugin/skills/ship/`, `plugin/skills/review/` (new commands).
- A new deterministic script alongside `plugin/scripts/apply_loop.py` for running
  `check_command` and, where applicable, the Playwright check, and handing their facts to
  the verifier.
- `plugin/scripts/setup.py` (modified): proposes and writes the project's `.mcp.json`
  Playwright entry, by entry, the same ownership model already used for
  `.claude/settings.json`'s floor entries.
- `plugin/orchestration/workflow.md` (corrected and extended with real `verify`/`ship`
  entries in place of "not yet implemented").
- No change to `plugin/control/` — `ship`'s `git commit`/`git push`/PR commands fall under
  the guard's existing default `ask` patterns from `C4`; no new pattern is needed for this
  change to work.

## Non-goals

- `/harnex:update`, plugin versioning, and everything else `docs/PLAN.md` §11 assigns to
  `C6`, beyond the one Playwright entry `/harnex:update` also needs to re-propose if a
  project's profile changes.
- Resolving `docs/PLAN.md` §13's open question on which MCP servers profiles should declare
  in general — this change declares Playwright only, for the UI-profile case `C5` itself
  needs.
- Any new deny-severity guard pattern — `ship`'s commit and PR commands rely on the
  existing `ask` floor from `C4`; deny-severity patterns remain absent on both sides, as
  they were left in `C4`.
- Making the reviewer's fixed model actually exclude the tool that built the code under
  review — the simplified rule (a fixed Claude model, always) is a deliberate, named
  regression from that goal, not an oversight; see "What Changes."
- Building a real Playwright MCP check of the running app: `verify_checks.py`'s Playwright
  step is a stubbed placeholder in this version, always recording that Playwright MCP is
  not yet configured — the profile-gated wiring and the facts-file shape are real and
  tested, the check itself is future work. Proving the running-app path end to end is
  likewise out of scope for this change's own manual try-it: the person is setting up their
  own scratch project for that separately, and will report back; this change's own exit
  criterion is met by the non-UI path.
