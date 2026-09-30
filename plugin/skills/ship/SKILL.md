---
name: ship
description: Commit a verified change, open its pull request, then archive it and sync its specs after the person's explicit yes. Use when the person wants to ship a verified change.
---

# Shipping a change

You turn a fresh, clean `verify` review into the change's commit and pull request, then
archive the change. The gate is authoritative: do not begin any write or publication step
until it says the exact working tree is safe to ship and the person has explicitly said yes.

## 1. Check the fresh `verify` review before doing anything else

Name the change from the current branch:

```
git branch --show-current
```

Use that branch name as `<change-name>`. Confirm `openspec/changes/<change-name>/` exists;
if it does not, say so plainly and stop rather than guessing the change path. Run the gate,
capturing its stdout, stderr, and exit status separately because a refusal exits non-zero
while still printing its result:

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

## 2. Show advisory findings and ask once for the person's explicit yes

Only when `"decision": "go"`, show every finding in `findings` unchanged. These are
advisory findings: a blocking finding would have made the gate refuse.

Then ask the person once whether to proceed with committing, pushing, opening the pull
request, archiving the change, and syncing its specs. Make clear that those advisory
findings are part of the decision. Wait for an explicit yes.

If the person says no, or does not give an explicit yes, stop. Do not commit, push, open a
pull request, archive the change, or sync specs. Do not ask again.

## 3. Commit the change

Before attempting a commit, check whether the tree has anything to commit:

```
git status --porcelain=v1 --untracked-files=all
```

If its output is empty, the tree is already clean relative to `HEAD`. This is normal when
re-running after a pull-request failure: skip the commit step and proceed to step 4. If it
has output, continue with the commit.

Read `openspec/changes/<change-name>/proposal.md` and use it to derive a conventional,
English commit message. Check the repository's recent style before committing:

```
git log --oneline -5
```

Commit with the resulting message:

```
git add -A
git commit -m "<conventional English message>"
```

Do not add an AI author or co-author line to the commit message. If this commit fails while
there is something to commit, report the failure plainly and stop; do not push, open a pull
request, archive, or sync specs.

## 4. Push the branch

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

## 5. Open the pull request with `gh`

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

## 6. Archive the change and sync its specs

Only after `gh pr create` succeeds, run:

```
openspec archive <change-name> --yes --json
```

This command archives the change and, by default, updates the main specs from its delta
specs; do not use `--skip-specs`. If it fails, report the archive-and-spec-sync failure
plainly. The commit, push, and pull request already happened and stand.

## 7. Finish

Report success plainly: the commit was made, the branch was pushed, the pull request was
opened with the URL from `gh`, the change was archived, and its specs were synced.

## What this skill never does

- Commit without the person's explicit yes.
- Proceed past a `gh` failure.
- Ask for yes twice.
- Run `openspec archive` before the person's yes.
