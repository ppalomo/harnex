## MODIFIED Requirements

### Requirement: A `score`-typed question resolves through one threshold per option

For a question of type `score`, the interface SHALL build a request whose `criteria` is a
JSON **array** of the option names the question file's `option.*` fields declare, as plain
strings, in the order the question file declares them — not a JSON object keyed by option
name, which the live API rejects for this question type (unlike `choice` and `noul`,
whose object-shaped `criteria` the live API does accept), and not an array of richer
`{name, description}` objects either: the live API treats each array item as an opaque
label it echoes back verbatim in the response's `legend`, so a plain name is both
sufficient and the most direct match against the question file's own option names.

The interface SHALL read the response's `probabilities` as keyed by a stringified index,
not by option name, and SHALL map each index back to its option name by matching the
response's own `legend` value at that index against the question file's declared option
names before applying any threshold — the response carries no other way to tell which
probability belongs to which option. The response's probabilities for a `score` question
SHALL be treated as summing to 1 across every declared option, not as independent
per-option probabilities; this does not change how the interface resolves a decision,
since it already checks each option's own probability against its own threshold
independently of what the other options carry.

The question file SHALL declare a `rule_threshold.<option-name>` for every option that can
resolve the question on its own, and SHALL NOT declare the flat `rule_threshold` or
`rule_threshold_low` fields, which belong to `choice` and `noul` only.

Options are checked in the order the question file declares them. The interface SHALL
resolve to the first option, in that order, whose own probability is at or above its
`rule_threshold.<option-name>`, carrying every option's probability, keyed by option name.
When no option's probability reaches its own threshold, the interface SHALL return an
unresolved outcome carrying every option's probability, keyed by option name, the same
shape as any other unresolved call.

#### Scenario: The request's `criteria` is built as an array of plain option names

- **WHEN** the interface builds a request for a `score` question
- **THEN** the request's `criteria` field is a JSON array of strings, one per declared
  option's own name, in declaration order — no description text, no nested object

#### Scenario: A response's probabilities are mapped through its own legend

- **WHEN** a `score` response returns `probabilities` keyed by stringified index (for
  example `{"0": 0.1, "1": 0.9}`) alongside a `legend` mapping each index to the criterion
  sent at that position (for example `{"0": "destructive", "1": "read_only"}`)
- **THEN** the interface matches each index's `legend` value against the question file's
  declared option names before checking any `rule_threshold.<option-name>`, and every
  probability the interface returns or journals afterward is keyed by option name, never
  by index

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
