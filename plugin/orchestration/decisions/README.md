# The decision-question format

A decision question is one typed question `decide.py` can put to a backend: its type, its
options, the state it needs, and its own rule on the returned probabilities. One question
is one file. The format is YAML-*shaped*, not YAML, for the same reason a rule's
frontmatter is (`../../context/rules/README.md`): the schema is simple enough that a
parser can refuse anything it does not understand instead of a library guessing at it,
and `decide.py` is standard library only (decision 15).

## The file

```markdown
id: phase.route
type: choice
state_fields: phase, task, profiles
option.codex: Delegate to Codex through its plugin — well-scoped implementation with tests already named.
option.claude-sonnet: A Claude subagent on Sonnet — the default for ordinary work.
rule_threshold: 0.70
---

# Which tool and model should run this phase?

Explains, for a person or a model reading the file, what the question is for and how the
rule reads in prose. `decide.py` never parses this part; the frontmatter above is what it
trusts, and the two must agree.
```

Every line above the bare `---` is `key: value`, flat, nothing nested and nothing quoted —
the same refusal `render_rules.py` already performs for rules. One convention extends it:
a key of the shape `option.<name>` is collected into a `{name: text}` map rather than kept
as a literal key; every other key is exactly one flat string.

| Field | What it is |
|---|---|
| `id` | the question's identity, matching the file's own name without its suffix |
| `type` | `choice`, `noul` or `score` — the three shapes a backend can answer |
| `state_fields` | the field names the caller's state must carry, comma separated |
| `option.<name>` | for `choice`, one line per option, its text explaining when to pick it |
| `rule_threshold` | the probability the highest option must reach before the question resolves; below it, the caller asks the person |

Below the `---`, the body is prose: the question stated as one sentence in a level-one
heading, then why it exists and how its rule reads for a person. Redundant with the
frontmatter on purpose — the same reason a rule states its enforcer in both places.

## What is here

- `phase-route.yaml` — the `phase.route` question from `docs/PLAN.md` §8: which tool and
  model should run a phase. Advice only where the phase runs in the main session; binding
  for `verify` once it exists.

## What does not

- **A question whose rule needs more than one threshold.** `task.scope`'s two-threshold
  `noul` and `guard.risk`'s two-threshold `score` extend this format when `C3` and `C4`
  add them; nothing here generalises ahead of a question that needs it.
- **The client that reads these files.** `../../scripts/decide.py` is the interface and
  its backends; this directory holds only what a question asks and how it is judged.
