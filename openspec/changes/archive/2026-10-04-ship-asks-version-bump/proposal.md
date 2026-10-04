**Pillar:** 3 · Orchestration (the `ship` skill and a new script beside `ship_gate.py` in
`plugin/scripts/`) — no `plugin/control/` change, since the tag itself is never cut or
pushed by `ship`, only its command printed back to the person; the version-bump question
and the commit it lands in already fall under `ship`'s own existing guard patterns (`git
commit`, already asked about).

**Phase:** `docs/PLAN.md` has no scheduled slot for this; the nearest named phase,
`C6 · update and release`, explicitly left "cutting the tag is the owner's own call in
`ship`, not `apply`'s" as its own owed item (§C6's exit notes) rather than build it. This
change is the next phase after `C7 · a personal, local-only setup` — call it
**`C8 · ship asks the version bump`**. Exit criterion: running `/harnex:ship` on a change
that touches a project's own releasable plugin manifest offers the version-bump choice
inside the existing confirmation prompt; running it on a change that does not touches
nothing about version and asks nothing new.

## Why

`claude plugin update` silently no-ops against an unversioned plugin — recorded live in
`docs/PLAN.md` (`C3`'s own notes) as the concrete evidence for why real versioning matters
— and today bumping this repository's two manifests (`plugin/.claude-plugin/plugin.json`,
`.claude-plugin/marketplace.json`) is a step a person has to remember to do by hand, listed
in `docs/releasing.md`, separately from every ordinary `/harnex:ship` run. In practice it
never happens: this repository has gone through fourteen-plus shipped commits since the
plugin's manifest was first written, and the version field has never moved past `0.1.0`.
`/harnex:ship` already asks the person one confirmation question before its first commit;
this change folds the version decision into that same moment, for any project whose own
`ship` run is already touching a releasable plugin manifest — not only this repository's.

## What Changes

- `/harnex:ship`'s gated-path confirmation (today: one yes/no question before committing)
  becomes two questions asked together, in the same turn, but only when the project being
  shipped carries a releasable plugin manifest: a `plugin.json` plus an agreeing
  marketplace entry, the same shape `claude plugin tag --dry-run` already knows how to
  find and validate. A project with no such manifest is asked nothing new — the existing
  single yes/no question is unchanged for it.
- The added question explains what `X.Y.Z` means and offers four options, each showing the
  concrete resulting version computed from the manifest's current one: no bump, patch
  (`X.Y.Z+1`), minor (`X.Y+1.0`), major (`X+1.0.0`).
- A chosen bump is written to both manifests by a small deterministic script (beside
  `ship_gate.py` in `plugin/scripts/`, not left to the model to hand-edit JSON) and folded
  into the same commit `ship` was already about to make (section 2.3 of the skill), before
  the push and the pull request.
- `/harnex:ship` never runs `git tag` or pushes one, and never touches
  `.github/workflows/release.yml` or its `v*.*.*` trigger pattern — it cannot: `ship`
  pushes a branch and opens a pull request, it never merges to `main`, and the tag has to
  name a commit that is actually on `main`. When a bump happened, `ship`'s final report
  (section 4) adds a reminder naming the exact commands from `docs/releasing.md`
  (`git tag vX.Y.Z`, `git push origin vX.Y.Z`) for the person to run once the pull request
  is merged — the existing `vX.Y.Z` convention, not `claude plugin tag`'s own
  `{name}--v{version}` naming, which would not match the release workflow's trigger.
- `docs/releasing.md` is updated to say its step 1 (bump both manifests) is normally
  already done by `/harnex:ship`'s prompt, and is only a manual step for a release cut
  without going through `ship`.

## Non-Goals

- No automatic detection of *which* bump (patch/minor/major) a change deserves from its
  commits or its diff — the person always chooses, explicitly, every time.
- No change to `claude plugin tag`, to `.github/workflows/release.yml`'s trigger pattern,
  or to the `vX.Y.Z` tag-naming convention.
- `/harnex:ship` still never cuts, annotates, or pushes a git tag, and never opens a GitHub
  release — that remains entirely the person's own manual step, after the pull request
  merges.
- No new `.harnex.yml` key and no opt-in `features` entry: whether the question appears is
  decided structurally, by whether the project's own tree carries a releasable plugin
  manifest `ship` can find and validate — not by a recorded project choice.
- No change to the direct path (section 3, a branch with no `openspec/` change behind it)
  beyond the same manifest-detection check — a hand-edited or `/harnex:flash`-made branch
  that happens to touch a plugin manifest gets the same question, nothing more.
- No change to `/harnex:apply`, `/harnex:verify`, or the verifier's own review.

## Capabilities

### Modified Capabilities
- `verify-and-ship-commands`: `ship`'s commit-confirmation requirement gains the
  version-bump question (asked only when a releasable plugin manifest is present),
  the manifest write folded into the existing pre-push commit, and the post-ship
  tag/push reminder.

## Impact

- `plugin/skills/ship/SKILL.md` — sections 2.2 (the combined question), 2.3 (the manifest
  write lands in the same commit), and 4 (the tag/push reminder); section 3's direct path
  gets the same detection check.
- A new script in `plugin/scripts/` (beside `ship_gate.py`) that finds a project's plugin
  manifest and its marketplace entry (reusing the same shape `claude plugin tag --dry-run`
  already validates), computes the three candidate `X.Y.Z` values from the manifest's
  current version, and writes a chosen bump to both files.
- `plugin/orchestration/README.md` — the new script's one-line entry, alongside
  `ship_gate.py`'s.
- `docs/releasing.md` — steps 1 through 3 (bump both manifests, run the check command,
  commit the bump) reframed as normally already done by `ship`'s own commit; the
  document's remaining steps (tag, push) are unchanged.
- `docs/PLAN.md` — a new `C8` roadmap entry, folded into this change's own last task
  (`tasks.md` §4), the same way `personal-local-setup` added its own `C7` entry as a
  task rather than a follow-up.
