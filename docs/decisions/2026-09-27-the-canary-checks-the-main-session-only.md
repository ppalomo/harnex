# The canary checks the main session only

**Date:** 2026-09-27 · **Phase:** C1d · **Status:** answered, and one claim in the plan
corrected · **Verified against:** Claude Code 2.1.267

## The question

`docs/PLAN.md` §5 listed the canary's hook as `Stop, SubagentStop`, on the assumption
that a subagent's last answer is checkable the same way the main session's is. Before
building that second hook, C1d asked: does a subagent actually receive the project's
instructions closely enough that a missing canary word means the same thing there as it
does for the main session?

## What was recorded

A scratch project (`CLAUDE.md` asking for the word `Hullaballoo!`), with a dumping `Stop`
and `SubagentStop` hook, run as a real Claude Code `2.1.267` session:

- The main session's answer, ending with the word — recorded as
  [`stop.json`](../../tests/fixtures/hooks/2.1.267/stop.json).
- A `general-purpose` subagent, asked a trivial question — recorded as
  [`subagent-stop-general-purpose.json`](../../tests/fixtures/hooks/2.1.267/subagent-stop-general-purpose.json).
  Its `last_assistant_message` ends with the word.
- A built-in `Explore` subagent, asked a trivial question — recorded as
  [`subagent-stop-explore.json`](../../tests/fixtures/hooks/2.1.267/subagent-stop-explore.json).
  Its `last_assistant_message` does **not** end with the word.

Both subagents ran inside the same session, given the same project. The only variable is
which built-in agent type answered.

## The answer

**`Stop` only. No `SubagentStop`, for now.** The `Explore` subagent's own instructions do
not include the project's `CLAUDE.md`, so it was never in a position to end with the
word — nothing was not followed, because nothing was asked of it. A hook that warned on
its answer anyway would be a false positive on every single `Explore` call, which is
often enough to teach the person to ignore the warning. A signal that fires when nothing
is wrong destroys the only value the canary has (design.md, D1).

`general-purpose` shows the check is not impossible in principle — that subagent type
does receive the project's instructions and does end with the word. The difference is
which built-in agent types the host chooses to brief, a list harnex does not control and
the host can change without notice. Matching a `SubagentStop` hook to that list would
couple the canary to host internals it has no say over.

## One claim in the plan was wrong

`docs/PLAN.md` §5 listed `canary (Stop, SubagentStop)` among what `plugin/hooks/hooks.json`
declares. It now lists `Stop` only; the canary rule's `**Enforced by:**` line says the
same, and says so on the main session's answers only.

## What would reopen this

`C2` gives harnex its own `verifier` subagent, whose prompt harnex writes and therefore
can guarantee ends with the canary rule. At that point a `SubagentStop` hook matched on
harnex's own agent types (not on the host's built-in ones) becomes sound, and it reuses
this script and these fixtures rather than a new check (proposal.md, "Downstream").
Nothing here should be read as ruling that out — only as ruling out matching the host's
own, unbriefed, subagents.
