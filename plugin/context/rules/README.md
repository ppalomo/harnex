# The rule format

A rule is a short statement of how work is done that every agent must follow. One rule is
one file. The harness holds no second statement of the same rule — if a rule is also
enforced, the enforcement lives in pillar 4 or pillar 5 and the rule file names it.

Rules are grouped into **sets**, one directory each. A set is what a project chooses; a
project's chosen sets are rendered into its rules file by `../../scripts/render_rules.py`.

## The file

```markdown
---
id: no-ai-attribution
set: git
applies_to: always
enforced_by: none
---

# Never add an AI author or co-author line to a commit or a pull request

The history records who is accountable for a change, and that is the person who approved
it. A co-author line on a machine makes the record wrong in a way no later commit can fix.
```

Four fields, all plain `key: value` strings, nothing nested and nothing quoted. The
parser that reads them understands that and nothing else, and refuses the rest rather
than guessing, so the format stays the schema.

| Field | What it is |
|---|---|
| `id` | the rule's identity, unique across every set, and the file's own name without its suffix |
| `set` | the set the rule belongs to, which is the directory it is stored in |
| `applies_to` | `always`, or the name of a profile under `../../tools/profiles/`; a profile rule is rendered only for a project that declared that profile |
| `enforced_by` | `none`, `guard`, `hook`, `check` or `decision` |

The body is the rule as an agent reads it. Its first line is a level-one heading that
**is the rule, stated as one sentence**; what follows is why it exists, in a few lines.
There is exactly one heading in the body — a file that needs a second one is two rules.

## Enforcement

`enforced_by` says what kind of thing enforces the rule, not where it lives:

| Value | Enforced by |
|---|---|
| `none` | nothing. The rule is read and followed, and that is the whole mechanism. |
| `guard` | the shell guard, before a command runs (pillar 4) |
| `hook` | a hook the host calls around a turn (pillar 5) |
| `check` | the project's check command, or the loop that runs it (pillar 5) |
| `decision` | a question put to the decision model (pillar 3) |

A rule whose `enforced_by` is anything but `none` **must** carry a line in its body
beginning `**Enforced by:**`, naming the component that does the enforcing. That line is
how a reader of the rule finds the code, and how a check walks the other way — from every
rule that claims a hook to a hook that exists. Both directions are tested.

A rule may name an enforcer that a later change builds. That is the normal order: the
statement comes first, and the enforcement is written against it.

## What a rule must not contain

- **A project name, its domain vocabulary, a private resource or a credential.** A rule
  that needs a project fact says so and leaves the fact to the project's own working
  instructions.
- **A technology name.** Only `../../tools/profiles/` may name a language, a framework or
  a service. A rule that needs one is a profile rule, or is written without it.
- **A second rule.** If the body says "and also", it is two files.

## Adding a rule

Write the file, put it in its set, and run the checks. Adding a set is adding a
directory: the renderer discovers sets from the tree, so there is no list to keep in step.
