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

`openspec store setup` needs `--path`. Setup asks for it, passes it as the `store_path` answer (never recorded; only the id is)
(local only, validated like `store_id`), and prints "register store `<id>` at `<path>`"
as a plan line. The skill runs the command after the yes and before `write`. The script's
`write` keeps requiring a non-empty `store_id` and does not check the store exists.

### D3 · `.env` goes through `.git/info/exclude`, under both visibilities

The existing `GIT_EXCLUDE_PATHS` mechanism already adds root-level paths there for
`local`. `.env` joins it when `decision_model` is `jev` and the project is inside a git repository
(found through `git rev-parse`, see D4). Under `shared`
the same entry is safe (the file is per clone, not project-owned) and costs one line, so
the gap is closed for both; the notice states that it protects this clone only, because
`shared` teammates' clones have their own exclude list. The project's `.gitignore`
stays untouched. The entry is added even if `.env` does not exist yet, since the person
creates it next.

### D4 · A clean git tree is a precondition, checked by the script

Revised after the first `apply` run, at the person's request. The earlier version of this
decision planned a `git init` step under `local` visibility; it is withdrawn. Setup now
requires a git repository with a clean working tree, under either visibility, and never
creates one: running `git init` on an existing folder leaves every file untracked, which
is the opposite of clean, and leaves the person's first commit unreviewed.

The script checks it during the survey, through the standard library's `subprocess`
running `git status --porcelain=v1 --untracked-files=all` (decision 15 holds: no
dependency, only the `git` the project already uses). No repository, a failing `git`
or any output line is a conflict, so `write` refuses on the same terms as any other
conflict, and its own re-survey catches a tree that changed after the plan. Under
`update` the check does not apply: a shared project's harness-owned files may be
legitimately uncommitted between `setup` and the first commit.

Revised again after `verify`: paths setup itself writes or owns do not count against the
tree, so a rerun before the first commit and a rerun after an interruption both still
work without the person repairing anything ("Running setup again changes nothing" and
"An interrupted setup completes on the next run" stay true). The conflict joins the
plan's other conflicts rather than replacing the plan, so every path is still printed
once. The repository is found through git (`rev-parse`), not by looking for a `.git`
directory, so worktrees and subdirectories work, and the exclude file is resolved with
`git rev-parse --git-path info/exclude`. A `store_path` answered alongside an already
recorded `store_id` is refused.

### D5 · Reusing a store registered by an interrupted run

Revised after the third `verify`. A run interrupted after `openspec store setup` and
before `write` leaves the store registered and `.harnex/config.yml` unwritten. The skill
finds the store with `openspec store list --json` and passes a `store_registered: true`
answer alongside its `store_id` and an empty `store_path`; the script then plans a
"reuse store `<id>`" line instead of a registration, and records the id on `write`. The
script does not query `openspec` itself: the answer is the skill's, like every other.

Git's messages are read under `LC_ALL=C`, so telling "no repository" from a git failure
does not depend on the person's locale. The `.env` exclude step is owned by "this
clone" under `shared` visibility, matching `docs/PLAN.md`.

## Risks

- A Codex prompt prefix can be ignored by the model. Mitigated, not removed: the
  apply loop's own checks (`task_scope_check`, the check command) still run after every
  builder.
