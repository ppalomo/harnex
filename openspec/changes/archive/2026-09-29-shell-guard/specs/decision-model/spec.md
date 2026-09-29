## ADDED Requirements

### Requirement: A `score`-typed question resolves through one threshold per option

For a question of type `score`, the interface SHALL build a request whose `criteria`
declares every option the question file's `option.*` fields name, and SHALL read the
response as one independent probability per option — not a distribution that sums to one.
The question file SHALL declare a `rule_threshold.<option-name>` for every option that can
resolve the question on its own, and SHALL NOT declare the flat `rule_threshold` or
`rule_threshold_low` fields, which belong to `choice` and `noul` only.

Options are checked in the order the question file declares them. The interface SHALL
resolve to the first option, in that order, whose own probability is at or above its
`rule_threshold.<option-name>`, carrying every option's probability. When no option's
probability reaches its own threshold, the interface SHALL return an unresolved outcome
carrying every option's probability, the same shape as any other unresolved call.

#### Scenario: One option crosses its own threshold

- **WHEN** a `score` question's response gives one declared option a probability at or
  above that option's own `rule_threshold.<name>`, and no earlier-declared option does
- **THEN** the interface returns a resolved decision of that option, carrying every
  option's probability

#### Scenario: Two options both cross their own thresholds

- **WHEN** more than one declared option's probability is at or above its own threshold
- **THEN** the interface resolves to whichever of them is declared earliest in the
  question file, not the one with the higher probability

#### Scenario: No option crosses its own threshold

- **WHEN** every declared option's probability is below its own `rule_threshold.<name>`
- **THEN** the interface returns an unresolved outcome, carrying every option's
  probability and the question's prompt

#### Scenario: A question file declares a `score` type without a per-option threshold

- **WHEN** a question file's type is `score` and no `option.*` it declares has a matching
  `rule_threshold.<name>`
- **THEN** the question fails to load, naming the file

#### Scenario: A question file declares a `score` type with the flat threshold fields

- **WHEN** a question file's type is `score` and it declares `rule_threshold` or
  `rule_threshold_low`
- **THEN** the question fails to load, naming the file and which field it does not hold
