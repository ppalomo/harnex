---
name: ship
description: Commit what is pending on this branch, open its pull request, and — when the branch has its own openspec/ change — archive it and sync its specs, all after the person's explicit yes. Use when the person wants to ship a verified change, or to publish whatever a /harnex:flash or a hand-made edit left in the working tree.
---

# Shipping a change

You turn what is sitting on this branch into a commit and a pull request. Two shapes reach
you here, and step 1 decides which:

- **A change with its own `openspec/` artifacts** (`propose` → `apply` → `verify` ran) —
  the gated path, section 2 below. The gate is authoritative: do not begin any write or
  publication step until it says the exact working tree is safe to ship and the person has
  explicitly said yes.
- **A branch with no `openspec/` change behind it** — what `/harnex:flash` or an ordinary
  hand-edit leaves — the direct path, section 3 below. There is no proposal to read a
  title or description from, and nothing for `/harnex:verify` to have gated, so there is
  nothing to check before asking; the diff itself is what you commit, push, and describe.

## 1. Name the change, and decide which path applies

Name the change from the current branch:

```
git branch --show-current
```

Use that branch name as `<change-name>`. Read the project's recorded choices
(`.harnex/config.yml` if it exists — `local` visibility — otherwise `.harnex.yml`); under
`local` visibility, resolve the store named by the recorded `store_id`
(`openspec store list --json`, matched by `id`). Check whether the change's own directory
exists — `openspec/changes/<change-name>/` under the project (`shared` visibility) or under
that store's own root (`local`).

- If it exists, continue with **section 2, the gated path**.
- If it does not, continue with **section 3, the direct path** — this is not an error; most
  branches made by `/harnex:flash`, or by hand, never had one.

## 2. The gated path: a change with its own `openspec/` artifacts

### 2.1 Check the fresh `verify` review before doing anything else

Run the gate, capturing its stdout, stderr, and exit status separately because a refusal
exits non-zero while still printing its result:

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/ship_gate.py" check --project . --change <change-name>
```

Parse stdout as its one JSON object. It has `decision`, `reason`, and `findings`.

- If `"decision": "refuse"` and the reason is `"no run found"`, tell the person no
  fresh `/harnex:verify` run exists for this change and to run `/harnex:verify` first.
- If the reason is `"stale fingerprint"`, tell the person the tree changed since its last
  review and to run `/harnex:verify` again.
- If the reason is `"a blocking finding"`, show every blocking finding from `findings`
  unchanged and tell the person that the change cannot ship until those findings are
  resolved and `/harnex:verify` has run again.
- If the reason is `"an unreadable review record"`, tell the person the last `/harnex:verify`
  run's own record is missing a required field, malformed, or points at a `base_ref` that no
  longer resolves, and to run `/harnex:verify` again to produce a fresh, valid one.

For every refusal, stop. Do not commit, push, open a pull request, archive the change, or
sync specs. If the command fails without a parseable JSON result, report its stdout and
stderr plainly and stop rather than guessing whether the change is safe.

Only once the gate's decision is `"go"`, also run the version-bump detector, capturing its
stdout:

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/version_bump.py" detect --project .
```

Parse stdout as its one JSON object and note whether its `found` field is `true` or
`false` — section 2.2 uses it when framing the confirmation ask below.

### 2.2 Show advisory findings and ask once for the person's explicit yes

Only when `"decision": "go"`, show every finding in `findings` unchanged. These are
advisory findings: a blocking finding would have made the gate refuse.

Then ask the person once whether to proceed with committing, pushing, opening the pull
request, archiving the change, and syncing its specs. Make clear that those advisory
findings are part of the decision.

If the version-bump detector run in 2.1 reported `"found": true`, fold the version-bump
question into this same ask — one ask, not two. Briefly explain what the three numbers in
a version `X.Y.Z` mean (major, minor, patch), then offer four choices, each stated with
the exact resulting version from that `detect` call's own `candidates`:

- no bump — stay on the current version (`current_version`)
- patch (`<current_version> -> <candidates.patch>`)
- minor (`<current_version> -> <candidates.minor>`)
- major (`<current_version> -> <candidates.major>`)

Make explicit that declining to ship means nothing happens at all, including no version
bump, whatever was chosen for the version question. If `detect` reported
`"found": false`, the ask is unchanged from today: a single yes/no question, with nothing
about a version in it.

Wait for an explicit yes.

If the person says no, or does not give an explicit yes, stop. Do not commit, push, open a
pull request, archive the change, or sync specs. Do not ask again.

### 2.3 Commit the change

Before attempting a commit, check whether the tree has anything to commit:

```
git status --porcelain=v1 --untracked-files=all
```

If its output is empty, the tree is already clean relative to `HEAD`. This is normal when
re-running after a pull-request failure: skip the commit step and proceed to 2.4. If it has
output, continue with the commit.

Read `proposal.md` (the project's own `openspec/changes/<change-name>/` under `shared`
visibility, the store's under `local`) and use it to derive a conventional, English commit
message. Check the repository's recent style before committing:

```
git log --oneline -5
```

If the version-bump detector in 2.1 reported `"found": true` and the person chose patch,
minor, or major in 2.2's combined ask, run the bump before staging anything:

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/version_bump.py" bump --project . --level <level>
```

substituting the chosen level for `<level>`. This writes the manifest files the detector
found; they are picked up by the `git add -A` below. If it exits 1 with a JSON error —
its own re-detection no longer finds the same, single, agreeing manifest, because the tree
moved since 2.1's `detect` call — report that plainly and stop; do not commit. If the
person chose no bump, or `detect` reported `"found": false` in 2.1, skip this step
entirely: do not run `bump`.

Commit with the resulting message:

```
git add -A
git commit -m "<conventional English message>"
```

Do not add an AI author or co-author line to the commit message. If this commit fails while
there is something to commit, report the failure plainly and stop; do not push, open a pull
request, archive, or sync specs.

### 2.4 Push the branch

Check whether the branch already has an upstream:

```
git rev-parse --abbrev-ref --symbolic-full-name @{u}
```

If it has one, push normally:

```
git push
```

If it has none, run:

```
git push -u origin <change-name>
```

If the push fails, report the failure plainly and stop. Do not open a pull request, archive
the change, or sync specs.

### 2.5 Open the pull request with `gh`

Read the same proposal again and derive the pull-request title and body from it. Put the
proposal-derived body in a temporary file. Do not add an AI author or co-author line to the
pull request. Use the installed, authenticated `gh` CLI:

```
gh pr create --title "<proposal-derived-title>" --body-file <proposal-derived-body-file>
```

Keep the URL that `gh pr create` prints.

If `gh` is missing, unauthenticated, or `gh pr create` otherwise fails, report that the
pull-request step failed and why. The commit and push already happened and stand; do not
undo them, archive the change, or sync specs. Tell the person to resolve `gh` and re-run
`/harnex:ship`; the existing commit and push will not be duplicated. Do not invent separate
idempotent re-run logic.

### 2.6 Archive the change and sync its specs

Only after `gh pr create` succeeds, run:

```
openspec archive <change-name> --yes --json
```

Add `--store <store_id>` under `local` visibility (section 1's resolved id) — the change
archives into that store's own `openspec/specs/`, never into this project's. This command
archives the change and, by default, updates the main specs from its delta specs; do not
use `--skip-specs`. If it fails, report the archive-and-spec-sync failure plainly. The
commit, push, and pull request already happened and stand.

Then go to section 4.

## 3. The direct path: no `openspec/` change behind this branch

### 3.1 Look at what is pending, and ask once for the person's explicit yes

```
git status --porcelain=v1 --untracked-files=all
git diff --stat
```

If both are empty and the branch has nothing unpushed, tell the person there is nothing to
ship and stop — this is not a refusal, just nothing to do.

Otherwise, read the actual diff (`git diff`, plus the content of any untracked file) to
understand what changed — there is no `proposal.md` to read instead — and check the
repository's own recent style:

```
git log --oneline -5
```

Also run the version-bump detector, capturing its stdout:

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/version_bump.py" detect --project .
```

Parse stdout as its one JSON object and note whether its `found` field is `true` or
`false` — it is part of what the confirmation ask below covers.

From that, derive a conventional, English commit message, and a pull-request title and
body that say what changed and why, the same way `/harnex:flash` would have. Show the
person the pending diff and the message you derived, and ask once, explicitly, whether to
commit, push, and open the pull request.

If the version-bump detector run above reported `"found": true`, fold the version-bump
question into this same ask — one ask, not two. Briefly explain what the three numbers in
a version `X.Y.Z` mean (major, minor, patch), then offer four choices, each stated with
the exact resulting version from that `detect` call's own `candidates`:

- no bump — stay on the current version (`current_version`)
- patch (`<current_version> -> <candidates.patch>`)
- minor (`<current_version> -> <candidates.minor>`)
- major (`<current_version> -> <candidates.major>`)

Make explicit that declining to ship means nothing happens at all, including no version
bump, whatever was chosen for the version question. If `detect` reported
`"found": false`, the ask is unchanged from today: a single yes/no question, with nothing
about a version in it.

Wait for a clear yes.

If the person says no, or does not give a clear yes, stop. Do not commit, push, or open a
pull request. Do not ask again.

### 3.2 Commit the change

If `git status --porcelain=v1 --untracked-files=all` came back empty in 3.1, the tree is
already clean relative to `HEAD` — this is normal when re-running after a pull-request
failure — skip straight to 3.3. Otherwise, if the version-bump detector in 3.1 reported
`"found": true` and the person chose patch, minor, or major in that same ask, run the bump
before staging anything:

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/version_bump.py" bump --project . --level <level>
```

substituting the chosen level for `<level>`. This writes the manifest files the detector
found; they are picked up by the `git add -A` below. If it exits 1 with a JSON error —
its own re-detection no longer finds the same, single, agreeing manifest, because the tree
moved since 3.1's `detect` call — report that plainly and stop; do not commit. If the
person chose no bump, or `detect` reported `"found": false` in 3.1, skip this step
entirely: do not run `bump`.

Commit with the message derived in 3.1:

```
git add -A
git commit -m "<conventional English message>"
```

Do not add an AI author or co-author line to the commit message. If this commit fails while
there is something to commit, report the failure plainly and stop; do not push or open a
pull request.

### 3.3 Push the branch

Check whether the branch already has an upstream:

```
git rev-parse --abbrev-ref --symbolic-full-name @{u}
```

If it has one, push normally (`git push`); if it has none, run
`git push -u origin <change-name>`. If the push fails, report the failure plainly and stop.
Do not open a pull request.

### 3.4 Open the pull request with `gh`

Put the title and body derived in 3.1 in a temporary file for the body, with no AI author or
co-author line in either, and use the installed, authenticated `gh` CLI:

```
gh pr create --title "<derived title>" --body-file <derived-body-file>
```

Keep the URL that `gh pr create` prints. If `gh` is missing, unauthenticated, or
`gh pr create` otherwise fails, report that the pull-request step failed and why. The
commit and push already happened and stand; do not undo them. Tell the person to resolve
`gh` and re-run `/harnex:ship`; the existing commit and push will not be duplicated.

There is nothing to archive and no specs to sync for this path — there was never a change
under `openspec/` to begin with. Go to section 4.

## 4. Finish

Report success plainly: the commit was made, the branch was pushed, and the pull request
was opened with the URL from `gh`. For the gated path only, add that the change was
archived and its specs were synced.

If a version bump was made in 2.3 or 3.2 — the person chose patch, minor, or major and
`bump` succeeded — also state the exact version it bumped to, and the exact commands the
person should run once this pull request merges:

```
git tag vX.Y.Z
git push origin vX.Y.Z
```

substituting the new version for `X.Y.Z`. Make clear that `ship` does not run these
itself — it only states them — because `ship` never merges the pull request, so the tag
has to wait until the person has done that themselves.

## What this skill never does

- Commit without the person's explicit yes, on either path.
- Proceed past a `gh` failure.
- Ask for yes twice.
- Run `openspec archive` before the person's yes, or for a change that never had an
  `openspec/` directory to begin with.
- Invent an `openspec/` change to make the direct path look like the gated one.
- Cut or push a release tag, or open a GitHub release, on its own — it never merges the
  pull request it opens, so it cannot confirm the tag would name a commit actually on
  `main`; it only states the commands in its final report.
