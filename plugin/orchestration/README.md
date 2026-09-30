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

- **A role prompt's own content, twice.** A role's Claude Code adapter — the file the host
  actually reads, under `../agents/` — still belongs to this pillar even though it cannot
  live inside `orchestration/` itself (the host looks for it at the plugin root) or import
  the role prompt it binds (an agent's body has no import syntax, verified against Claude
  Code's own docs while designing `C2`). It is a verbatim copy, and a test walks the
  correspondence so the two cannot drift apart unnoticed.
- **Guardrails.** A question that judges *risk* before an action belongs to pillar 4, even
  though it is a decision. Orchestration routes work; control stops it.

## What is here

- `../scripts/decide.py` — the decision interface and its `mock`/`jev` backends, and
  `decide_many()` (`C3`) for asking several questions in one call. Kept in `scripts/`,
  where every harness script lives and where `uv run` expects it, not inside this
  directory — the same reason `../tools/README.md` names `setup.py` the same way.
- `../scripts/apply_loop.py` — the apply loop's own filesystem and process steps (`C3`),
  kept in `scripts/` for the same reason.
- `../scripts/verify_checks.py` — runs the configured check and records the facts the
  verifier receives (`C5`), kept in `scripts/` for the same reason.
- `../scripts/ship_gate.py` — records verifier findings and decides whether a fresh,
  non-blocking verification may proceed to `ship` (`C5`), kept in `scripts/` for the same
  reason.
- `../agents/verifier.md` — the verifier's Claude Code adapter, binding the role prompt
  under `roles/verifier.md`.
- `../agents/builder.md` — the builder's Claude Code adapter (`C3`), binding
  `roles/builder.md`; the Codex binding is reached through its own plugin, not adapted
  here.
- `../agents/reviewer.md` — the reviewer's Claude Code adapter (`C5`), binding
  `roles/reviewer.md`; it always runs on the fixed `opus` model.

## Filled by

`C2` — **delivered**: the workflow, the `verifier` role prompt and its adapter, the
`phase.route` question, the decision client, and the advice line it prints on screen
before anything runs.

`C3` — **delivered**: the `builder` role and its two bindings, `task.route` and
`task.scope`, `decide_many()`, and `apply_loop.py`. Next: `C4` adds `guard.risk` in
pillar 4, not here.

`C5` — **delivered**: the `reviewer` role prompt and its Claude Code adapter; the
verifier's `/harnex:verify` extension for the diff, facts file, and severity-carrying
findings; `verify_checks.py` and `ship_gate.py`; and the workflow's `verify` and `ship`
entries. Next: `C6` adds the update command in pillar 2, not here.
