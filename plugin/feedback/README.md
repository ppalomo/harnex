# Pillar 5 · Feedback & Verification

The vitals: how the harness knows whether what just happened was any good.

## What belongs here

- **The check command**: how a harnessed project's own tests and linters are run, and what
  counts as evidence that they passed.
- **The canary check** under `canary/`: `canary.py`, run by the plugin's `Stop` hook at
  the end of every main-session answer. Inert without `.harnex.yml` or without the
  `canary` set; warns the person, never the model, when the project's word is missing.
  Checks the main session only — a built-in subagent is not briefed on the project's
  instructions, so a missing word there proves nothing (see `docs/decisions/`).
- **The decision journal** under `journal/`: the format every decision is appended in, so
  thresholds can later be tuned on evidence instead of taste.

## What does not

- **The statement of any rule this pillar enforces.** Every one of them is stated in
  pillar 1, and the rule file names the check here that enforces it. A check with no rule
  behind it is a bug: it enforces something no agent was ever told.
- **Anything that runs before an action.** Stopping a command before it runs is pillar 4.
- **Fixing what it finds.** This pillar reports; it never repairs, never commits, and
  never reopens a settled decision.

## Filled by

`C1d` — **delivered**: the canary check and the `Stop` hook that runs it at the end of the
main session's answers. `C2` — **delivered**: the decision journal's format, exercised by
`decide.py`'s first real question; `scope_check.py` under `../feedback/`, the detection
for the `sdd` rule `the-proposal-is-the-scope`. Next: `C4` for the guard's journal entries,
and `C5` for the verification that closes a change.
