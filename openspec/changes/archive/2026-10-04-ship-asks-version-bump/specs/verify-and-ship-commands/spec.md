## MODIFIED Requirements

### Requirement: `ship` commits only after the person's explicit yes

`/harnex:ship` SHALL be the first phase allowed to run `git commit`, and SHALL only do so
after asking the person and receiving an explicit yes. A non-blocking finding from the
latest `verify` run SHALL be shown to the person before that yes is asked, so the decision
to proceed is informed, but SHALL NOT be asked twice or silently dropped. When the project
being shipped carries a releasable plugin manifest (see the version-bump requirements
below), the same ask SHALL also carry the version-bump question, in the same turn — never
a second, separate ask — but declining to ship SHALL still mean nothing happens at all,
regardless of what was chosen for the version bump.

#### Scenario: The person declines

- **WHEN** `/harnex:ship` asks for the person's yes and they decline
- **THEN** no commit is made, and no pull request, archive, or spec sync follows — and no
  manifest is bumped, whatever the version-bump question's answer was

#### Scenario: The person agrees

- **WHEN** `/harnex:ship` asks for the person's yes and they agree
- **THEN** it commits, opens a pull request, archives the change, and syncs its deltas into
  `openspec/specs/`, in that order

## ADDED Requirements

### Requirement: `ship` asks about a version bump only when a releasable plugin manifest is present

`/harnex:ship` SHALL check, before its commit-confirmation ask, whether the project being
shipped carries a releasable plugin manifest: a plugin manifest declaring a semantic
version together with an agreeing marketplace catalogue entry, the same shape a plugin
release tag is validated against. Only when that shape is present SHALL the
commit-confirmation ask include the version-bump question, explaining what the manifest's
three version components mean and offering four choices — no bump, patch, minor, major —
each stated together with the concrete version it would produce from the manifest's
current one. A project with no such manifest SHALL be asked nothing about a version; its
existing single yes/no confirmation is unchanged.

#### Scenario: A releasable manifest is present

- **WHEN** `/harnex:ship` runs on a change that touches a project carrying a plugin
  manifest and an agreeing marketplace entry
- **THEN** the confirmation ask includes the four version-bump choices, each showing the
  resulting `X.Y.Z`

#### Scenario: No releasable manifest

- **WHEN** `/harnex:ship` runs on a project with no plugin manifest, or one whose
  marketplace entry disagrees with it
- **THEN** the confirmation ask ships unchanged: a single yes/no question, nothing about a
  version

### Requirement: A chosen version bump lands in the same commit `ship` was already making

When the person agrees to ship and chose patch, minor, or major, `/harnex:ship` SHALL
write the resulting version to both the plugin manifest and its marketplace entry before
making its commit, and SHALL include both files in that same commit — never a separate
one. When the person chose no bump, or there was no releasable manifest to begin with,
`ship` SHALL NOT modify either file.

#### Scenario: A patch bump is chosen

- **WHEN** the person agrees to ship and chooses the patch option
- **THEN** the plugin manifest's version and its marketplace entry's version are both
  updated to the same incremented patch value, and that commit is the one `ship` pushes

#### Scenario: No bump is chosen

- **WHEN** the person agrees to ship and chooses not to bump the version
- **THEN** neither the plugin manifest nor the marketplace entry is modified, and `ship`
  proceeds exactly as it did before this capability existed

### Requirement: `ship` never cuts or pushes the release tag itself

`/harnex:ship` SHALL NOT run `git tag`, SHALL NOT push a tag, and SHALL NOT open a GitHub
release, because it never merges the pull request it opens — a release tag has to name a
commit that is actually on the project's main branch, which `ship` cannot confirm. When a
version bump was made, `ship`'s final report SHALL remind the person of the exact tag and
push commands for the new version, to run once the pull request has been merged. When no
bump was made, the report SHALL say nothing about a tag.

#### Scenario: A bump was made

- **WHEN** `/harnex:ship` finishes a run that included a version bump
- **THEN** its final report states the exact `git tag` and `git push` commands for the new
  version, and does not run either of them

#### Scenario: No bump was made

- **WHEN** `/harnex:ship` finishes a run with no version bump, whether because none was
  offered or because the person chose not to
- **THEN** its final report says nothing about a tag
