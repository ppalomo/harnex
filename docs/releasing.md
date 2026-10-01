# Releasing

A release is a git tag named `vX.Y.Z`. There is no other source of truth: the tag is cut
by a person, by hand, never inferred from a commit by CI (`update-and-release`'s
design.md, D4, Open Question resolved). CI reacts to the pushed tag; it never creates one.

## Steps

1. **Bump both manifests to the same version.** Edit the `version` field in each of:
   - `plugin/.claude-plugin/plugin.json` (`version`)
   - `.claude-plugin/marketplace.json` (`plugins[0].version`, the `"harnex"` entry under
     `plugins`)

   Both must end up holding the identical new value, e.g. `0.2.0`.

2. **Run the check command and confirm it passes**, including the pytest check that fails
   if the two manifests disagree:

   ```bash
   uv run --with pytest pytest
   ```

3. **Commit the version bump:**

   ```bash
   git commit -am "chore: release vX.Y.Z"
   ```

4. **Tag the commit**, with the tag name matching the manifests' new version exactly:

   ```bash
   git tag vX.Y.Z
   ```

5. **Push the commit and the tag:**

   ```bash
   git push --follow-tags
   ```

   (`--follow-tags` pushes the current branch and any annotated-or-not tag reachable from
   it that isn't on the remote yet; `git push && git push origin vX.Y.Z` works the same if
   you prefer to push them as two separate steps.)

Pushing the tag is what the release workflow reacts to — it re-runs the same checks
against the tagged commit and fails if the tag's own `X.Y.Z` does not match what the
manifests declare.
