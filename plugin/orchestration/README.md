# Pillar 3 · Orchestration

The nervous system: who does what, in which order, and who decides.

## What belongs here

- **The workflow**: the phases, what each one may write, and the criteria to enter and
  leave it.
- **The role prompts** under `roles/`: one file per role, written to one skeleton —
  what the role may write, what it must refuse, what it reads first, what it reports.
- **The decision questions** under `decisions/`: one typed question per file, each with
  its criteria, the small state it receives, its own rule on the returned probabilities,
  and what it does when the decision backend is unavailable.

## What does not

- **Tool names inside a role prompt.** A role is a contract, not a runtime: the same
  `builder` prompt must work whichever tool plays it. The adapters that bind a role to a
  particular runtime live at the plugin root, where the host reads them.
- **The decision client.** The interface and its backends are scripts; the questions are
  what lives here.
- **Guardrails.** A question that judges *risk* before an action belongs to pillar 4, even
  though it is a decision. Orchestration routes work; control stops it.

## Filled by

`C2` — the workflow, the first role prompts, the routing question and the line it prints
on screen before anything runs.
