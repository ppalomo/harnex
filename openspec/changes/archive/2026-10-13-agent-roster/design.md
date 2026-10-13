## Context

See `proposal.md` for why. What shapes the approach:

- `C10` made the profile directory the team (its design D1) and deliberately added no
  key to `.harnex.yml`, to leave decision 11 closed. This change reopens decision 11
  for exactly two keys, and keeps D1's mechanism: a fragment is still what a stack
  adds to a role, read from the profile directory; only who is on the team moves.
- The choices file is flat on purpose (scalars and lists, `parse_choices`, standard
  library only), and its reader refuses a missing key. Every `.harnex.yml` written so
  far lacks `team` and `bench`, and `update` must keep reading those files unaided
  (`harness-update`: a fresh clone updates asking nothing). So the two keys cannot be
  required.
- A role's frontmatter is exactly four fields, by spec, by test and by the renderer's
  own refusal of an unknown field. `department` is a fifth; `triggers`, which would be
  a sixth and would need a home on the fragment side, is the next change.
- The host starts a project agent by its `name` field; the plugin's own agents are
  reached as `harnex:<name>`. A project agent named `debugger` would therefore not
  collide with the plugin's, but it would be a second Dani with a different prompt
  lifecycle. The roster refuses the five core names for that reason.
- The `review` and `propose` skills already read the profiles from the choices file
  and hand them to `render_agents.py list`; the roster travels the same way.

## Goals / Non-Goals

**Goals:**

- A project names its specialists, independently of its stacks, and tells the ones a
  skill starts from the ones the person starts.
- Nothing recorded before this change reads differently: no roster, same agents, same
  fan-out.
- A specialist is useful without a stack: the generic agent is the role as written.
- Adding a department later costs one value in one tuple and one line per role.

**Non-Goals:**

- A roster that varies by phase, by profile or by branch; a roster entry carrying
  anything but a name.
- Any change to the manifest, the fragment convention (no frontmatter on a fragment),
  the persona shape, the guard or the floor.
- Starting a bench agent from any skill, under any flag. The bench is on disk for the
  person.

## Decisions

### D1 · Two optional list keys, present together or absent together

Options considered:

- **A nested `team:` with `always:` and `on_demand:` under it.** Rejected: the file
  is flat by decision, and the flat reader would need a second grammar for one key.
- **One list with a marker per entry (`security-reviewer!`, `+name`).** Rejected: a
  marker is a second grammar hidden inside a value, and the lists are what a person
  reads back.
- **Two flat lists, `team` and `bench`.** Chosen. `parse_choices` gains a notion it
  did not have — an optional key — as the tuple `ROSTER_KEYS = ("team", "bench")`
  that the "missing" check skips; everything else about the grammar is unchanged.
  `Answers` carries `team`, `bench` and a boolean `roster_recorded` derived from
  their presence, so no caller tests for `None`.

  The two keys are kept out of `ANSWER_KEYS`, `LOCAL_ANSWER_KEYS` and the two list-key
  tuples, which every existing loop treats as required: `read_answers` turns a missing
  list key into `[]`, `validate_answers` looks each list key up among what the harness
  holds, and `parse_choices` indexes every list key. Instead `ROSTER_KEYS = ("team",
  "bench")` is one tuple of its own, read after those loops by one function,
  `read_roster(values)`, which returns either "absent" or both lists — the
  absent-versus-empty difference this decision rests on lives there and nowhere else.
  `parse_choices` accepts the roster keys as known, `_format_flat` appends them once,
  at the end of either shape (after `check_command` for `.harnex.yml`, after
  `store_id` for `.harnex/config.yml`), and only when recorded.

Both or neither: a file with one key and not the other is refused with the line, since
a person who wrote `team:` and forgot `bench:` has not said whether the bench is
empty. Both empty is a valid, explicit "nobody", distinct from absent.

The answers document setup's skill assembles (JSON) carries the same two keys; on a
first setup they are always present, so a project set up from now on always records
them. `_format_flat` writes them last in either shape — the file's order, not the
order setup asks its questions in (the roster is asked after the profiles, D6). On a
rerun the skill forwards the two keys from the recorded file only when the file carries
them, so an absent roster is never turned into an empty one; a project set up before this change has them nowhere, and nothing adds
them — `update` never writes the choices file, and setup never rewrites one that
exists.

### D2 · The roster names specialists; profiles supply fragments

A roster name is a role the harness holds whose phase is `review` or `propose` and
that does not ship as a plugin agent. That last condition is read from the plugin's
own `agents/` directory, the same way `sync` finds the core set: no list of core names
in the script. `validate_answers` checks every name against `held_specialists()`, a
new renderer function returning each such role with its department, emoji and phase —
which is also what `choices` prints as `specialists`, grouped by department, so the
offer and the validation cannot disagree.

The same checks hold on every path a roster reaches, not only setup's. `update` reads
the choices through `read_choices`, which already ends in `validate_answers`, so a
roster edited by hand is refused by `update` with the same message setup gives. The
skills reach the renderer directly through `list`, so `_walk` refuses on the same
terms and with the same text: the entry, why it cannot be on a roster, and the
specialists the harness holds. One helper, `roster_refusal()`, in the renderer, words
it for both callers.

A fragment for a role that ships as a plugin agent is refused too, with or without a
roster: `C10` would have rendered `<profile>-debugger`, and setup's default team would
then propose a name the roster refuses. No shipped profile carries one, so this
refuses nothing that exists today.

Rendering, given a roster and the profiles: for each name, every chosen profile with a
fragment of that name yields `<profile>-<name>` as today; a name with no fragment
among the chosen profiles yields the generic agent (D3). A chosen profile's fragment
for a name not on the roster yields no agent, but is still read and checked: every
fragment of every chosen profile is validated on every walk, roster or not, so a
fragment naming no role, or an `apply`- or `verify`-phase role, is refused rather than
skipped whatever the roster says. Without a roster, the walk is `C10`'s:
every fragment of every chosen profile, and no generic agent. `_walk` is the one
place this is decided, so `render`, `agents_for` and `available_teams` keep agreeing.

### D3 · The generic agent is the adapter of the role at a project path

`render_generic(role)` is `adapter_of(role)` — the same bytes `sync` writes under
`plugin/agents/` — placed at `.claude/agents/<name>.md`. No stack heading, no
description suffix, nothing invented. The same spec requirement that makes an adapter
"the role minus `phase`" now says "minus `phase` and `department`", and the generic
agent inherits it. Ownership, local exclusion, removal and conflict are the existing
paths' outcomes, since `_render_agents` returns the generic agent in the same
`{path: bytes}` map; the only new text is the plan's reason, "named on the project's
team" or "named on the project's bench", in place of "rendered for the `<profile>`
profile's team".

### D4 · `department` is a fifth role field, dropped on rendering

`ROLE_FIELDS` becomes five; `AGENT_FIELDS` stays three. `DEPARTMENTS =
("engineering", "design")` is a tuple in the renderer, and `read_role` refuses a value
outside it by name. The field is read by `held_specialists()` and `list` and by
nothing else in this change: it groups, it does not gate. A test asserts every role
carries one of the tuple's values and that `designer` and `accessibility-reviewer`
are `design` — the one project-of-harnex fact the test pins, since the grouping is the
point of the field.

### D5 · The listing takes the roster and hides the bench

`render_agents.py list --profiles <a,b> --team <x,y> --bench <z> --phase review`:
`--team` and `--bench` are optional and must be given together (an empty value is a
present, empty list), mirroring D1. With them, `agents_for` walks the roster and keeps
only team names; without them it walks the profiles as today. Output is unchanged in
shape — emoji, one space, `name` — so the skills' presentation is untouched. A
department is not added to `list`, and `list` does not group: the skills start
agents by phase and roster, and a department changes neither. The department shows in
setup's offer (D6); a listing of the team by department is the later `/harnex:team`
command's, which can ask `held_specialists()` directly.

The `review` and `propose` skills read `team` and `bench` from the same file they
read `profiles` from and pass them through when present. Their fan-out step is skipped
only when the project records neither a roster nor any profile; a roster with no
profile still starts its team, through generic agents. `list` therefore accepts an
empty `--profiles`. A skill does not judge the keys itself: it passes what it read,
and when `list` refuses — one option without the other, or a name no roster can hold
— the skill shows `list`'s own message as printed and stops the fan-out, as it would
for any unreadable choices file. That message names the missing option or the entry;
the file is named by the skill, which knows which one it read.

### D6 · Setup asks once, proposes the profiles' specialists, and never asks again

The roster question comes after the profiles and before the canary word, on a first
setup only. `choices` prints `specialists` — every roster-eligible role, grouped by
department — so the skill can show the whole offer, and `teams` still says which
specialists each profile holds a fragment for, which is what the proposed default is
built from. The skill records the person's answer in both lists, empty or not. A
project with recorded choices is not asked: the choices file is the project's, and
"edit it and run again" is already how every other choice changes.

### D7 · Decisions 1, 4 and 11 are revised, 15 and 16 hold

Decision 11 gains "`team` and `bench`, optional, present together". Decision 4 changes
in two places: the five stack specialists are rendered per project from the roster —
prefixed by each chosen profile holding a fragment for one, generic when none does —
rather than "from a profile's team", and each role names its department. Decision 1
keeps "stacks are profiles, and a profile may declare fragments", and narrows what the
fragments are: a profile's team for a project without a roster, and under a roster
only what that stack adds to a specialist the roster names. Decision 15 holds because
the reader is still the standard library's, and decision 16 because the rendered
agents remain a pure function of the choices, roster included.

## What setup and update write, and who owns each path

| Path | Owner | Written by | Visibility |
|---|---|---|---|
| `.harnex.yml` | **project** | setup, on a first setup only, now with `team:` and `bench:` | `shared` |
| `.harnex/config.yml` | **project** | setup, on a first `local` setup only, same two keys | `local` |
| `.claude/agents/<profile>-<specialist>.md` | harness, by hash | setup (after the yes), update (asking nothing) | both; under `local` also excluded by its own path |
| `.claude/agents/<specialist>.md` (generic) | harness, by hash | same | same |
| `.harnex/manifest.json` | harness | setup, update | both |
| `.git/info/exclude` | local (this clone) | setup, update | `local` only — one entry per agent path, generic ones included |

Nothing else changes. A project's own files under `.claude/agents/` are never read for
content, written or removed. A project-owned agent whose name happens to equal a
generic agent's path is the existing "present but unaccounted for" conflict, resolved
by moving it aside or adopting, never silently.

## Guarantees, by kind

| Guarantee | Kind | When the component fails |
|---|---|---|
| A bench agent is never started by a skill | **I** — the listing omits it, and the skill starts only what the listing prints; the skill-content tests assert the wording | a skill that started it by name anyway would be read-only still (P, the role's `tools`); nothing detects the start after the fact |
| A roster name can only be a read-only specialist | **P** — `validate_answers` refuses an `apply`/`verify` role, an unknown name and a core name before any plan; tested | a refusal is a `SetupError`, shown like any other, and nothing is written |
| A generic agent cannot write | **P** — it is the role's own `tools`, copied; every roster-eligible role is a `review`/`propose` role, whose `tools` the existing test reads | a role with a wrong `phase` or `tools` fails the suite before release |
| A project recorded before this change reads unchanged | **D** — `test_update_reader` and `test_setup_answers` read a file without the keys and assert no roster and the `C10` agents | a reader that refused would surface as an `update` refusal on every existing project, loudly |
| Rendering is byte-stable under roster order | **D** — a test renders the same roster in two orders | a renderer that depended on order would fail that test before release |
| `department` is one of the named values | **P** — `read_role` refuses by name; tested across every role | a bad value fails the suite and `sync --check` before release |
| An adapter is its role minus `phase` and `department` | **D** — `sync --check`, run by the correspondence test | an edited role or adapter fails the suite naming the adapter |
| Setup never asks a project that already answered | **I** — the skill's own steps; tested as content | a skill that asked anyway could not record the answer, since setup never rewrites the choices file (P) |

## Risks / Trade-offs

- [A person writes `team:` and not `bench:`] → refused with the line, naming the
  missing key; nothing rendered. The message says both keys go together.
- [Two chosen profiles both hold a fragment for a roster name] → two prefixed agents,
  as `C10` renders today; the roster does not change that, and the listing shows both.
- [A roster drops a specialist a profile holds a fragment for] → the fragment is
  simply unused; nothing warns, since not wanting a specialist is the point.
- [The generic agent's path `security-reviewer.md` collides with a project's own agent
  of that name] → the existing unaccounted-for conflict; setup stops and names it.
- [Existing projects never gain a roster unless edited by hand] → accepted: the file
  is the project's, and the smoke section shows the four lines to add.
- [`list` gains two options the skills must pass correctly] → the skill-content tests
  assert the command lines; the options must be given together or `list` refuses.

## Migration Plan

1. Land the renderer's five fields, the generic rendering and the optional keys with
   no skill change: every existing project updates to nothing new, since none records
   a roster.
2. Land the skills: setup asks on a first setup; `review` and `propose` pass the keys
   when present.
3. At ship, after the deltas are synced into `openspec/specs/`, the `agent-teams`
   Purpose is reworded by hand to say a team is the set of specialists a project's
   roster names, each completed by what a chosen stack adds. The delta format cannot
   carry a Purpose for an existing capability, and `openspec/` is never a builder's to
   write, so this is ship's edit, not a task's. The requirement titles that still say
   "profiles" keep their names: renaming them would add a rename delta for wording
   alone, and their bodies already state the roster.
4. Rollback is removing the two keys from a project's choices file: the next `update`
   renders the profiles' agents as `C10` did and removes the generic ones, since they
   still match their fingerprints.

## Open Questions

- Whether a later `/harnex:team` should read the roster from the choices file or from
  the generation record. Deferrable: the record lists paths, the file lists names, and
  both are there whichever it picks.
