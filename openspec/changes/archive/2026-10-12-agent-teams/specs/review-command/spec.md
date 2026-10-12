## ADDED Requirements

### Requirement: `/harnex:review` starts every reviewer of the project's teams

After the core reviewer, `/harnex:review` SHALL start, once each, every agent rendered
for the project's chosen profiles whose role's phase is `review`, with the same diff,
and SHALL present each review exactly as returned, labelled with the agent's emoji and name. It
SHALL NOT merge reviews, drop a finding because another agent reported it, or start any
agent more than once per run. A project whose profiles have no team SHALL see exactly
the core reviewer's review, as before. None of these reviews SHALL affect
`/harnex:ship`.

#### Scenario: A project with two review-phase agents

- **WHEN** `/harnex:review` runs in a project whose chosen profile rendered a
  `security-reviewer` and a `migration-reviewer`
- **THEN** the core reviewer's review is shown first, then each of the two agents' reviews
  under its own emoji and `name`, each as returned

#### Scenario: A project without a team

- **WHEN** `/harnex:review` runs in a project whose chosen profiles are all single-file
- **THEN** only the core reviewer runs, exactly as before this capability existed

#### Scenario: A rendered agent is missing from disk

- **WHEN** a `review`-phase agent the recorded profiles would render is not present
  under `.claude/agents/`
- **THEN** `/harnex:review` says so, names `/harnex:update` as the remedy, and finishes
  with the reviews it could obtain
