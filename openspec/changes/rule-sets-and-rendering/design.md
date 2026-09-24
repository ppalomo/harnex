## Context

The plugin installs and contributes nothing (`C1a`). Pillar 1 is an empty directory with
a README that promises rules. See `proposal.md` — Why for the motivation; the behaviour
this design has to satisfy is in `specs/rule-sets/spec.md`.

Two constraints from `docs/PLAN.md` shape everything below. **A rule is stated once**
(§1): if it is also enforced, the enforcement lives in pillar 4 or 5 and the rule file
names it; a rule that exists only as enforcement is a bug. And **ownership is by file**
(§6): `update` will overwrite a harness-owned file whose hash still matches what it
wrote. The rules file is harness-owned, so its bytes must be a pure function of the
project's choices — not of the clock, not of the plugin's version, not of the order the
sets were typed in.

## Goals / Non-Goals

**Goals:**

- A rule format minimal enough that writing a rule is writing a paragraph, and strict
  enough that a check can hold the "stated once, enforced elsewhere" constraint.
- A renderer whose output depends only on the chosen sets and profiles, so the hash
  manifest `C1c` writes stays meaningful.
- The six sets of §7 stated, in English, without naming a project or a technology.
- Tests that fail on a bad tree, not only pass on a good one, as `C1a` established.

**Non-Goals:**

- Enforcement of any kind. Rules here name enforcers that later changes build.
- A rule authoring command, rule overrides per project, or rule versioning.
- Reading `.harnex.yml`. The renderer takes its sets and profiles as arguments; `C1c`
  owns the file that supplies them.

## Decisions

**The rule's statement is the body's first heading, not a frontmatter field.**
A `title` field would state the rule twice: once as a field and once in the prose.
Instead the body opens with a level-one heading that *is* the rule, and the rest is the
reason. The renderer demotes that heading and emits the body verbatim. The check enforces
exactly one heading per rule file, first and at level one — which also keeps a rule short
enough to be one rule. The alternative, deriving a heading from the identifier, produces
`Canary word ends every answer` where the author meant a sentence; the format should not
degrade the prose an agent reads.

**Frontmatter is four flat fields and is parsed by fifteen lines, not by a library.**
`id`, `set`, `applies_to`, `enforced_by`, all scalar strings — the minimum-frontmatter
instinct of decision 9 applied to rules. A parser that understands only `key: value` and
refuses anything else *is* the schema check for structure, and it keeps the renderer free
of dependencies. That matters beyond tidiness: `C1c`'s setup and, later, hooks with a
three-second budget call this code, and `uv run` with a dependency to resolve is the
difference between instant and not. The cost is that the frontmatter is not YAML, only
YAML-shaped; the check makes that boundary explicit by failing on anything it cannot
parse rather than guessing.

**`id` is the file name and is unique across every set; `set` is the parent directory.**
Both fields are therefore redundant with the path, which is the point: the redundancy is
what a check compares. A rule that is moved between sets and forgets to update its field
is caught, and a rule that is copied to start another is caught by the uniqueness test
before the duplicate statement reaches a project.

**`enforced_by` is one of `none`, `guard`, `hook`, `check`, `decision`, and anything but
`none` obliges the body to carry an `**Enforced by:**` line naming the component.**
The vocabulary is the plan's. The obliged line is how the "stated once" constraint
becomes checkable in both directions: from the rule you find the code, and `C1d`'s check
walks the other way, from every `hook` rule to a hook that exists. That check fails today
on the canary rule, deliberately, and is why it belongs to `C1d` and not here.

**Set order is alphabetical, rule order within a set is alphabetical by `id`, and the
rendered file carries no timestamp and no version.** Determinism is not "the same run
twice"; it is "the same choice, byte for byte, from any direction". Honouring the order
the sets were typed in would make `.harnex/rules.md` depend on how `setup` happened to
build its argument, and a version stamp would make every plugin release look like an
edited file to `update`. Alphabetical needs no extra metadata to maintain and no ordering
field in the frontmatter. The price is that the sets read in an order nobody chose, which
costs nothing to a reader looking for a rule.

**The rendered file states only the rule statements and their reasons.** No identifiers,
no set metadata, no enforcement column. The reader of `.harnex/rules.md` is an agent
about to do work, and every line that is not a rule competes with the rules for
attention. Traceability is served the other way: the harness's own files carry the ids,
and `C4` maps `enforced_by: guard` rules to pattern lists by reading the source files,
never the rendered output.

**`applies_to` is honoured now, though no rule uses it yet.** The renderer takes an
optional profile list and drops any rule whose `applies_to` names a profile the project
did not declare. Declaring a field and ignoring it teaches the next author that fields
are decorative; five lines of filtering, exercised on a fixture tree, keep the field
real until `C3` brings the first profile rule. The check ties the field to the tree:
`applies_to` is `always` or a profile that exists under `plugin/tools/profiles/`, which
passes vacuously today and becomes a real cross-pillar link the moment profiles land.

**One committed snapshot, of every set, plus a subset property.** The plan asks for
snapshots of several combinations, but a second full snapshot would copy every rule body
into the test data twice and double the cost of editing a word. Instead one snapshot
pins the exact bytes of the whole rendering, and the smaller combinations are checked
against it by the property that makes them safe to compose: the part of the output
belonging to a set is the same whether that set was rendered alone or beside others.
That property is stronger than a second snapshot — it holds for every combination, not
for the two someone thought to record — and it is what lets `setup` offer sets freely.

**The renderer finds the rules relative to its own file, with an override for tests.**
Installed, the script sits beside the pillars inside the plugin, so `__file__` resolves
the rules directory from any working directory and without the host having to pass a
path. A `--rules-dir` override exists so the failure cases — an unknown set, an unparsable
rule, a profile rule — are exercised on fixture trees rather than by mutating the real one.

## What setup and update write in a target project

Still nothing, directly: this change delivers no command. It decides the *content* of one
file that `C1c` will write, `.harnex/rules.md`, and fixes the ownership consequence that
comes with it. That file is **harness-owned**: `setup` renders it, records its hash, and
`update` re-renders it and overwrites it while the hash still matches. The decisions above
about ordering, timestamps and version stamps exist to make that ownership workable — a
harness-owned file that changes for reasons the project did not choose is a file `update`
can only ever refuse to touch.

## Risks / Trade-offs

- **The snapshot makes every wording edit a two-file change** → the test's docstring
  carries the one command that regenerates it, so the loop is edit, regenerate, read the
  diff. The diff is the review: a rule changing is exactly the thing that should be hard
  to do by accident.
- **Frontmatter that is YAML-shaped but not YAML** will eventually meet an author who
  writes a list or a quoted string → the parser refuses rather than guesses, and the
  failure names the file and the line. If a rule ever genuinely needs structure, that is
  the signal to take the dependency, not to loosen the parser.
- **Sixteen rules written in one change is a lot of prose to get right**, and a rule
  stated badly is worse than a rule missing → the bodies stay to a few lines each, every
  one gives its reason, and the private-name check runs over the rendered output as well
  as the tree.
- **The `safety` rules describe enforcement that does not exist until `C4`**, so a
  project set up between now and then reads rules nothing checks → that is the honest
  order, and the rule bodies say what enforces them rather than claiming they are
  enforced today.

## Open Questions

- Whether `check` and `decision` as enforcement kinds survive contact with `C3` and `C5`,
  or collapse into one. Deferrable: the vocabulary lives in one constant.
- Whether the rendered file should group by set at all, or present one flat list of
  rules. Grouping is kept because `setup` asks by set and a reader should see the same
  shape they chose.
