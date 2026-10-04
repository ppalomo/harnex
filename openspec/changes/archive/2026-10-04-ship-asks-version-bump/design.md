## Context

See `proposal.md` — Why / What Changes for the motivation and the shape of the change.
This section only covers what the proposal does not: the exact manifest shape `ship`
looks for, and how the version write stays safe.

Today the only place that knows how to relate a plugin manifest to its marketplace entry
is the Claude Code CLI's own `claude plugin tag [path]`, which validates that a
`.claude-plugin/plugin.json` and the marketplace entry referencing it agree before
tagging. It has no `--json` output — only human-formatted text — so this change does not
shell out to it for detection; it reimplements the same, narrow agreement check directly,
reading JSON on both sides, so the result is a stable contract `ship`'s skill text can
branch on. `claude plugin tag` itself stays entirely unused and unchanged by this change;
it remains the command the person runs by hand, from `main`, once a pull request merges.

**Setup/update ownership:** nothing here changes what `/harnex:setup` or `/harnex:update`
write into a project. Those commands render harness-owned templates
(`AGENTS.md`/`CLAUDE.md` pointer lines, `.harnex.yml`, the permission floor, …); a
project's own `plugin.json`/`marketplace.json`, when it has them at all, are project-owned
content already — the same way `ship` already edits a project's other files to build its
commit. This change adds a script the `ship` skill calls, and a few paragraphs to that
skill; it adds nothing to setup's or update's own write plan.

## Goals / Non-Goals

**Goals:**
- A single, dependency-free script that can (a) detect whether a project has exactly one
  plugin manifest with an agreeing marketplace entry, and, if so, the three candidate
  next versions, and (b) write a chosen one into both files atomically, touching only the
  `version` field.
- Keep `ship`'s existing guard-level guarantees (nothing commits or reaches a remote
  without the person's prior yes) exactly as strong as they are today, with no new
  control-pillar surface, because nothing this change adds can run `git commit`,
  `git push`, or `git tag` itself.

**Non-Goals:**
- Detecting a marketplace with more than one plugin entry, or a plugin manifest with no
  enclosing marketplace file at all (a plugin published without a catalogue). Either case
  is treated as "no releasable manifest" — `ship` asks nothing extra, the same as a
  project with no manifest at all. Widening this is a later change, not this one.
- Changing `metadata.version` — the marketplace catalogue's own version, a different field
  from `plugins[N].version` — the entry for the specific plugin being shipped. Only the
  latter is ever written; `docs/releasing.md` already draws this line and this change
  does not redraw it.
- Reproducing `claude plugin tag`'s own validation logic exactly; this change's detection
  only needs to be conservative (never write to a mismatched or ambiguous shape, even if
  that means asking fewer times than `claude plugin tag` itself might accept).

## Decisions

**Detection is reimplemented, not parsed from `claude plugin tag --dry-run`'s text.**
That command's output is human-formatted prose with no `--json` flag and no documented
stability guarantee across CLI versions. Parsing it would make `ship` depend on another
tool's unversioned text contract. Instead, the new script reads the project's root
`.claude-plugin/marketplace.json` directly: if it declares exactly one entry in
`plugins[]`, resolve that entry's `source` to a directory, read
`<source>/.claude-plugin/plugin.json`, and compare `plugin.json`'s `name`/`version`
against the marketplace entry's own `name`/`version`. Anything else — no marketplace
file, zero or more-than-one entries, a `source` that does not resolve, a disagreement —
is reported as "no releasable manifest," never guessed at.

**The script exposes two verbs, matching `ship_gate.py`'s own shape:**
```
uv run plugin/scripts/version_bump.py detect --project <root>
uv run plugin/scripts/version_bump.py bump --project <root> --level patch|minor|major
```
`detect` always exits 0 and prints one JSON object: `{"found": false}`, or
`{"found": true, "plugin_path", "marketplace_path", "name", "current_version",
"candidates": {"patch", "minor", "major"}}` with each candidate the full `X.Y.Z` string.
`bump` re-runs the same detection itself (the tree could have moved between the skill's
`detect` call and the person's answer, however unlikely in one `ship` run) and refuses —
exit 1, a plain JSON error — if it no longer finds the same, single, agreeing manifest;
otherwise it writes the chosen level's candidate version into both files and prints the
old and new version. This mirrors `ship_gate.py check`/`record`'s own split between a
read-only decision verb and a verb that writes.

**The write touches only the `version` string, through a parsed-JSON round trip, not a
text patch.** Python's `json.load` preserves key order, so re-serialising with
`json.dump(..., indent=2)` after changing one value reproduces the file's existing shape
(no `sort_keys`, unlike `ship_gate.record`'s own fact file, which has no human-curated key
order to preserve). The write is atomic — a temporary sibling file, then `os.replace`,
the same pattern `ship_gate.record` already uses — so a crash mid-write never leaves a
half-written manifest.

**`ship`'s skill text gains the question and the two calls; the script never calls `git`
at all.** There is no verb to cut or push a tag. If `ship`'s own skill text were somehow
wrong about when to stop, the only way it could reach a remote is by running `git`
directly — already covered by the existing shell guard and permission floor from `C4`,
unrelated to this change and unweakened by it.

## Guarantees

- **"A manifest is only ever bumped after the person's explicit choice."** Instruction
  only: the skill text asks before calling `bump`. If the skill text were followed
  wrongly, a bump could land in the working tree before any `git commit` — but nothing is
  committed, pushed, or opened as a pull request without the pre-existing, separately
  enforced yes (see next point), so a wrong bump stays a harmless, uncommitted, easily
  reverted file change.
- **"Nothing commits, pushes, or opens a pull request without the person's yes."**
  Unchanged by this change: still enforced the same way it already is, by the permission
  floor and the shell guard (`C4`) on `git commit`/`git push`/`gh pr create` themselves,
  regardless of which phase or skill is running.
- **"`ship` never cuts or pushes the release tag."** Prevention by omission: the new
  script has no code path that runs `git tag` or pushes one, so the skill cannot call it
  for that purpose even by mistake. A direct `git tag`/`git push` run by the skill text
  itself would still have to pass the same shell guard as any other command.

## Risks / Trade-offs

- A hand-edited or unusually shaped `marketplace.json` (a `source` using a key this
  script does not expect, a monorepo with several plugins) is read as "no releasable
  manifest" even when a person would consider it unambiguous → accepted for now (Non-
  Goals); `ship` degrades to exactly today's single yes/no question, never a wrong write.
- `detect` and `bump` run as two separate process invocations inside one `ship` run, so
  the tree could in principle change between them (another process editing the manifest
  mid-run) → `bump` re-validates from disk immediately before writing rather than trusting
  `detect`'s earlier answer.
- The version-bump question adds a small amount of reading to every `ship` run against a
  project that has a releasable manifest, including this repository's own → accepted: it
  is the entire point of the change, and it only appears where a version is actually there
  to bump.

## Open Questions

None — the explore and propose conversations already settled the question shape, the
tag-naming convention, and the manual, post-merge nature of the actual tag/push step.
