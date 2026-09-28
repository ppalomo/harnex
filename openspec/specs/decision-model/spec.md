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

#### Scenario: A project with no backend chosen

- **WHEN** a project's `.harnex.yml` does not record `decision_model`
- **THEN** the interface behaves as `mock`

#### Scenario: A project with `jev` chosen and no key

- **WHEN** `decision_model` is `jev` and the `OPENROUTER_API_KEY` environment variable is
  not set
- **THEN** the interface never attempts a network call and answers as it would on any
  other `jev` failure

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
not the call resolved.

#### Scenario: An unresolved call is still journaled

- **WHEN** the backend cannot answer and the interface returns an unresolved outcome
- **THEN** one journal line is still appended, recording that no decision resolved and why

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
