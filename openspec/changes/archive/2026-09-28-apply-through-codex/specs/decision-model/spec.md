## ADDED Requirements

### Requirement: `decide_many` answers several distinct questions sharing one state, in a single call

The interface SHALL expose `decide_many(questions: list[(Question, state)]) ->
list[Decision]` — a list of already-loaded questions paired with their own state, mirroring
`decide()`'s own `(question, state)` pair — sending every distinct question in one request
when the backend is `jev`, sharing one combined state object across them. It SHALL NOT be
used to ask the same question id more than once in a single call. `decide()` SHALL be a
one-question convenience over `decide_many()`, and every existing caller of `decide()`
SHALL see no change in behaviour.

#### Scenario: The same question, asked once per item, batched into one call

- **WHEN** a caller builds several distinctly-keyed questions of the same type — the same
  `id` would collide, so each carries its own id and its own self-contained instructions —
  and asks them together through `decide_many`
- **THEN** one request is sent, and the interface returns one outcome per question, each
  shaped exactly as a `decide()` call for that question would have returned it

#### Scenario: The backend is `mock`

- **WHEN** `decide_many` is called with the project's backend set to `mock`
- **THEN** every question in the call returns its own unresolved outcome, carrying its
  own prompt, with no network contacted

#### Scenario: One request answers, the batch does not change any single answer's shape

- **WHEN** `jev` answers a batched call
- **THEN** each question's outcome in the returned list is indistinguishable in shape
  from what a single-question `decide()` call for that question would have returned

### Requirement: A `noul`-typed question resolves through two thresholds

For a question of type `noul`, the interface SHALL build a request whose `criteria`
declares exactly two options, `true` and `false`, and SHALL read the response's single
`noul` probability, `p`. The `false` probability the interface reports SHALL be `1 - p`,
since the response itself carries no second number. It SHALL resolve to `true` when `p` is
at or above the question's `rule_threshold`, resolve to `false` when `p` is at or below the
question's `rule_threshold_low`, and SHALL return an unresolved outcome, carrying both
`{"true": p, "false": 1 - p}`, when `p` falls strictly between the two.

#### Scenario: Above the upper threshold

- **WHEN** a `noul` question's probability is at or above `rule_threshold`
- **THEN** the interface returns a resolved decision of `true`

#### Scenario: At or below the lower threshold

- **WHEN** a `noul` question's probability is at or below `rule_threshold_low`
- **THEN** the interface returns a resolved decision of `false`

#### Scenario: Between the two thresholds

- **WHEN** a `noul` question's probability falls strictly between `rule_threshold_low`
  and `rule_threshold`
- **THEN** the interface returns an unresolved outcome carrying the question's prompt,
  the same shape as any other unresolved call

#### Scenario: A question file declares a `noul` type with the wrong options

- **WHEN** a question file's type is `noul` and its declared options are not exactly
  `true` and `false`
- **THEN** the question fails to load, naming the file and what it declared instead
