## 1. The templates and the pointer lines

- [ ] 1.1 Write `plugin/context/templates/pointer-agents.md` and `plugin/context/templates/pointer-claude.md`, each holding only the exact line the harness needs in that entry file and a comment saying where it goes, and verify the two files are the only place either line is stated
- [ ] 1.2 Write the `AGENTS.md` template — a thin brief a project fills in, with the placeholder where the pointer line is composed in and no project noun anywhere — and verify the private-name check passes over it and no sentence assumes a stack
- [ ] 1.3 Write the `CLAUDE.md` template carrying nothing but the pointer line's two imports and a sentence saying the project's own instructions belong in `AGENTS.md`, and verify a rendered copy imports both files by the paths the plan fixes
- [ ] 1.4 Write the `.harnex.yml` template and the OpenSpec config template — the config carrying the harness's artifact rules and an empty project context for the project to fill — and verify `openspec validate --all` runs in a scratch project created from it
- [ ] 1.5 Add the `{{token}}` substitution helper with its refusal for an unreplaced token, and verify every template renders with the answers of a default project and that a missing answer fails loudly rather than leaving the token in the file

## 2. The project's choices

- [ ] 2.1 Write the reader for `.harnex.yml` inside `plugin/scripts/setup.py` — flat `key: value` scalars, the three lists as `- item` lines, comments and blank lines ignored, quoted scalars accepted, everything else refused with the file and line named — and verify it reads a file the writer produced and rejects a nested mapping, an anchor, a tab-indented list and a duplicate key
- [ ] 2.2 Write the writer for the same shape, emitting the seven keys the plan fixes in a fixed order, and verify a round trip through the reader returns the same answers and that writing the same answers twice produces identical bytes
- [ ] 2.3 Add the answers document the script is driven by — the seven choices plus the per-insertion approvals — with its validation: an unknown set, an unknown profile or an unknown feature refused before any survey, naming what the harness holds; verify each refusal exits non-zero and touches nothing

## 3. The survey

- [ ] 3.1 Add the record reader for `.harnex/manifest.json` with its `format` check, and verify an absent record, an unreadable one and one of an unknown format are each distinguished and reported
- [ ] 3.2 Implement the survey's four classes — absent, generated, current, project-owned, unaccounted for — computed from the record and the bytes on disk, and verify on fixtures that a hash match, a byte-identical file with a stale record, and a file matching neither are classified apart
- [ ] 3.3 Implement conflict detection over the survey — an unaccounted-for harness path, an unparsable permission file, a record missing while harness paths exist — and verify every conflict in a fixture is reported in one run rather than one per run

## 4. The plan

- [ ] 4.1 Implement `setup.py plan --answers <file|->`: one line per path with the action intended, a machine-readable result beside the human lines, and no write of any kind; verify on a fixture project that every surveyed path appears exactly once and that the working tree is byte-identical afterwards
- [ ] 4.2 Make the plan of an unchanged, already harnessed project say "nothing to do" and verify it lists every path as unchanged and proposes no write, including no rewrite of the record
- [ ] 4.3 Make a plan carrying a conflict exit non-zero with every conflict named and the resolution for each, and verify no write is proposed even for the paths that have no conflict

## 5. The floor

- [ ] 5.1 Write `plugin/control/floor.json` — every entry naming the rule it comes from, its list and its pattern in the host's syntax, plus `guard_only` entries with their reason — covering the four `safety` rules and the deny entries on reading credential files, and verify each pattern against the host's documented permission syntax
- [ ] 5.2 Record the answer to the plan's open question in `docs/decisions/` — which patterns the host's syntax expresses, which stay guard-only and why, and the host version checked — and verify `docs/PLAN.md` §13 is updated to point at it in task 10.2
- [ ] 5.3 Implement the merge into `.claude/settings.json`: parse, add the floor's entries to `permissions.deny` and `permissions.ask` if absent, write only if the parsed result differs, record exactly the entries written; verify a project file with its own entries keeps every one of them and a second merge writes nothing at all
- [ ] 5.4 Implement the overlap notice — a project `allow` entry equal to or a prefix generalisation of a floor entry, anything else broad reported as broad, and a warning for a permission mode that bypasses permissions — and verify it reports `Bash(git *)` against the floor's `git push` entry, reports a bare tool entry, says the floor still applies because of the host's rule order, does not report an unrelated allow, and never stops the run
- [ ] 5.5 Restate `plugin/control/README.md` in the terms of §9 — a floor and a guard, what each guarantees, what defeats each, dropping "permissions per role" and "it never fails open" — and verify the layout test's pillar checks still pass and the file names the floor this change adds
- [ ] 5.6 Reword the four `safety` rules so each names both layers and the kind of guarantee each gives, and verify the rule format check and the rendered snapshots are regenerated and pass

## 6. The writes

- [ ] 6.1 Implement the atomic write — temporary sibling then replace — and the fixed write order, project files before the rules file, the state directory, the permission merge and the record last; verify a test that interrupts after each step and re-runs completes to the same tree as an uninterrupted run
- [ ] 6.2 Render `.harnex/rules.md` by importing `C1b`'s renderer with the chosen sets and profiles, and verify the result is byte-identical to running the renderer's own command line with the same choices
- [ ] 6.3 Create `.harnex/state/` with the file that ignores its own directory, and verify the project's `.gitignore` is untouched — absent stays absent — and that `git status` in a scratch project reports nothing under the state directory
- [ ] 6.4 Write the record last, with sorted keys and no stamp of any kind, and verify two runs of the same answers on two different machines' paths produce the same record bytes
- [ ] 6.5 Implement `setup.py write` as a re-survey followed by the writes, refusing on any conflict before the first write, and verify an answers document approved against a plan that has since gone stale writes nothing and says why

## 7. The project's own files

- [ ] 7.1 Create each project-owned file from its template when absent, never when present, and verify a fixture whose `AGENTS.md` and `CLAUDE.md` already exist ends byte-identical except for an approved insertion
- [ ] 7.2 Implement the pointer-line insertion: only when the answers carry the approval for that file, at the position the template's comment states, never anywhere else; verify the script cannot write a project-owned file by any other path and that the insertion is idempotent
- [ ] 7.3 Implement the declined-insertion notice — detected from the line's absence, so nothing is remembered — and verify it is repeated on a later plan and names which tool will not read the rules
- [ ] 7.4 Implement adoption of an unaccounted-for harness path: show the difference against what the harness would write, replace only when the answers carry that approval, and verify the file is left alone without it and replaced with it

## 8. The command and the skill

- [ ] 8.1 Write `plugin/skills/harnex-setup/SKILL.md` with the procedure — the questions in order, only those the harness has something to offer for, the defaults the plan fixes, what to show, what counts as a yes, and the refusal to approve on the person's behalf — with the minimum frontmatter, and verify `claude plugin validate plugin --strict` passes
- [ ] 8.2 Write `plugin/commands/setup.md` as the thin entry point that invokes the skill, and verify the installed plugin lists one command and one skill and that `/harnex:setup` is offered in a session
- [ ] 8.3 Update `plugin/tools/README.md` and `plugin/context/README.md` to say what the pillar now holds instead of "filled by `C1c`", and verify the layout test passes and neither README names a technology

## 9. The checks

- [ ] 9.1 Add the survey and plan tests over fixture projects — empty, harnessed, harnessed and edited, adopted, foreign rules file, unparsable settings, record missing with harness files present — and verify each fixture asserts what is kept, what is asked and what stops the run before any write
- [ ] 9.2 Add the write tests: a full run on an empty project against committed snapshots for each rule-set choice, a second run byte-identical to the first including the record, and a fresh clone recognised as already harnessed; verify the snapshots' regeneration command is recorded in the test's docstring
- [ ] 9.3 Add the interruption tests — the run stopped after each write and re-run to completion — and verify no path is ever left partially written and no step is redone that was already correct
- [ ] 9.4 Add the floor tests: every rule declaring `guard` enforcement resolves to at least one floor entry or a recorded `guard_only` reason, the merge preserves a project's entries, the undercut check's table, and an unparsable settings file stops the run; verify the coverage test fails when an entry is deleted from the floor
- [ ] 9.5 Run the private-name check over the templates, the floor and every snapshot this change adds, and verify it reports both halves ran
- [ ] 9.6 Run `uv run --with pytest pytest -q -rs` on the whole suite and verify every check passes with no dependency beyond pytest and no network

## 10. Close the change

- [ ] 10.1 Append the `setup-writes-a-project` section to `docs/smoke.md` — the empty scratch project, the second run, the existing project with its own entry files and settings, the fresh clone, the declined pointer line — with the versions verified against, and verify the steps run top to bottom and produce what the section says
- [ ] 10.2 Update `docs/PLAN.md` to match what landed — `C1c` delivered, the record's shape, the answer to the permission-syntax open question, and what setting a project up taught us — and verify `openspec validate --all`, `claude plugin validate plugin --strict` and `claude plugin validate . --strict` all pass and the diagrams are regenerated if the layout changed
