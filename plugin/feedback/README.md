# Pillar 5 · Feedback & Verification

The vitals: how the harness knows whether what just happened was any good.

## What belongs here

- **The check command**: how a harnessed project's own tests and linters are run, and what
  counts as evidence that they passed.
- **The canary check** under `canary/`: the script that reads the last answer and warns
  when the agreed word is missing, which is how a lost instruction set is detected.
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

`C1d` — the canary check and the hook that runs it at the end of an answer. Then `C4` for
the guard's journal entries, and `C5` for the verification that closes a change.
