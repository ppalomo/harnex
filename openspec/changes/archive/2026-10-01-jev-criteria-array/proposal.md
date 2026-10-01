## Why

Two independent bugs compound into the same symptom: on a project with `jev` chosen, the
shell guard asks about nearly every command, including ones a person would call obviously
safe.

First, `decide.py`'s `score`-typed request never reached the live OpenRouter Decisions API
against a wire contract only its docs described, never a live call (C4's "What it taught
us" already flags that gap for the request side). A live call today returns **HTTP 400**
for every `score` question — `guard.risk`, the shell guard's own residue classifier, is
the only one that exists — because the API requires `criteria` as an array; `decide.py`
sends an object (`dict(question.options)`), the same builder `choice` and `noul` share and
which the live API does accept for those two types (confirmed live, both ways, on this
repository). The effect: `guard.risk` never resolves, so the shell guard (pillar 4) falls
back to `ask` for every command its deterministic allow/deny/ask lists do not already
cover. A second, response-side mismatch sits behind the same bug: a live `score` answer
returns `probabilities` keyed by a stringified index with a separate `legend` mapping
index to option name — not `probabilities` keyed by option name as `parse_response`
assumes, and not an independent per-option distribution either: TypeSafe's own docs
(`docs.typesafe.ai/api.md`) and the live response both show `score` probabilities summing
to 1 across the given criteria, contradicting the decision-model spec's current claim that
they do not — so even a corrected request would still fail to parse, and the spec would
still misdescribe the shape, once the first half is fixed.

Second, and found while diagnosing the first bug on this very repository: `guard.py` never
reads `.harnex.yml` at all, so a project that never chose the `safety` set — or that never
ran `/harnex:setup` — gets the full default deny/ask/residue treatment anyway. This
directly contradicts a decision already recorded in `docs/PLAN.md` (§12.19): "every harnex
hook is inert in a project without `.harnex.yml`, and each acts only when the project
enabled its set or feature." `canary.py` (pillar 5) already implements exactly this
inertness for its own set; the shell guard has no equivalent, so commenting `safety` out of
`sets` — the only lever a project has — currently does nothing.

Both land in the same change because they produce the same complaint from the same
session (every Bash call prompts) and because the second was only found by instrumenting
the first; fixing only one leaves the symptom's other half unexplained.

### Evidence: the live `score` call, recorded 2026-10-01

The broken request (today's `decide.py`, object-shaped `criteria`) against
`https://openrouter.ai/api/alpha/decisions`, model `typesafe/jev-1.13`:

```json
// request body (abbreviated to the score question)
{"questions": {"guard.risk": {"type": "score", "instructions": "What risk does this shell command carry?", "criteria": {"destructive": "...", "read_only": "...", "reversible": "..."}}}}
```
```json
// HTTP 400 response
{"error": {"message": "[{\"expected\":\"array\",\"code\":\"invalid_type\",\"path\":[\"questions\",\"guard.risk\",\"criteria\"],\"message\":\"Invalid input: expected array, received object\"}]", "code": 400}}
```

The corrected request (array of plain option names) and its live response, same
endpoint and model, same question:

```json
// request body (abbreviated), criteria as an array of plain names
{"questions": {"guard.risk": {"type": "score", "instructions": "What risk does this shell command carry?", "criteria": ["destructive", "read_only", "reversible"]}}}
```
```json
// HTTP 200 response, command under judgement: "ls -la"
{"model": "typesafe/jev-1.13-20260917", "answers": {"guard.risk": {"type": "score", "score": 1.01, "legend": {"0": "destructive", "1": "read_only", "2": "reversible"}, "probabilities": {"0": 0, "1": 0.99, "2": 0.01}, "confidence": 0.99}}, "usage": {"input_tokens": 337, "output_tokens": 19, "cost": 0.000014154}}
```

`probabilities` sums to `1.0` (`0 + 0.99 + 0.01`), keyed by the stringified index
`legend` maps back to `destructive` / `read_only` / `reversible` — the exact shapes
`tasks.md` task 1.4 pins into a fixture.

## What Changes

- Build the `score`-typed request's `criteria` as a JSON array of plain option-name
  strings, one per `option.*` the question file declares, in declaration order — not the
  description text those options also carry, which stays unsent for `score` exactly as it
  is today (`choice` and `noul` keep their existing object-shaped `criteria`, with
  descriptions as values, confirmed live and unaffected).
- Parse a `score` response's `probabilities` through the answer's own `legend` (index →
  option name) instead of assuming `probabilities` is already keyed by option name, and
  correct the decision-model spec's claim that `score` probabilities are independent —
  live evidence and TypeSafe's own docs agree they sum to 1.
- Add a fixture-based test that pins both shapes against the recorded live response in
  this proposal, so a future contract drift fails a test instead of shipping silently
  broken, the same way `decide.py`'s other request/response shapes are already tested.
- Make the shell guard's default list (read-only allowlist, deny, ask, and the
  decision-model residue call) inert in a project without `.harnex.yml`, or whose
  `.harnex.yml` does not list `safety` among its sets — mirroring the canary check's own
  inertness exactly, per the already-recorded decision in `docs/PLAN.md` §12.19. A
  `.harnex.yml` that exists but fails to read or parse stays active (never allow on an
  error), and a role's own pattern additions (`agent_type`-scoped) stay active
  unconditionally, since they are not a set a project opts into.
- This repository's own `.harnex.yml` comments out `safety` from `sets:`, as a deliberate
  bootstrapping opt-out: harnex is still being built on top of itself, and the guard asking
  before nearly every command slows that work down; the project re-enables `safety` once it
  is far enough along that the guard's prompts are a help rather than friction. This is the
  `safety` opt-out `docs/PLAN.md` §12.19 already describes, exercised on the harness's own
  repository — the same path task 4.2/4.3 test, not a new mechanism.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `decision-model`: the "A `score`-typed question resolves through one threshold per
  option" requirement gains an explicit wire shape for the request's `criteria` and the
  response's `probabilities`, where today's spec only says the interface "SHALL build a
  request whose `criteria` declares every option" without saying how, and corrects the
  claim that `score` probabilities are independent.
- `shell-guard`: a new requirement that the default list is inert without the project's
  own `safety` set chosen, matching `canary-check`'s existing inertness and the decision
  already recorded for every harnex hook.

## Impact

- `plugin/scripts/decide.py`: `_question_payload` (branch for `score`, `choice`/`noul`
  unchanged) and `parse_response`'s `score` branch.
- `plugin/control/guard/guard.py`: a new `.harnex.yml`-aware gate in front of the default
  list's classification (`classify_segments`/`classify_command`), importing
  `setup.parse_choices` the same way `canary.py` and `decide.py` already do. No change to
  `guard-risk.yaml`, `patterns.yaml`, or any rule file; the pattern lists themselves and
  role-scoped additions are untouched.
- `tests/` fixtures covering `decide.py`'s `score` path (request shape and response
  parsing) and `guard.py`'s inertness (present/absent/malformed `.harnex.yml`, with and
  without `safety`, and a role addition still applying while inert).
- `.harnex.yml` (repo root): comment out `- safety` under `sets:`, this repo's own
  opt-out, enabled by the inertness fix above.

## Pillar and phase

Pillar 3 (Orchestration) owns `decide.py` and the decision interface; pillar 4 (Control &
Guardrails) owns the shell guard. Both fixes directly unblock `C4`'s own shell guard
(delivered), whose `guard.risk` question is the only `score`-typed question in the
repository today, and whose default list is the only guard-owned mechanism `.harnex.yml`'s
`safety` set is meant to gate. This change belongs to `C4`'s own exit criterion, not a new
phase: `C4`'s "You try it" step ("ask something ambiguous... it asks you") only ever
demonstrated the *unresolved* path live, and never exercised `.harnex.yml` opting out of
`safety` at all — this change is what makes a `score` question actually resolve, and makes
the opt-out `docs/PLAN.md` §12.19 already promises actually work, for the first time.

## Non-Goals

- Fixing the installed plugin cache's stale `decide.py` (no `.env` fallback) — already
  fixed on `main` (`2be8db5`); the gap is distribution/versioning, `C6`'s job, not this
  change's.
- Changing `DECIDE_TIMEOUT_SECONDS`, the guard's retry count, or any threshold
  (`rule_threshold.read_only: 0.85`, etc.).
- Touching `choice` or `noul` request-building — both confirmed live, unaffected by this
  bug.
- Adding new `score` questions or changing `guard-risk.yaml`'s own options.
- Extending inertness to any set other than `safety`, or to any feature flag — the guard's
  default list is the only mechanism `safety` currently governs; no other set gates
  guard-owned behavior today.
- Changing `plugin/control/guard/generate_floor.py` or the committed permission floor
  (`floor.json`, `.claude/settings.json`'s merged entries) — the floor is a setup-time
  artifact already written per the project's chosen sets; this change is about the live
  hook's own runtime check, not floor generation.
- Patching an already-installed plugin's cache directly, in this repository or any other —
  out of reach for an agent working inside this session, and not how a fix is meant to
  reach an installed project regardless (that is `/harnex:update`'s job, `C6`).
