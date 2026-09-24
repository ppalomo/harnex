# Pillar 4 · Control & Guardrails

The immune system: what happens *before* an action runs, and what always stops for a
human.

## What belongs here

- **Permissions per role**: what each role may reach, expressed as the settings a
  harnessed project gets.
- **The shell guard** under `guard/`: the pattern lists, the script that classifies a
  command, and the risk question it asks when the deterministic lists do not decide.
- **The approvals**: the list of actions that always ask the human, with the reason each
  is on the list.

## What does not

- **The statement of a safety rule.** It is stated once in pillar 1; this directory is
  where it is enforced, and the rule file names this enforcement.
- **Checks that run after the fact.** A verification that reads a result belongs to
  pillar 5. The line is the moment: control decides before, feedback judges after.
- **Routing decisions.** Which tool runs a phase is pillar 3.

## Invariants this pillar keeps

- **A deny never comes from a model alone.** Only a deterministic pattern denies; the
  decision model may push an ambiguous command towards asking the human, never past them.
- **It never fails open.** Any error, timeout, missing key or unavailable backend results
  in asking the human, not in allowing.

## Filled by

`C4` — the guard script, its pattern lists, the hook that runs it before a shell command,
and the risk question.
