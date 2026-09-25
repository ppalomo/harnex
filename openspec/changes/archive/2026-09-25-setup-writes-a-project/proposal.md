## Why

The plugin installs and holds rules, and no project can use either. Nothing yet writes
the handful of files that turn a checkout into a harnessed project, and nothing records
what the harness wrote — so there is no way to try a rule in anger, and no way for a later
release to refresh what it owns without guessing.

This is also the change where the hardest contract in the plan is settled: **ownership**.
`update` (`C6`) can only refresh a file it is sure it wrote, and the guard (`C4`) can only
be a second layer if the first one — the permission floor — is already in every project.
Both need the generation metadata and the merge rules that setup establishes. Adoption is
part of the same contract: a project that already has its own `AGENTS.md`, `CLAUDE.md`,
settings and OpenSpec config must be harnessed by the same command, without a byte of its
own changing unless the owner said yes.

Phase: **C1c** of `docs/PLAN.md` §11. Exit criterion: a new project and an existing one
are both set up in one command each; a second setup changes nothing; no project-owned byte
changes without an explicit yes.

Pillars: **2 · Action & Tools** (the setup command, its skill and its script, and the
generation metadata they keep), **1 · Context & Memory** (the templates for the project's
own context files and the two pointer lines), **4 · Control & Guardrails** (the permission
floor and its entry-level merge). Three components, three pillars, one command.

## What Changes

- Add `/harnex:setup`: one skill asks the questions, and `plugin/scripts/setup.py` does
  every deterministic step, so the whole sequence is testable without a session. Standard
  library only, as every harness script is.
- Add the templates for the files a project owns — `AGENTS.md`, `CLAUDE.md`, `.harnex.yml`
  and the OpenSpec config — and the two pointer lines: a sentence in `AGENTS.md` telling a
  tool without an import syntax to read the rules file, and the two `@` imports in
  `CLAUDE.md`.
- Implement the **survey → plan → stop on conflict → write** sequence of §6: classify every
  target path as absent, harness-generated, project-owned or foreign; print one line per
  path; refuse to write anything while a conflict stands; write each file to a temporary
  sibling and rename it atomically, metadata last.
- Ask for profiles, sets, features, canary word and decision backend, offering only what
  the plugin actually holds, and record the answers in `.harnex.yml` under the keys the
  plan fixes.
- Render `.harnex/rules.md` by calling `C1b`'s renderer, and record its hash.
- Add the permission floor, `plugin/control/floor.json`, and merge its entries into
  `.claude/settings.json` **by entry**, recording exactly the entries written; report — and
  refuse to resolve — any project entry that undercuts the floor, and warn about permission
  modes that bypass it.
- Add the committed generation metadata at `.harnex/manifest.json` and the self-ignoring
  `.harnex/state/`, and fix the whole regeneration contract here: hash match before
  overwrite, conflict before write, recovery by content after an interruption, a fresh clone
  recognised through the committed metadata, and a refusal when harness files exist without
  it.
- Make setup idempotent: a second run on an unchanged project plans "nothing to do" and
  writes nothing, including no metadata rewrite.
- Restate `plugin/control/README.md` in the terms of §9 — a floor and a guard, two layers
  with different promises — dropping "permissions per role" and "it never fails open".
- Name the floor in the four `safety` rules that today name only the guard, so each rule
  says which layer gives which guarantee.
- Append this change's section to `docs/smoke.md`.

## Capabilities

### New Capabilities

- `project-setup`: how one command brings a project — new or already working — to a
  harnessed state: what it asks, what it surveys, the plan it prints, what stops it, what
  it creates, what it only proposes, and why running it again changes nothing.
- `harness-ownership`: which paths and entries belong to the harness rather than to the
  project, the committed record of what was generated, and the contract every later
  regeneration obeys — overwrite only what matches, stop on an edit, write atomically,
  recover by content, refuse to guess.
- `permission-floor`: the minimum permission entries a harnessed project carries so that
  protection does not depend on a hook being alive, what they cover, how they merge with
  the project's own, and what is reported when a project entry undercuts them.

### Modified Capabilities

- `plugin-delivery`: the requirement that the plugin contributes nothing and a session
  behaves as before. The plugin now contributes a command, so the guarantee moves from
  "contributes nothing" to "does nothing in a project that has not run setup" — decision
  19, and the property every later hook depends on.

## Impact

- New: `plugin/skills/setup/SKILL.md`, `plugin/scripts/setup.py`, `plugin/context/templates/`, `plugin/control/floor.json`, and
  the tests for the survey, the plan, the writes, adoption, idempotence, interruption and
  the floor merge.
- Changed: `plugin/control/README.md` restated and no longer "filled by C4" alone;
  `plugin/tools/README.md` and `plugin/context/README.md` lose their "filled by C1c" lines;
  the four `safety` rules name the floor; `docs/smoke.md` gains a section; `docs/PLAN.md`
  records what landed.
- Unchanged: the renderer, which this change calls and does not touch; the rule files'
  format; both plugin manifests except the version they already declare.
- Dependencies: none added. `setup.py` imports the renderer directly.
- Downstream: `C1d`'s hook reads the `.harnex.yml` this change writes and is inert without
  it; `C2`'s commands read `decision_model` from it; `C4` regenerates the floor from the
  guard's own pattern lists and must produce the same entries; `C6`'s `update` implements
  the contract fixed here and is tested against a project this change set up.
- Assumption recorded: the plugin holds no profile and no feature yet — profiles arrive
  with `C3` and the first feature with `C4` — so setup offers neither question today and
  records both keys as empty lists. The snapshot matrix the plan describes "for each profile
  combination" is therefore one snapshot per rule-set choice until `C3` adds the first
  profile, and the question is written so that adding one needs no change to setup.

## Non-goals

- No `update` command. The contract is fixed and tested here; the command that re-runs it
  is `C6`.
- No guard. The floor is written and merged, but nothing classifies a command before it
  runs; that is `C4`, which also takes over generating the floor from the guard's patterns.
- No canary hook. Setup asks for the word and records it; the hook that reads it is `C1d`.
- No decision model. Setup records which backend the project chose and calls none; the
  client arrives in `C2`.
- No profiles, and so no technology named anywhere in this change.
- No rule editing, no per-project rule overrides, no uninstall command, and no migration
  from the old private marketplace — that is `C6`.
