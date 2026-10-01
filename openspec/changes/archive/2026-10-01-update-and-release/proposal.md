## Why

Every harness-owned file a project carries was written once, by `setup`, and has had no
way to change since. A rule edited in the harness checkout, a re-rendered `rules.md`, a
new permission-floor entry — none of it reaches a project that already ran setup, because
`C6`'s contract (`docs/PLAN.md` §6) is fixed but nothing implements it yet. Nor is the
plugin itself versioned in a way a project can pin against, and the README still describes
the repository as it was before `C2`–`C5` landed. A harness nobody can update, from a
repository a stranger cannot install from, is not yet shippable.

Phase: **C6** of `docs/PLAN.md` §11. Exit criterion: `v0.1.0` tagged; a stranger can
install it from the README.

Pillars: **2 · Action & Tools** (`/harnex:update` and its script, reusing `setup`'s own
survey/plan/write machinery), **1 · Context & Memory** (nothing new stated, but the
`AGENTS.md`/`CLAUDE.md` pointer-line notice path is exercised, not written, by update).

## What Changes

- Add `/harnex:update`: a skill plus `plugin/scripts/update.py`, implementing the contract
  §6 already fixed and C1c already tested harness-side against (`setup`'s own
  `build_plan`/`write_atomic`/manifest machinery is reused, not re-implemented) —
  - **Reads** `.harnex.yml` and `.harnex/manifest.json`; reads `AGENTS.md`/`CLAUDE.md` only
    to report a missing pointer line, never to insert one (that approval is `setup`'s).
  - **Writes** only harness-owned paths (`.harnex/rules.md`, `.harnex/state/.gitignore`)
    and harness-owned entries (`.claude/settings.json`'s floor entries, `.mcp.json`'s
    Playwright entry) — never a project-owned file (`AGENTS.md`, `CLAUDE.md`, `.harnex.yml`,
    `openspec/config.yaml`).
  - Overwrites a harness-owned file only if its current hash matches the manifest; an
    edited file stops the run and names the file, the same way a `setup` conflict does.
  - Surveys and stops on conflict before writing anything; writes each file atomically;
    writes the manifest last — so an interruption recovers by content on the next run
    (a file whose hash matches either the old or the new rendering is safe; anything else
    stops it).
  - Refuses, naming `setup`, when `.harnex.yml` exists but `.harnex/manifest.json` does
    not (harness files present with no record of them is the same unresolvable case
    `setup`'s own survey already refuses, not a case to guess at here).
  - A fresh clone works unaided: every committed path is recognised from the committed
    manifest and nothing is asked; the one uncommitted path, `.harnex/state/`, is restored.
- Version the plugin: `plugin/.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json` gain a release process — a `vX.Y.Z` git tag per
  release, starting at `v0.1.0`, with both manifests' `version` fields kept at the tag.
- Add a "verified against" table (Claude Code, Codex CLI, OpenSpec versions this release
  was tested with) to the README.
- Rewrite `README.md` for a stranger: drop the "planned"/"early" framing now that `C2`–`C5`
  shipped five real commands, document `/harnex:update` alongside `/harnex:setup`, and
  describe the installed state truthfully.
- Add CI (GitHub Actions): run `uv run --with pytest pytest`,
  `claude plugin validate plugin --strict` / `claude plugin validate . --strict`, and
  `openspec validate --all` on every push and pull request; add a release workflow that
  tags and publishes on a version bump.
- Migrate one real project from the old private marketplace to `harnex`, by hand, and
  record what the migration needed; remove that project's registration from the private
  marketplace once `/harnex:setup` (adoption path) and `/harnex:update` both work on it.

## Capabilities

### New Capabilities

- `harness-update`: what `/harnex:update` is, what it reads, what it is allowed to write,
  that it shares setup's survey → plan → stop-on-conflict → write sequence scoped to
  harness-owned content only (never asking, never creating or inserting into a
  project-owned file, never offering adoption — that stays setup's), the hash-match/
  conflict rule that protects an edited file, how an interruption recovers, and what a
  project with no `.harnex.yml` or no manifest sees. `project-setup`'s own requirements
  already anticipate this command by name (its Playwright-entry and `.env`-notice
  requirements read "setup or update") and need no change; `harness-ownership`'s
  regeneration contract is already written generically enough ("any operation that
  refreshes a harnessed project") to cover update without a delta.

### Modified Capabilities

- `plugin-delivery`: the identity requirement gains what a stranger needs to trust and
  complete an install — the versions this release was verified against, and that the
  README alone is enough to reach a harnessed project.

## Impact

- New: `plugin/skills/update/SKILL.md`, `plugin/scripts/update.py`, its tests (update
  between two tags on a rendered project and on an adopted one, manifest-mismatch
  detection, interruption after each write kind, a conflict stopping the run and naming
  the file), `.github/workflows/` (check + release), the migrated project's own
  `.harnex.yml`/adoption record (outside this repository).
- Changed: `README.md` (rewritten), `plugin/.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json` (version bump to the tag), `docs/PLAN.md` (records
  what landed, C6 marked delivered), `docs/smoke.md` (gains an update section).
- Unchanged: `setup.py`'s own survey/plan/write functions, called by `update.py` rather
  than duplicated; the manifest format fixed in C1c; the permission floor and its merge
  rules; every rule set and renderer.
- Dependencies: none added to the plugin itself (standard library only, decision 15);
  CI adds a GitHub Actions workflow file, outside `plugin/`.
- Downstream: none — this is the last phase before `v0.1.0`.

## Non-goals

- No rule editing and no per-project rule overrides — update refreshes what setup already
  rendered, it does not change what a project chose; changing a project's own `sets` or
  `profiles` answers is a `setup`/adoption concern, not update's.
- No uninstall command.
- No automatic migration tool for the old private marketplace — the one project named
  above is migrated by hand, to learn what a migration needs, not to build a migrator.
- No change to what `setup` writes or asks; `update`'s scope is strictly narrower than
  `setup`'s (harness-owned paths and entries only), never wider.
- No semantic versioning policy beyond "tag what you release starting at `v0.1.0`" — when
  the project needs a real policy (breaking rule changes, deprecations), that is a later
  decision, not this change's.
