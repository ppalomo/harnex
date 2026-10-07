## Context

The first real `local` run is the evidence (see the proposal). Four decisions follow.

## Decisions

### D1 · Codex gets the rules from the apply loop's prompt, not from a file it discovers

Options considered for getting rules to Codex under `local` visibility:

- **`AGENTS.override.md` in the project, excluded via `.git/info/exclude`.** Codex reads
  an override *instead of* `AGENTS.md` in the same directory, so it would hide the
  project's own instructions. Rejected.
- **`~/.codex/AGENTS.md`.** Machine-wide: every project, harnessed or not, would carry
  this project's rules. Rejected.
- **The prompt the apply loop passes.** The loop already composes it, `.harnex/rules.md`
  is on disk in the working tree (ignored by git, not hidden from the workspace), and the
  change is one sentence in one skill. Chosen. It is a prompt instruction, not a rule, so
  "a rule is stated once" holds: the rule text stays in `.harnex/rules.md`.

Cost accepted: Codex used directly, outside `apply`, still has no rules. The disclosure
says so.

### D2 · The store path is an answer, registration happens after the yes

`openspec store setup` needs `--path`. Setup asks for it, records it as `store_path`
(local only, validated like `store_id`), and prints "register store `<id>` at `<path>`"
as a plan line. The skill runs the command after the yes and before `write`. The script's
`write` keeps requiring a non-empty `store_id` and does not check the store exists.

### D3 · `.env` goes through `.git/info/exclude`, under both visibilities

The existing `GIT_EXCLUDE_PATHS` mechanism already adds root-level paths there for
`local`. `.env` joins it when `decision_model` is `jev` and `.git` exists. Under `shared`
the same entry is safe (the file is per clone, not project-owned) and costs one line, so
the gap is closed for both; the notice states that it protects this clone only, because
`shared` teammates' clones have their own exclude list. The project's `.gitignore`
stays untouched. The entry is added even if `.env` does not exist yet, since the person
creates it next.

### D4 · `git init` is a plan line, run by the skill

The script never shells out to `git`. Where it today reports a conflict ("no .git
directory here"), under `local` visibility with a missing repository it plans the
exclude entries as pending on a `git init` step; the skill asks once for the whole plan, runs `git init` after
the yes and before `write`; there is no second plan. The conflict remains for `shared` visibility, where `.git` is not
setup's to create.

## Risks

- A Codex prompt prefix can be ignored by the model. Mitigated, not removed: the
  apply loop's own checks (`task_scope_check`, the check command) still run after every
  builder.
