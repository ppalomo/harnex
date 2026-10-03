## Context

See `proposal.md` — Why. This section covers only what shapes the approach.

Today's `shared`-visibility setup (C1c, docs/PLAN.md §6) writes nine paths, eight of them
committed: `AGENTS.md`, `CLAUDE.md`, `.harnex.yml`, `.harnex/rules.md`,
`.harnex/manifest.json`, entries in `.claude/settings.json`, entries in `.mcp.json`,
`openspec/config.yaml`; only `.harnex/state/` already escapes version control, by holding
a `.gitignore` of its own (`*`) inside itself, so the project's own ignore file is never
touched. That one mechanism — a path excluding itself, from inside itself — is the
precedent this design generalises.

The owner's own constraint, settled across exploration before this change: `local`
visibility must not create or edit `AGENTS.md` or `CLAUDE.md`, whether or not they already
exist. One mechanism, not two depending on whether the project is greenfield or an
existing team repository.

Three facts, verified against primary sources before this design was written (not
assumed):
- `CLAUDE.local.md` is a first-class, currently-supported Claude Code memory file, loaded
  automatically alongside `CLAUDE.md`/`AGENTS.md`, without any `@import` — confirmed
  against `code.claude.com/docs/en/memory` (Claude Code 2.1.28x). It is not gitignored by
  Claude Code itself; the project (or, here, the harness) has to exclude it.
- Having a `CLAUDE.local.md` makes Claude Code stop reading a project's `AGENTS.md` by
  default, unless `Project instructions` is set to `claude-md-and-agents-md` — a setting
  only available at user/managed scope (`~/.claude/settings.json`), not per project.
- `claude mcp add` already has `--scope local` (confirmed via `--help`, default scope),
  and `openspec store setup` already registers a standalone store on the machine
  (confirmed via `--help`) — neither mechanism needed to be invented.

## Goals / Non-Goals

**Goals:**
- One `visibility` choice in setup, `shared` (default, unchanged) or `local`.
- Under `local`, nothing setup writes is ever committed, and nothing it writes requires
  touching a file the project owns — not `AGENTS.md`, not `CLAUDE.md`, not the project's
  own `.gitignore`, not `.claude/settings.json`, not `.mcp.json`, not `openspec/`.
- `git status` is clean immediately after a `local`-visibility setup run, and stays clean
  through every later harness operation on that project.

**Non-Goals:** see `proposal.md` — Non-goals (promotion from `local` to `shared`, giving
Codex a way to read rules under `local` visibility, changing anything about `shared`).

## Decisions

### D1 — `CLAUDE.local.md`, not a line inserted into a tracked file

**Decision:** write `CLAUDE.local.md` at the project root (`@.harnex/rules.md`, one
line), excluded via `.git/info/exclude`.

**Alternative considered:** insert the existing pointer line into `AGENTS.md`/`CLAUDE.md`
and hide the modification with `git update-index --skip-worktree`. Rejected — not on
technical grounds (it would have worked) but because it still means the harness wrote
into a file the project owns; the owner's own framing of the problem ruled this out
explicitly during exploration, in favour of a mechanism that never touches those files at
all, existing or not. `CLAUDE.local.md` is additive by construction — Claude Code loads
it alongside whatever the project already has — so there is nothing to hide a
modification of in the first place.

### D2 — `local` visibility's answers live at a new path, `.harnex/config.yml`; its self-ignore widens to the whole directory

**Decision:** under `local` visibility only, the project's recorded choices live at
`.harnex/config.yml` — a path this change introduces, not a rename of `.harnex.yml` — and
`.harnex/`'s own `.gitignore` (today scoped to `state/`) widens, for `local` visibility
only, to `*` for the whole directory. `shared` visibility is untouched: `.harnex.yml`
stays at the project root, named and committed exactly as `docs/PLAN.md` §12 decision 11
already settled; this change does not reopen it.

**Alternative considered:** keep the `local`-visibility answers file at the project root
too (as `.harnex.yml`, shared name, different content shape) and add it to
`.git/info/exclude` alongside `CLAUDE.local.md`. Rejected — every harness-owned path that
*can* live inside a self-ignoring directory should, so that `.git/info/exclude` carries
exactly one entry (the one file that must live at the project root for Claude Code to
find it) rather than growing with every future local-visibility path, and so that a
`local`-visibility project can never be mistaken for a `shared`-visibility one by the
presence of a root `.harnex.yml`.

### D3 — The floor goes to `.claude/settings.local.json`, not a new mechanism

**Decision:** under `local` visibility, the permission floor's entries are written to
`.claude/settings.local.json` instead of merged into `.claude/settings.json`.

**Rationale:** already an established, documented Claude Code convention — personal,
excluded from version control by convention, already relied on elsewhere in this
repository (`docs/observability.md`). Nothing new to build or explain.

**Alternative considered:** drop the floor entirely under `local` visibility, relying
only on the plugin's guard hook (which already needs no project file). Rejected — the
floor exists specifically as the fallback for when the hook itself fails to start (PLAN
§9); dropping it under `local` visibility would leave those projects with a strictly
weaker safety net for a reason that has nothing to do with visibility.

### D4 — `claude mcp add --scope local`, not an untracked `.mcp.json`

**Decision:** register the Playwright entry (or any future MCP entry a profile needs)
with `claude mcp add <name> ... --scope local` instead of writing to the project's
`.mcp.json`.

**Rationale:** the CLI already has this exact distinction (`--scope local|user|project`,
`local` the default); nothing invented, nothing to protect with an ignore entry, because
no project file is written at all.

### D5 — A local OpenSpec store, registered once, keyed like auto memory

**Decision:** under `local` visibility, setup runs `openspec store setup` once, records
the store id among the project's choices, and `propose`, `apply`, `verify` and `ship`
resolve `--store` (or, where a script reads `openspec/changes/<name>/` directly rather
than through the CLI, `--changes-root`) from that recorded id rather than the nearest
`openspec/`. `explore` and `review` resolve nothing — neither calls `openspec` or reads
a change's own directory under either visibility, so there is nothing for either to
resolve; an earlier draft of this design and of the `local-visibility` delta spec said
otherwise, caught and corrected during this change's own `/harnex:verify` run. The
store's own id is derived from the project the same way Claude Code's own auto-memory
keys its per-project directory — from the git repository, so every worktree and
subdirectory of the same repo shares one store, the same sharing rule auto memory
already uses.

**Alternative considered:** keep creating `openspec/` inside the project, but exclude it
via `.git/info/exclude` the same way as `CLAUDE.local.md`. Rejected — `openspec/changes/`
and `openspec/specs/` grow over time as the person works; a store purpose-built for
exactly this ("standalone OpenSpec repos you register on this machine") means there is
no directory inside the project to protect at all, rather than an ignore entry that has
to keep up with a growing tree.

### D6 — The roles/tools question is explicit, and states the Codex/`AGENTS.md` limitation at the point it's asked

**Decision:** `local` visibility's guided question list includes which roles/tools the
person wants active; choosing Codex triggers an explicit statement, at that point, that
the Codex builder binding will not see this project's rules under `local` visibility.

**Rationale:** the owner asked for a guided setup, explicitly listing "which agents you
need" as an example. Separately, this closes a real silent-failure mode: without the
statement, a person could enable Codex as builder and never learn that it never saw the
project's rules in the first place.

**Alternative considered:** silently exclude Codex from the choices offered under `local`
visibility. Rejected per `proposal.md`'s Non-goals — Codex is not specially blocked, only
honestly described.

### D7 — The one-time `~/.claude/settings.json` offer is part of setup, not documentation

**Decision:** setup itself offers the `instructionFiles: claude-md-and-agents-md` change,
showing the exact edit and writing it only after an explicit yes — at most once needed
per machine, never per project, never under `shared` visibility.

**Rationale:** without this setting, the very first `local`-visibility setup on a project
that relies on `AGENTS.md` (no `CLAUDE.md` of its own) silently stops Claude Code from
reading that `AGENTS.md` the moment `CLAUDE.local.md` exists — a correctness break, not a
nicety. Setup is the one place that already knows both facts (that it is about to write
`CLAUDE.local.md`, and what the person's own settings currently say), so it is the
natural place to ask, following the same "show the exact change, write only on yes"
discipline C1c already established for the pointer-line case.

**Alternative considered:** document the step instead of offering it. Rejected — the harm
is automatic and immediate on the very first local setup; a document only helps someone
who reads it first.

## Guarantees — kind and failure mode

- **Nothing local-visibility writes is tracked by accident** (ordinary `git add .` /
  `git add -A`): **Prevention**, from git's own exclude mechanisms
  (`.git/info/exclude`, and each self-ignoring `.gitignore`). Fails only against a
  deliberate `git add -f` — the same limit `shared` visibility already lives with for its
  own guard and floor (nothing here claims to stop a person who overrides git on
  purpose).
- **`AGENTS.md`/`CLAUDE.md` are never created or modified under `local` visibility**:
  **Instruction**, by construction — the code path that creates or inserts into those
  files is a `shared`-visibility-only path, never invoked under `local` — plus
  **Detection**: a test asserts both files are byte-identical (or still absent) before
  and after a `local`-visibility setup run, the same snapshot style C1c's own tests
  already use.
- **A `local`-visibility project still reads `AGENTS.md` after `CLAUDE.local.md`
  exists**: **Instruction** only, and conditional — it holds once the person accepts the
  one-time global offer (D7); if declined, setup states the consequence at decline time
  and repeats the notice on every later run, mirroring the existing pointer-line-decline
  pattern. There is no enforcement layer behind this one: it is the person's own global
  Claude Code setting.
- **A harness-owned path is overwritten only when it matches the record** (existing
  `harness-ownership` guarantees): unchanged under `local` visibility, since the record
  still exists and is still read the same way — it is simply never committed.

## Risks / Trade-offs

- [Risk] A deliberate `git add -f` can still stage an excluded path → Mitigation: none
  claimed beyond the ordinary case; stated plainly in the guarantees above rather than
  implied.
- [Risk] A gitignored `CLAUDE.local.md` "only exists in the worktree where you created
  it" (per Claude Code's own docs) → Mitigation: out of scope here; relevant only if a
  future change has `apply`/`ship` operate in worktrees under `local` visibility.
- [Risk] Declining the D7 offer silently stops `AGENTS.md` from being read the moment
  `CLAUDE.local.md` exists → Mitigation: stated at decline time, repeated on every later
  run; no stronger guarantee is claimed.
- [Risk] Local OpenSpec stores accumulate across unrelated projects on one machine with
  no harness-driven cleanup → Mitigation: out of scope; `openspec store remove` already
  exists as a manual, person-driven tool.
- [Risk] A person enables Codex as an active role under `local` visibility and later
  forgets the one-time D6 statement → Mitigation: accepted, named in `proposal.md`'s
  Non-goals; this change makes the limitation visible once, it does not solve it.

## Migration Plan

Not applicable in the deploy/rollback sense: `shared` visibility is unaffected and stays
the default, so no existing project needs to do anything. There is, deliberately, no path
from `local` to `shared` yet (`proposal.md` — Non-goals); a project that wants to move
from personal use to team adoption reruns `/harnex:setup` choosing `shared` from scratch,
which this change does not change or improve.

## Open Questions

- Exactly where `claude mcp add --scope local` records its entry (confirmed the flag
  exists and defaults to `local`; not yet confirmed which file it writes to). Does not
  change the requirement, which only asks for "a local-scoped registration" — worth a
  one-line confirmation during implementation.
- Whether `instructionFiles: claude-md-and-agents-md` behaves exactly as documented on
  the version of Claude Code this change ships against — confirmed against primary docs
  (2.1.28x) but not yet exercised end to end, the same kind of gap S1 left open for Codex
  before C2. Worth one live check during implementation; does not change the approach
  either way, since the offer is conditional and self-describing regardless of outcome.
