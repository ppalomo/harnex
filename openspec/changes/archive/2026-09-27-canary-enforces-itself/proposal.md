## Why

The `canary` rule has been stated since `C1b` and setup has recorded a project's word since
`C1c`, but nothing reads an answer to see whether the word is there. A rule that claims
`enforced_by: hook` with no hook behind it is exactly what pillar 5 calls a bug: the
cheapest signal that the rules have dropped out of the context is promised and never
given. This change closes that gap, and with it the whole install path of `C1`.

Phase: **C1d** of `docs/PLAN.md` §11. Exit criterion: the canary is stated once and
checked once; it acts only where it was chosen; removing the statement is detected.

Pillars: **5 · Feedback & Verification** (the canary check and the hook that runs it),
**1 · Context & Memory** (the `canary` rule's wording, revised to say what the check does
and does not prove), **2 · Action & Tools** (`setup.py` states the word in `AGENTS.md`, so
a model has somewhere to read its own canary word from). Three components, three pillars,
one capability.

## What Changes

- Add `plugin/feedback/canary/canary.py`: reads the host's end-of-turn payload, and — only
  in a project whose `.harnex.yml` chooses the `canary` set — warns the person when the last
  answer does not end with the recorded word. It never blocks, never makes the model
  continue, and has no fallback word of its own. Standard library only, reading
  `.harnex.yml` with the reader setup already uses, so there is one reader of that file.
- Add `plugin/hooks/hooks.json` with a `Stop` hook that runs it, declaring a timeout above
  the script's own budget.
- **Main session only.** The plan said `Stop` *and* `SubagentStop`. A payload recorded
  from Claude Code `2.1.267` shows why not: a built-in `Explore` subagent does not receive
  the project's instructions and so never ends with the word, while a `general-purpose`
  one does. A check on `SubagentStop` would warn on every such subagent and teach the
  person to ignore the warning. The finding is recorded in `docs/decisions/`, and the
  plan is corrected.
- Keep the recorded payloads as test fixtures, with their paths and ids replaced, so the
  field the check depends on — `last_assistant_message` — is tested against what the
  host actually sends rather than what its documentation says.
- Revise the `canary` rule so its reason matches §3: a missing word is a signal that this
  one instruction was not followed, not a diagnosis that the context is lost; and its
  `**Enforced by:**` line names the check by path, so a check can walk from the rule to the
  hook.
- Add the check that walks both ways: every rule with `enforced_by: hook` names a script
  that exists and that a declared hook runs, and every hook the plugin declares runs a
  script some rule names. The first half fails on `C1b` alone and passes here.
- Update the pillar 5 README, append this change's section to `docs/smoke.md`, and record
  what landed in `docs/PLAN.md`.
- **Found while trying it, fixed here.** `.harnex/rules.md` is a pure function of the
  chosen sets, so the canary rule can only ever say "the word the project declares" — it
  cannot state the word itself. Nothing else in a rendered project ever stated it either:
  the word lived in `.harnex.yml` only, which nothing points a model at. A model given the
  rule genuinely could not comply; it had no way to learn the word. `setup.py` now renders
  a `## Canary` section into `AGENTS.md`, naming the word, when (and only when) the project
  chooses the `canary` set. `.harnex.yml`'s shape is unchanged — no new key, no new
  question — this only states, in the one place a model actually reads, the fact setup
  already recorded.

## Capabilities

### New Capabilities

- `canary-check`: when the harness looks for the canary word, where it looks for the
  project's choice, what it says when the word is missing, what it never does (block,
  continue the turn, guess a word, act in a project that did not choose it), and what
  happens when it cannot run.

### Modified Capabilities

- `rule-sets`: the requirement "A rule that is enforced names its enforcer" gains the
  walk the other way for hooks — a rule that claims a hook resolves to a hook the plugin
  declares, and a hook the plugin declares is claimed by a rule.

## Impact

- New: `plugin/feedback/canary/canary.py`, `plugin/hooks/hooks.json`, the recorded
  payload fixtures and the tests over them, a decision note under `docs/decisions/`.
- Changed: `plugin/context/rules/canary/canary-ends-every-answer.md` (reason and enforcer
  line), and so the committed rendering snapshots that include it;
  `plugin/feedback/README.md`; `docs/smoke.md`; `docs/PLAN.md` (§3, §11 C1d, decision 7,
  §13); `plugin/context/templates/AGENTS.md` and `plugin/scripts/setup.py` (a `## Canary`
  section, rendered only for a project that chooses the set), and so the setup snapshot
  that includes it.
- Unchanged: `.harnex.yml`'s shape — no new file, key or entry to a project. The hook
  reads it; setup already wrote it before this change.
- Dependencies: none added.
- Host surface: the plugin now declares one hook, so `claude plugin details harnex` lists
  one hook. A hook adds no always-on tokens to a session.
- Downstream: `C2`'s verifier is harnex's own subagent, so whether its answers carry the
  word is harnex's to decide; if they should, `C2` adds a `SubagentStop` hook matched on
  harnex's own agent types, built on this script and these fixtures.

## Non-goals

- No check of subagent answers (see above), and none of Codex's answers, which never pass
  through a Claude Code hook.
- No blocking and no automatic remedy: the check does not force the model to continue, does
  not compact, and does not re-inject the rules. It tells the person, who decides.
- No new question in setup and no new key in `.harnex.yml`: the word and the set are
  already recorded.
- No journal entry for a missing word. The decision journal arrives with `C2`/`C4`; the
  canary is a signal to the person, not a decision.
- No version bump or release; that is `C6`.
