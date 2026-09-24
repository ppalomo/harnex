## Why

The plugin installs and contributes nothing. The first thing it must carry is the one
kind of content every other pillar depends on: the rules. A rule is the smallest unit of
how work is done, and the plan puts a hard constraint on it — a rule is stated exactly
once, and if it is also enforced, the enforcement lives elsewhere and the rule names it.
That constraint only holds if rules have a format a check can read.

`setup` (`C1c`) cannot write a project's rules file until something can render one, and
the canary hook (`C1d`) cannot enforce a rule that has not been stated. So the rules and
their renderer come first, and they come as one change because a format with no reader is
untestable and a reader with no content is untested.

Phase: **C1b** of `docs/PLAN.md` §10. Exit criterion: every rule is stated exactly once,
and the same set list always renders the same file, byte for byte.

Pillar: **1 · Context & Memory**. The rule files are what the agent reads; the renderer is
the pillar's only script. Nothing in this change enforces anything.

## What Changes

- Define the rule file format: frontmatter `id`, `set`, `applies_to`, `enforced_by`, and
  a body whose first line is the rule stated as a sentence, followed by its reason.
- Add the six sets of `docs/PLAN.md` §7 under `plugin/context/rules/<set>/`, one file per
  rule: `git`, `code`, `sdd`, `safety`, `canary`, `language`.
- Add `plugin/scripts/render_rules.py`, which turns a list of sets — and the project's
  profiles, for rules that apply only to one — into a project's rules file,
  deterministically and with no dependency outside the standard library.
- Add the checks: the format over every rule file, the renderer's determinism, a
  committed snapshot of every set rendered, and the subset property that makes a set's
  section independent of which other sets were asked for.
- Append this change's section to `docs/smoke.md`.

## Capabilities

### New Capabilities

- `rule-sets`: how a rule is written, where it lives, what makes a set, and how a chosen
  list of sets becomes the rules file a project reads.

### Modified Capabilities

<!-- None: plugin-delivery is unchanged; this change fills a pillar it already fixed. -->

## Impact

- New: `plugin/context/rules/` with its six sets, `plugin/scripts/render_rules.py`,
  `tests/test_rule_format.py`, `tests/test_render_rules.py`, one committed snapshot.
- Changed: `plugin/context/README.md` loses its "filled by C1b" line and gains the format;
  `docs/smoke.md` gains a section; `docs/PLAN.md` records what landed.
- Unchanged: both manifests, the other four pillars, the layout check.
- Dependencies: none. The renderer is standard library only, so a hook can call it
  without paying for dependency resolution.
- Downstream: `C1c`'s `setup` calls the renderer to write `.harnex/rules.md` and records
  its hash; `C1d` enforces the `canary` rule this change states; `C3` adds profile rules
  and `C4` reads the `safety` rules into the guard's pattern lists.

## Non-goals

- No enforcement. Every rule this change states with an enforcer names a component that a
  later change builds; nothing here checks that the component exists, which is `C1d`'s
  check and would fail today by design.
- No `setup`, no project files, no hash manifest: `C1c`.
- No profiles. `applies_to` is honoured by the renderer, but the first rule that uses it
  arrives with the profiles in `C3`.
- No rule editing command and no per-project rule overrides. A project's own rules stay
  in its working instructions, as the plan settles.
