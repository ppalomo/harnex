# decision-model Specification

## Purpose

How the harness answers a typed decision question through a swappable backend — a real
model over OpenRouter or a person asked directly — so that no command ever needs to know
which one is behind `decide()`, and never blocks on one that cannot answer.

## Requirements

### Requirement: One interface, two backends, chosen by the project

The harness SHALL expose one decision interface, `decide(question_id, state)`, with
exactly two backends: `mock`, which never contacts a network, and `jev`, which calls
OpenRouter's Decisions endpoint. The backend used SHALL be the one recorded at the
project's `.harnex.yml` `decision_model` key, and the interface SHALL behave identically
to every caller regardless of which backend answers.

Before treating `OPENROUTER_API_KEY` as absent, the `jev` backend SHALL look for it in
two places, in order: the process environment first, then an `OPENROUTER_API_KEY=` line
in a `.env` file at the project root (the same project the interface's `--project`
already names). The process environment SHALL always win when both carry a value. The
`.env` file SHALL be read as flat `KEY=VALUE` lines only — no shell expansion, no
`export` prefix, no interpolation — and a `.env` that does not exist, cannot be read, or
does not declare the key SHALL be treated exactly as if it were absent.

#### Scenario: A project with no backend chosen

- **WHEN** a project's `.harnex.yml` does not record `decision_model`
- **THEN** the interface behaves as `mock`

#### Scenario: A project with `jev` chosen and no key

- **WHEN** `decision_model` is `jev`, the `OPENROUTER_API_KEY` environment variable is not
  set, and the project's `.env` does not declare it either (or no `.env` exists)
- **THEN** the interface never attempts a network call and answers as it would on any
  other `jev` failure

#### Scenario: The key comes from the project's `.env`

- **WHEN** `decision_model` is `jev`, the `OPENROUTER_API_KEY` environment variable is not
  set, and the project's `.env` declares `OPENROUTER_API_KEY=<value>`
- **THEN** the interface uses that value to call OpenRouter, exactly as if it had been
  exported

#### Scenario: Both the environment and `.env` carry a value

- **WHEN** `decision_model` is `jev`, the `OPENROUTER_API_KEY` environment variable is
  set, and the project's `.env` also declares the key with a different value
- **THEN** the interface uses the environment variable's value and never reads the
  `.env` file's value for the key

### Requirement: Every outcome is one of two shapes

The interface SHALL return either a resolved decision — the chosen option, the
probability of every option, and a confidence — or an unresolved one carrying a
human-readable prompt for the option's caller to put to the person. It SHALL NOT raise an
error to its caller for any backend failure, and SHALL NOT block waiting for a person to
answer.

#### Scenario: `jev` answers above the question's threshold

- **WHEN** the `jev` backend returns a probability for the highest option at or above the
  question's own threshold
- **THEN** the interface returns a resolved decision naming that option

#### Scenario: `jev` answers below the question's threshold

- **WHEN** the `jev` backend returns an answer whose highest probability is below the
  question's own threshold
- **THEN** the interface returns an unresolved outcome, not the low-confidence option

#### Scenario: `jev` is unreachable

- **WHEN** the `jev` backend cannot be reached, times out, or returns a response the
  interface cannot parse, after one retry
- **THEN** the interface returns an unresolved outcome, the same shape as a `mock` answer

#### Scenario: The backend is `mock`

- **WHEN** the project's backend is `mock`
- **THEN** the interface always returns an unresolved outcome carrying the question's
  prompt, and never contacts a network

### Requirement: A retriable failure is retried once, within a fixed budget

Before returning an unresolved outcome for a network failure, the `jev` backend SHALL
retry exactly once, and the whole attempt — both tries — SHALL complete within a fixed
time budget stated by the interface, never left to the network's own timeout.

#### Scenario: The first attempt times out, the second succeeds

- **WHEN** the first request to OpenRouter times out and the retried request returns a
  valid answer within the budget
- **THEN** the interface returns that answer, resolved or not, on the rule of the
  probabilities it carries

#### Scenario: Both attempts fail

- **WHEN** both the first request and its retry fail within the time budget
- **THEN** the interface returns an unresolved outcome and the elapsed time does not
  exceed the stated budget

### Requirement: Each question is defined once, outside the interface's code

A decision question's type, its options or levels, the state fields it declares, and its
own rule on the returned probabilities SHALL be recorded in one file the interface reads,
not written into the interface's own code. Adding a question SHALL NOT require changing
`decide()`'s implementation.

#### Scenario: A new question is added

- **WHEN** a new question file is added under the questions directory with a type the
  interface already supports
- **THEN** the interface can answer it without any change to its own code

### Requirement: `state` is passed as a keyed object, never as a bare positional list

Whatever state a caller passes to a question SHALL be a JSON object keyed by the field
names the question declares. The interface SHALL NOT accept, and a question file SHALL
NOT declare, a state field that is a list referenced by its position.

#### Scenario: A caller passes a list of candidates

- **WHEN** a question's state includes a list of several items the model must judge among
- **THEN** each item is keyed by an identifier or embedded in the question's own text,
  never referenced by its index in the list

### Requirement: Every call is recorded, whether or not it resolves

Every call to `decide()` SHALL append one line to the project's decision journal, naming
the question, a hash of the state, the probabilities returned (if any), the confidence (if
any), the outcome, the rule that produced it, and the backend that answered — whether or
not the call resolved. The journal line SHALL NOT include the `OPENROUTER_API_KEY` value,
regardless of whether it came from the environment or from the project's `.env`.

#### Scenario: An unresolved call is still journaled

- **WHEN** the backend cannot answer and the interface returns an unresolved outcome
- **THEN** one journal line is still appended, recording that no decision resolved and why

#### Scenario: A call resolved with a key read from `.env`

- **WHEN** a call resolves using a key the interface read from the project's `.env`
- **THEN** the journal line records the call exactly as it would for a key read from the
  environment, and carries no trace of the key's value or its source

### Requirement: The screen line names advice apart from a binding decision

Before a caller acts on an interface's outcome, or asks the person because it did not
resolve, it SHALL print one line naming the phase, the backend and model or the fact that
a person is being asked, and the confidence if any. A caller whose phase cannot act on the
outcome — because it runs somewhere the tool or model cannot be switched — SHALL print the
line as advice, not as a decision taken.

#### Scenario: A phase that cannot switch its own tool

- **WHEN** the calling phase runs in a context where the interface's outcome cannot
  actually change which tool or model is running
- **THEN** the printed line says the outcome is advice

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
