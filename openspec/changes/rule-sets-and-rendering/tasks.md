## 1. The format

- [ ] 1.1 Write `plugin/context/rules/README.md` stating the rule file format — the four frontmatter fields, their allowed values, the body's single level-one heading and its reason — and verify it names the `**Enforced by:**` line every enforced rule owes and the check that holds it
- [ ] 1.2 Update `plugin/context/README.md` to point at the format and replace its "filled by `C1b`" line with what the pillar now holds, and verify the layout test still passes

## 2. The renderer

- [ ] 2.1 Write the frontmatter parser inside `plugin/scripts/render_rules.py`: `key: value` scalars only, refusing anything else with the file and line named, and verify it parses every committed rule and rejects a nested value, a list and an unterminated block
- [ ] 2.2 Add set discovery and loading — sets are the directories under `plugin/context/rules/`, rules are the files in them, resolved from the script's own location with a `--rules-dir` override — and verify a fixture tree loads and the real tree reports the six sets
- [ ] 2.3 Add the rendering: sets alphabetically, rules alphabetically by `id` within a set, each rule's body emitted with its heading demoted to a rule heading under its set's heading, preceded by the header saying what produced the file and how to change a rule, with no timestamp and no version; verify the output ends with exactly one newline
- [ ] 2.4 Add the profile filter: an optional `--profiles`, a rule whose `applies_to` is not `always` rendered only when its profile is listed; verify on a fixture tree that the rule is absent without the profile and present with it
- [ ] 2.5 Add the command line — `--sets`, `--profiles`, `--out` with `-` for the screen — and its refusals: an unknown set exits non-zero naming the set and listing the known ones, no set at all exits non-zero, and neither writes a file; verify `uv run plugin/scripts/render_rules.py --sets git,code --out -` prints those two sets and nothing else

## 3. The six sets

- [ ] 3.1 Write the `git` set — a branch per change, conventional commit messages in English, never an AI author or co-author line, commits only in `ship` — and verify each file carries the four fields and that only the commits rule declares an enforcer
- [ ] 3.2 Write the `code` set — the check command runs before any claim of done, tests sit beside what they test, no scope beyond the task — and verify the two enforced rules name their enforcers
- [ ] 3.3 Write the `sdd` set — the change's artifacts are the brief and are re-read from disk, the proposal is the scope, a builder never ticks the task list — and verify no file names a project, a domain word or a tool
- [ ] 3.4 Write the `safety` set — destructive commands, deletions, pushes and credentials always ask the human — and verify every file declares `guard` and names the shell guard as its enforcer
- [ ] 3.5 Write the `canary` set — every answer ends with the project's canary word — and verify it declares `hook` and names the canary check of pillar 5, which `C1d` builds
- [ ] 3.6 Write the `language` set — everything committed is in English — and verify it declares no enforcer
- [ ] 3.7 Read the six sets end to end as an agent would and verify every rule is stated exactly once across all sets, each body opens with the rule as one sentence and gives its reason, and no rule restates another

## 4. The checks

- [ ] 4.1 Write the format check over every rule file — the four fields and no others, `id` unique and equal to the file name, `set` equal to the parent directory, `applies_to` either `always` or a profile that exists, `enforced_by` in the allowed vocabulary, exactly one heading, first and at level one, and an `**Enforced by:**` line whenever `enforced_by` is not `none` — and verify it fails on a temporary rule seeded with each of those faults
- [ ] 4.2 Write the set check — every set holds at least one rule, every rule belongs to exactly one set, the six expected sets are present — and verify it fails on a temporary empty set directory
- [ ] 4.3 Write the determinism checks: the same sets rendered twice are identical, a permuted list and a list with a repeat render the same bytes, and a set rendered alone matches its section when rendered beside the others; verify each fails if the renderer is made to honour the argument order
- [ ] 4.4 Commit the snapshot of every set rendered, assert the rendering matches it byte for byte, record the regeneration command in the test's docstring, and verify the test fails on a one-word edit to any rule
- [ ] 4.5 Run the private-name check over the rendered output as well as the tree, and verify it reports which halves ran
- [ ] 4.6 Run `uv run --with pytest pytest -q -rs` on the whole suite and verify every check passes with no dependency beyond pytest

## 5. The manual check

- [ ] 5.1 Append the `rule-sets-and-rendering` section to `docs/smoke.md` in the established format — what it delivers, the versions verified against, the steps that render two sets and then three, and what to expect — and verify the steps run top to bottom and produce what the section says

## 6. Close the change

- [ ] 6.1 Run the full suite and both manifest validations on the final tree and verify all pass, with the private-name test reporting both halves ran
- [ ] 6.2 Update `docs/PLAN.md` to match what landed — mark `C1b` delivered, record the rule format and what writing the six sets taught us — and verify `openspec validate --all` still passes
