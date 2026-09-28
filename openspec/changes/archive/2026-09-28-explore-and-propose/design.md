## Context

See proposal.md for why. What exists today, and what this design builds on:

- `C1c` established the pattern this change reuses everywhere: a skill (`plugin/skills/setup/SKILL.md`) holds the conversation and every approval; a stdlib-only Python script (`plugin/scripts/setup.py`), run with `uv`, holds every filesystem step and prints structured output the skill reads. `decide.py`, `scope_check.py`, `explore` and `propose` all follow this split: **scripts never talk to the person; skills never touch a file or a socket the script should own.**
- `C1b` established "YAML-shaped, not YAML": rule frontmatter is four flat `key: value` lines, parsed by a parser that refuses anything else, so no YAML library is ever a dependency. `docs/PLAN.md` §8 calls the decision questions "YAML" — this design reads that the same way it read the rules: the questions in `plugin/orchestration/decisions/` are YAML-*shaped*, parsed by the same kind of small, refusing parser, for the same reason (decision 15).
- `plugin/context/rules/sdd/the-proposal-is-the-scope.md` already states the rule this change enforces; `enforced_by: none` since `C1b`, which pillar 1's own format doc calls a bug once a change is positioned to fix it.
- `plugin/orchestration/README.md` and `plugin/tools/README.md` were both written in `C1a`. `tools/README.md` already has the pattern this design needs — a "What is here" section naming files that live outside the pillar's own directory (`../skills/setup/`, `../scripts/setup.py`) because Claude Code requires them elsewhere. `orchestration/README.md` promises the same thing ("Filled by `C2`") but the section does not exist yet.
- The OpenRouter Decisions endpoint (`POST https://openrouter.ai/api/alpha/decisions`, model `typesafe/jev-1.13`) was read from OpenRouter's own docs while designing this change (2026-09-28): request body `{model, state, questions: {id: {type, instructions, criteria}}}` for `noul` / `choice` / `score`; response `{id, model, provider, answers: {id: {type, ...}}, usage: {input_tokens, output_tokens, cost}}`; documented error statuses 400/401/402/403/404/413/429/500/502/503/524/529. No documented rate limit or timeout value — this design assumes none and sets its own.
- This repository's own OpenSpec workflow (`.claude/skills/openspec-*`) is dev tooling for building harnex itself; a harnessed *project* has no reason to have it installed. `propose` therefore drives the `openspec` CLI directly — `new change`, `status --json`, `instructions <id> --change <name> --json` — the same sequence this very change was authored through, not by re-invoking another plugin's skill.

## Goals / Non-Goals

**Goals:**

- One interface (`decide()`), two backends, one journal format — usable exactly as
  documented with no key, so a project can adopt harnex before ever touching OpenRouter.
- `explore` and `propose` hide OpenSpec and the decision model equally: the person sees a
  plain conversation, an advice line, a set of artifacts, and a review — never an artifact
  id, a schema name, or a raw HTTP error.
- The verifier is read-only **by construction** — an empty capability, not a promise the
  prompt keeps.
- Every failure mode named: what happens when OpenRouter is unreachable, when the key is
  missing, when the response is malformed, when `propose` writes outside its directory.

**Non-Goals:**

- Generalising the decision-question file format to every shape §8's table names.
  `task.scope`'s two-threshold `Noul` and `guard.risk`'s two-threshold `Score` are `C3`'s
  and `C4`'s to add; this design covers exactly what `phase.route` (a single-threshold
  `Choice`) needs.
- Closing the loop on `resolution`. The journal schema reserves the field (§8); nothing in
  `C2` yet knows an outcome to write there, since neither `explore` nor `propose` is bound
  by the decision they print. Left empty on every line this change writes.
- A `SubagentStop` canary hook for the verifier (proposal.md, "Downstream").
- Anything under `plugin/control/` or a `guard.risk` implementation — `C4`.

## Decisions

### D1 · `decide.py`'s contract: it never raises, and "ask" is a value, not a side effect

`decide.py` is invoked as `uv run decide.py ask --question <id> --state <json-file>
--project <root>` and always prints exactly one JSON object to stdout, then exits 0 (a
non-zero exit means the *script* is broken — bad arguments, an unreadable state file —
never that the decision was unavailable). The object is one of:

```json
{"resolved": true, "decision": "codex", "probabilities": {"codex": 0.83, "claude-sonnet": 0.12, "human": 0.05}, "confidence": 0.83, "backend": "jev"}
```
```json
{"resolved": false, "backend": "jev", "reason": "below_threshold", "prompt": "…", "probabilities": {...}, "confidence": 0.55}
{"resolved": false, "backend": "jev", "reason": "unreachable: timed out after 3s, 1 retry", "prompt": "…", "probabilities": null, "confidence": null}
{"resolved": false, "backend": "mock", "reason": "mock_backend", "prompt": "…", "probabilities": null, "confidence": null}
```

Every path that is not a clean, above-threshold `jev` answer — no key, unreachable,
malformed response, below the question's own threshold, or the backend genuinely
configured as `mock` — collapses to the same `resolved: false` shape. **The calling skill
has exactly one branch to write**: `resolved` → use `decision`; otherwise → ask the person
`prompt` yourself (`AskUserQuestion` or plain conversation) and use their answer directly,
never call `decide.py` a second time for the same question. This is the guard's own
"never allow on its own error, only ask" (§9) applied to advice instead of permission, and
it is the contract `C4`'s `guard.risk` will need too — established once, here.

*Alternative considered:* let `decide.py` block on stdin and ask the person itself when
`mock`. Rejected: a script run through the `Bash` tool has no line the person is watching
synchronously the way a real terminal's `input()` would; `setup.py` already draws this
line (scripts never talk to the person) and nothing about decisions is special enough to
cross it.

### D2 · The decision-question file format, "YAML-shaped" like a rule

`plugin/orchestration/decisions/phase-route.yaml`:

```
id: phase.route
type: choice
state_fields: phase, task, profiles
option.codex: Delegate to Codex through its plugin — well-scoped implementation with tests already named.
option.claude-sonnet: A Claude subagent on Sonnet — the default for ordinary work.
option.claude-opus: A Claude subagent on Opus — hard design or ambiguous reasoning.
option.claude-fable: A Claude subagent on Fable — long-form or narrative-heavy design writing.
option.human: Ask the person — a judgement only they can make.
rule_threshold: 0.70
---

# Which tool and model should run this phase?

`explore` and `propose` run in the main session, whose model harnex cannot switch, so this
question is advice only for them: the screen line says "advice" and a low-confidence
answer is shown, not enforced. `verify` binds it.

**State:** `phase` (the command name), `task` (the person's own framing, one paragraph,
never the model's description of its own work), `profiles` (the project's chosen stack
profiles).

**Rule:** the option with the highest probability, if that probability is at least 0.70;
otherwise ask the person which one they want.
```

One parser reads every field before the bare `---` line as `key: value`, refusing a
second colon-free line or a duplicate key — the same refusal `render_rules.py` already
performs for rule frontmatter, extended by one convention: a key of the shape
`option.<name>` is collected into a `{name: text}` map rather than kept as a literal key.
No key nests for real; `option.codex` is one flat string key, not two levels of structure,
so the parser never recurses. The line below `---` is read only by a person or a model —
`decide.py` never parses it — the same redundancy C1b calls "the check": frontmatter is
what code trusts, prose is what an agent reading the file trusts, and they must agree.

*Alternative considered:* true YAML via `PyYAML`. Rejected on decision 15 exactly as
C1b rejected it for rules: the format is simple enough that the library buys nothing but a
dependency `uv` has to resolve before a skill can ask a single question.

### D3 · Building the OpenRouter request and reading the response

For a `choice` question, `decide.py` builds:

```json
{
  "model": "typesafe/jev-1.13",
  "state": {"phase": "propose", "task": "<the person's framing>", "profiles": []},
  "questions": {
    "phase.route": {
      "type": "choice",
      "instructions": "Which tool and model should run this phase?",
      "criteria": {"codex": "…", "claude-sonnet": "…", "claude-opus": "…", "claude-fable": "…", "human": "…"}
    }
  }
}
```

`state` is the object the caller passed (per D5, never a bare positional list), keyed
exactly as `state_fields` names it — satisfying the "never index by position" rule §8 now
carries. `criteria` is built from the question file's `option.*` map, so the file is the
only place an option's wording is written. The request goes to `POST
https://openrouter.ai/api/alpha/decisions` with `Authorization: Bearer
$OPENROUTER_API_KEY` and a 3-second timeout, one retry on a network error or a 5xx (502,
503, 524, 529 — read as "try again", not "ask"); a 4xx, a malformed body, or a second
failure all degrade to D1's `resolved: false` shape, each with its own `reason` string for
the journal. `usage.cost` is recorded in the journal line as `cost_usd` — not in §8's
schema, added because it is the one number that lets a later phase tell whether `jev` is
worth its own risk (`docs/PLAN.md` §14 already calls it "alpha, with observed hangs").

*Alternative considered:* the vendor's own TypeSafe SDK. Ruled out already (§8): it cannot
target OpenRouter, and decision 15 rules out a third-party HTTP library regardless.

### D4 · The verifier: read-only by `tools`, not by prompt

`plugin/orchestration/roles/verifier.md` — the tool-agnostic role prompt, following the
skeleton the role study set: what it reads first (every artifact in the change's directory,
re-read from disk, never from the conversation — reusing `artifacts-are-the-brief`), what
it reports (a short markdown review: for each artifact, contradictions with `docs/PLAN.md`
or with another artifact in the same change, gaps against the phase's exit criterion, and
nothing else — no style notes, no rewriting), what it must refuse (fixing anything, ticking
anything, reopening a decision `docs/PLAN.md` §12 already settled).

`plugin/agents/verifier.md` — the Claude Code binding: frontmatter `name: verifier`,
`description`, `tools: Read, Grep, Glob` (no `Edit`, `Write`, `Bash`, `WebFetch` — it
reviews artifacts already on disk, nothing else). This is the row in §4's table that is
**P**, not I·D: a subagent whose `tools` list has no write capability cannot write,
independent of what its prompt says. `propose` starts it with the `Agent` tool, passing
the change's directory; its returned review is shown to the person verbatim, then
`propose` finishes — the review never blocks, matching "must refuse: fixing" in §4.

*Alternative considered:* a single combined `roles/verifier.md` with the Claude binding
inline, skipping the split `orchestration/roles/` vs `agents/` layout. Rejected: `C3`'s
`builder` needs the identical split (one Codex-side adapter, one Claude-subagent-side
adapter, one shared role prompt), so paying for the split now, on the simpler role, is
cheaper than retrofitting it under `C3`'s pressure.

### D5 · `scope_check.py`: a before/after `git status`, not a fingerprint

`propose`'s procedure captures `git status --porcelain=v1 --untracked-files=all` to a temporary file the moment
it starts, before creating the change. Once every required artifact exists, it runs:

```
uv run "${CLAUDE_PLUGIN_ROOT}/feedback/scope_check.py" check --change <name> --before <snapshot-file>
```

The script re-runs `git status --porcelain=v1 --untracked-files=all`, diffs against the snapshot, and reports
any path — new or modified, tracked or not — that is not under
`openspec/changes/<name>/` and was not already dirty before `propose` started (so a
proposal is never blamed for a mess that predates it). It exits 0 whether or not it finds
anything; `propose` shows the report to the person and does not fail the run — the check
is **detection**, per §4, not prevention, and pillar 5's own README says this pillar
"reports; it never repairs."

*Alternative considered:* `C10`'s fingerprint (a hash of the diff plus untracked files),
reused early. Rejected for now: the fingerprint's whole point is comparing the *same* tree
before and after a check re-runs on it (§10), which `propose` has no reason to do — it
writes once and stops. A plain path diff answers the one question this change has:
did anything land outside the directory. `C3` can still reuse this script's path-diffing
core for its own containment checks; nothing here forecloses that.

### D6 · Extending `the-proposal-is-the-scope`, not adding a new rule

The rule's body already says the right thing ("work that falls outside [the proposal] has
not been approved"); it never named a mechanism because none existed. This change adds:

```
enforced_by: check
```

and a body line: `**Enforced by:** the scope check, \`feedback/scope_check.py\` (pillar
5), run by \`propose\` once every artifact exists.` No new `sdd` rule file — the prompt
that requested this design asked to check for a close existing rule before adding one, and
this one already is the statement; it was only ever missing its enforcer.

### D7 · `explore` does not touch `openspec/` at all

`explore` prints the advice line (`phase: "explore"`, `task` = the person's own framing of
the idea) and then is a conversation, not a procedure with filesystem steps — the vendored
`openspec-explore` dev skill's own framing ("a thinking partner… before or during a
change") is the right shape, but harnex's version depends on nothing outside the plugin.
It never creates a change directory (there is nothing to scope-check yet) and never calls
the verifier (there is nothing to review yet). Its only artifact is the conversation
itself; when the person is ready, they say so and run `/harnex:propose`.

## Risks / Trade-offs

- [OpenRouter's Decisions endpoint was read from docs, not exercised live — this
  repository has no working key at the time of this design] → `decide.py`'s tests run
  against a recorded response shaped exactly as the docs show (D3) and against a stubbed
  hanging socket; a first real call is part of this change's manual "try it" step, and any
  mismatch between the documented and the actual response shape is fixed then, not
  assumed away.
- [A `jev` call inside `propose` adds latency to a phase the person is sitting through] →
  Bounded by the 3 s timeout and one retry (D3); worse, it degrades to asking the person,
  which is no slower than the `mock` backend they could have chosen instead.
- [The verifier's review has no severity levels, unlike the fuller verifier `C5` builds] →
  Deliberate: "minimal" per the plan's own word for this phase's verifier. A finding list
  with no gate is still strictly more than the nothing `C1` had.
- [`option.<name>` keys make the question file's parser slightly less uniform than a rule's
  four fixed fields] → Bounded to one convention, documented in D2's own file, and reused
  nowhere else in `C2`.

## What setup and update write

Nothing changes in a harnessed project's committed files. `decision_model` has been a
valid `.harnex.yml` key since decision 11; a project already recording `mock` or `jev`
needs no migration, and one that has never set it keeps whatever `setup` already defaults
it to. `explore`, `propose`, the verifier and the two scripts arrive with a plugin update,
the same way `C1d`'s hook did — no new question, no new file in the project, no change to
`.claude/settings.json`.

## Guarantees and what happens when they fail

| Guarantee | Kind | When the component fails |
|---|---|---|
| A phase-routing answer is never treated as binding in `explore`/`propose` | **instruction**, by the skill printing "advice" and never acting on `decision` unattended | A skill that acted on it anyway would be a bug in that skill, not in `decide.py` |
| The person is always asked when `jev` cannot answer confidently | **prevention**, by construction: `decide.py` cannot return anything but `resolved: false` on any failure (D1) | None — this is the fallback path itself; there is nothing further behind it |
| The verifier writes nothing | **prevention**: its `tools` list has no `Edit`, `Write` or `Bash` | A future Claude Code release could add an implicit write-capable tool to every subagent; the frontmatter test (already planned for `C2`) fails first if the list ever changes shape |
| A `propose` run that writes outside its change's directory is reported | **detection**: `scope_check.py`, run after every required artifact exists | If the script crashes, `propose` says the scope was not checked, rather than staying silent — mirroring D7 of `C1d`'s canary design |
| Every decision call is journaled | **detection**, for later tuning, not a live guarantee of anything | A crash between the call and the journal write loses that one line; nothing downstream yet depends on the journal being complete, so this is accepted, not mitigated, in `C2` |
