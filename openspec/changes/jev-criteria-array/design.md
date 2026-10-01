## Context

Two independent defects in two different pillar-owned files, bundled because the second
was found while live-diagnosing the first on this repository and both produce the same
symptom. See `proposal.md` - Why for the motivation and the live evidence (HTTP 400,
TypeSafe's own docs, the guard ignoring `.harnex.yml`).

`decide.py`'s `_question_payload` currently builds the same `{"type", "instructions",
"criteria": dict(question.options)}` shape for all three question types. Live calls
against `https://openrouter.ai/api/alpha/decisions` (model `typesafe/jev-1.13`) confirm
`choice` and `noul` accept that object shape; `score` returns HTTP 400 demanding an array.
TypeSafe's own docs (`docs.typesafe.ai/api.md`, fetched 2026-10-01) confirm the array shape
and the response shape: `probabilities` keyed by stringified index, a `legend` mapping
index to the criterion sent at that position, and the probabilities summing to 1 - not the
independent per-option distribution the current spec and `parse_response` assume.

`guard.py` has no code path that reads `.harnex.yml` at all - confirmed by its absence from
the file. `canary.py` (pillar 5) already solves the identical problem for its own set,
importing `setup.parse_choices` by path and checking `CANARY_SET not in choices.get("sets",
[])`. This design reuses that exact pattern for `guard.py` and the `safety` set.

## Goals / Non-Goals

**Goals:**
- A `score` request matches the live API's contract; `guard.risk` can actually resolve to
  `allow` through a real `jev` call.
- A `score` response parses correctly, mapping `legend` back to option names before any
  threshold check.
- The guard's default list goes inert exactly when `canary.py` would for the `canary`
  set - same file, same failure handling, same precedence between "not configured" and
  "misconfigured."
- Both fixes are covered by tests that do not require a live network call.

**Non-Goals:** see `proposal.md` - Non-Goals. In addition, at the design level: no change
to `classify_segments`'s existing allow/deny/ask precedence logic, or to how a role's
additions combine with the default list once the default list *is* active - only whether
the default list's own classification runs at all.

## Decisions

### D1: Send `criteria` as an array of plain option names, not `{name, description}` objects

Both shapes return HTTP 200 (confirmed live). TypeSafe's own example
(`"criteria": ["Calm", "Frustrated", "Very angry"]`) uses short labels, not full sentences,
and whatever is sent at each index is echoed back verbatim in the response's `legend` -
the API does not require or recognise a `name`/`description` split; it is an opaque label
per level. Sending plain option names (`["destructive", "read_only", "reversible"]`) makes
the response's `legend` values exact, direct matches against `question.options` keys - no
parsing an object back out of `legend`, no coupling to a description's exact wording
surviving a round trip. The question's own `instructions` field (already sent) carries the
one-line framing; the longer per-option description text in `guard-risk.yaml`'s body is
not sent to the model today for `score` any more than it is for the first line of
`choice`/`noul` instructions - this does not reduce the information the model already had
through the options' names and the instructions line.

**Alternative considered:** array of `{name, description}` objects, preserving the
description text. Rejected: it requires `parse_response` to pull `legend[i]["name"]`
instead of `legend[i]` directly, for no measured gain in the one live case tried
(`guard.risk` on an easy command resolved at 0.99 confidence either way); if a harder
residue case ever needs the fuller description, that is a future change to what
`_question_payload` sends, not a reason to carry the extra parsing complexity now.

### D2: Map `legend` to option names by value, not by array position

The response's `probabilities` are keyed by the same stringified index `legend` uses
(`"0"`, `"1"`, ...). Two ways to recover the option name for each probability: trust that
response order matches request order (zip positionally), or look up each index's value in
`legend` and match that value against `question.options`. This design takes the second:
`legend`'s existence in the response is itself a declaration from the API that index
order is not something a caller should assume stays fixed, and matching by value costs
nothing extra once option names are the criteria values sent (D1) - `legend[i] ==
option_name` directly.

### D3: Correct the spec's "not a distribution that sums to one" claim

The current `decision-model` spec text for `score` says the interface reads "one
independent probability per option — not a distribution that sums to one." Live responses
and TypeSafe's docs agree probabilities sum to 1. The resolution logic itself (first
option in declared order whose own probability crosses its own threshold) does not care
either way - it was already written generically enough to be correct under both
assumptions - so this is a pure documentation correction bundled with the fix that
revealed it, not a logic change.

### D4: Gate only `guard.py`'s default-list classification on `safety`, not the whole hook

`classify_segments` already separates `default_patterns` (no `agent_type`) from
`role_patterns` (`agent_type`-scoped). The inertness gate gives
`classify_segments`/`classify_command` a `safety_active: bool` parameter; when `False`,
the default classification short-circuits to `Classification("allow")` instead of calling
`_classify_against_patterns`, and the existing role-combination logic (unchanged) still
lets a role's own deny/ask override that allow. This keeps `builder-never-touches-
protected-paths` (an `agent_type: builder` addition with no tie to any of the six rule
sets - it protects harness state whenever the builder role runs, independent of a
project's own choices) working exactly as it does today, in a project that never chose
`safety` at all.

**Alternative considered:** have `main()`/`_classify_hook_payload` skip calling `guard.py`'s
classification entirely and print `{"permissionDecision": "allow"}` immediately when
`safety` is not chosen. Rejected: that would also suppress role-scoped protections, which
is not what `safety` governs and not what the symptom (`guard.risk` always asking) is
about.

### D5: Fail-safe precedence - missing file vs. unreadable file are different outcomes

Reusing `canary.py`'s own distinction: `.harnex.yml` absent, or present and parseable but
not listing `safety`, makes the default list inert (a project's own, legible choice).
`.harnex.yml` present but unreadable or malformed is an error, not a choice, and per the
existing "The guard never allows on its own error" requirement, an error SHALL leave the
default list active. `_safety_enabled(project)` returns `False` only for the first two
cases and `True` (active) for every read/parse failure, the same shape `canary.py`'s own
`_check` already uses (there, an unreadable file produces a distinct warning message
instead of silent inertness; here, it produces the safe default instead of a default that
looks like a choice no one made).

## Risks / Trade-offs

- [Sending bare option names loses the longer description text for `score` questions] →
  mitigated: the one live case tried resolved at high confidence without it; `guard-
  risk.yaml`'s descriptions remain available to send later if a harder case ever shows the
  gap (D1's alternative, not taken now).
- [A future TypeSafe/OpenRouter contract change breaks this again, unnoticed] → mitigated:
  the new test pins both the request shape and the response-parsing shape against the
  exact live payloads recorded 2026-10-01, so a silent contract drift fails a test instead
  of silently degrading to permanent `ask`, the way this bug did.
- [`_safety_enabled` reads and parses `.harnex.yml` on every single `Bash` call, adding
  filesystem and parse cost to the hook's hot path] → accepted: `canary.py` already pays an
  equivalent cost once per turn; `setup.parse_choices` is a small stdlib-only parser (no
  dependency to resolve, decision 15) and the guard already shells out to `decide.py` on
  every non-allowlisted command today, which dwarfs one local file read.
- [Importing `setup_script` from `guard.py` the same way `canary.py` and `decide.py` do
  adds a third site coupled to `setup.py`'s module shape] → accepted as the existing
  convention; deviating here (a fourth way to read `.harnex.yml`) would be the real
  inconsistency.

## Migration Plan

No data migration. Both fixes change `decide.py` and `guard.py`'s own behavior only;
`.harnex.yml`'s schema, `patterns.yaml`, and `guard-risk.yaml` are unchanged. A project
already running the plugin picks up both fixes the next time its installed copy is
updated (`C6`'s `/harnex:update`, not yet built - today, reinstalling the plugin). No
rollback step beyond reverting the commit; nothing is written to a project at apply time
that would need undoing.

## Open Questions

(none - every question this design needed answered is answered above, live, against the
real API or the real file this repository already carries)
