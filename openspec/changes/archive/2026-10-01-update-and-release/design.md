## Context

See `proposal.md` for why. What exists today, and what this design builds on:

- `plugin/scripts/setup.py` (`C1c`) already implements the whole survey → plan →
  stop-on-conflict → write sequence, generically: `build_plan()` classifies every path,
  `_plan_harness_files()` already carries the exact hash-match/conflict rule a refresh
  needs (`harness-ownership` spec, "A harness-owned file is overwritten only when it
  matches the record"), `_plan_settings()` and `_plan_mcp()` already merge by entry rather
  than by whole file, and `write_atomic()` / `_plan_record()` already write each path
  atomically with the manifest last. `update.py` reuses every one of these rather than
  reimplementing the contract a second time — the same choice `C5`'s verifier extension
  made over forking a new role (that design's D1).
- `_plan_project_files()` is the one function in that chain setup uses for paths update
  must never touch (`AGENTS.md`, `CLAUDE.md`, `.harnex.yml`, `openspec/config.yaml`): it
  creates a missing one from a template, and inserts a pointer line only when
  `answers.pointer_agents` / `pointer_claude` is `True`. Passing an `Answers` with every
  approval flag `False` already routes pointer handling to the existing "KEEP, with a
  notice" branch — no change needed there. The one branch that still writes unconditionally
  is "create a project file that is missing"; see D1.
- `project-setup`'s own spec already reads "setup or update" in two requirements (the
  Playwright-entry re-evaluation and the `.env` notice), written during `C5` in
  anticipation of this change. `harness-ownership`'s regeneration contract is phrased
  generically ("any operation that refreshes a harnessed project") for the same reason.
  Neither needs a delta here (`proposal.md`'s Capabilities).
- `setup.py` already has `parse_choices`, a flat-shape reader (`C1d`, since reused by
  `canary.py`, `guard.py`, `decide.py`, and `verify_checks.py`) — but nothing today turns
  its result into the `Answers` a build-plan call needs. Setup's own skill instead reads
  `.harnex.yml` as a person would (`SKILL.md` step 1: "read `.harnex.yml` … take them as
  given") and hands the script a JSON answers document it assembled by hand. `update` has
  no session asking questions, so `update.py` needs a function that calls the existing
  `parse_choices` and builds the `Answers` itself; see D2.
- No CI exists yet (`.github/` is absent); no git tag exists; `plugin/.claude-plugin/plugin.json`
  and `.claude-plugin/marketplace.json` already carry `"version": "0.1.0"` but nothing
  checks the two agree or that either matches a release.

## Goals / Non-Goals

**Goals:**

- `update.py` is additive to `setup.py`, not a parallel implementation: one function
  (`build_plan`) still decides what happens to every path; `update.py` calls it with a
  narrower `Answers` and a mode flag, and the narrowing is enforced in code, not by
  convention alone (D1).
- A missing project-owned file, during update, is reported and skipped — never created,
  never a reason to stop refreshing harness-owned content elsewhere.
- Update's two refusal cases (`.harnex.yml` absent; present but no manifest) are checked
  before `build_plan` runs at all, so neither can be reached by accident through the
  general path-classification logic.
- CI runs, on every push and pull request, exactly the checks `AGENTS.md`'s own "Before
  committing" section already asks a person to run by hand; `pytest` and
  `openspec validate --all` actually gate, while the two `claude plugin validate --strict`
  steps are best-effort (`continue-on-error`) until a real CI run confirms the CLI installs
  cleanly in a bare runner (Risks).
- The plugin's two manifests and the pushed tag agree, by a check, not by remembering to
  edit three places.

**Non-Goals:** see `proposal.md`. In addition, at the design level: no new `.harnex.yml`
key (update needs nothing setup does not already record); no general-purpose YAML parser
(D2's reader handles exactly the flat shape setup's own template produces, nothing else);
no automatic migration tool for the old private marketplace; no semantic-versioning policy
beyond "tag the release."

## Decisions

### D1 · `build_plan` gains one mode flag; update never creates or inserts into a project file

`_plan_project_files` and `build_plan` take a `mode: Literal["setup", "update"]` parameter,
defaulting to `"setup"` so every existing caller and test is unaffected. In `"update"` mode,
the branch that currently does `Step(path, "project", CREATE, ..., body)` for a missing
project-owned path instead does `Step(path, "project", MISSING, "...", data=None)` and adds
a notice naming the path and saying setup is the command that creates it. No other branch
of `_plan_project_files` changes: pointer insertion is already gated by an approval flag
update always passes as `False`, so it already falls through to the existing "KEEP, with a
notice" branch unchanged.

This keeps the enforcement in the one place that decides what gets written, rather than in
`update.py` filtering the plan afterward — a filter could silently hide a bug that slips a
write through; a mode-gated branch cannot produce one.

*Alternative considered:* a second, parallel `_plan_project_files_for_update`. Rejected —
the two would drift the way a forked verifier role would have (`C5`'s D1); one function
with one new branch keeps the "never creates a project file" guarantee visible at its one
call site.

### D2 · `update.py` reuses `setup.py`'s existing reader, rather than adding a second one

`.harnex.yml`'s own header already states its shape is deliberately flat — "scalars, and
three lists" — precisely so that every hook and command can read it without resolving a
dependency, and `setup.parse_choices` already implements exactly that grammar (`key:
value`, `key:` followed by `  - item` lines, anything else a read error, reported the same
way a `SetupError` already is). `update.py` calls `parse_choices` directly rather than
writing a second, parallel reader — "the reader is the schema, stated once" is the same
principle the renderer already follows for the other direction. `update.py` adds only the
thin function `parse_choices` itself does not provide: building the `Answers` shape
`read_answers` already validates against from `parse_choices`'s result, with every approval
flag `False` and `adopt` empty, then calling the existing `validate_answers`.

*Alternative considered:* depending on `PyYAML` to read the real file. Rejected on decision
15 — a harness script paying for a dependency resolution before its first write is exactly
what that decision rules out, and the file was deliberately kept flat so that a minimal
reader is enough.

### D3 · Update writes after planning, with no approval gate

Setup's plan is shown and written only after an explicit yes (§6), because setup's plan can
contain things only a person can decide — creating a new project file, inserting a line,
adopting a conflict. Update's plan, once the two refusal cases (D1's missing-file notices
aside) and conflicts are excluded, contains only harness-owned content reproducible from
choices the project already recorded through setup's own yes. There is nothing left in an
update plan for a person to approve that was not already approved when the project chose
its sets, profiles and features. `update.py` therefore plans and writes in one pass; a
conflict still stops it before any write, the same as setup.

*Alternative considered:* an approval step before every update write, mirroring setup
exactly. Rejected — it would ask a question whose answer is always "yes, since I already
approved this when I ran setup," which is the harness asking rather than deriving (the same
anti-pattern `project-setup`'s "Setup offers only what the harness holds" requirement
already rules out for setup's own questions).

### D4 · Versioning is the manifest's `version` field; a git tag of the same name is the release

`plugin/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` each already
carry a `version`. Releasing is: bump both to the same value, commit, tag `vX.Y.Z`, push the
tag. A new `pytest` check (sibling to the existing layout/privacy/manifest tests) fails when
the two files disagree, and CI's release workflow fails the same way if the pushed tag's
name does not match the manifest's `version`. No new source of truth is introduced — the
tag names what the manifest already declares, it does not compute it.

*Alternative considered:* a version computed from commit count or date. Rejected — decision
16 already requires every harness-generated file to be a pure function of recorded choices
with no version stamp; the plugin's own manifest is the one place a version belongs, and
inventing a second, derived one would give two numbers that could disagree.

### D5 · CI is two workflows: check, and release

A `check` workflow runs on every push and pull request: `uv run --with pytest pytest`,
`claude plugin validate plugin --strict`, `claude plugin validate . --strict`, and
`openspec validate --all` — exactly `AGENTS.md`'s own "Before committing" list, so a
contributor who only ever ran it by hand sees nothing new required of them. A `release`
workflow runs on a pushed `vX.Y.Z` tag: re-runs the same checks (a tag is not trusted
merely because the commit it points to once passed CI earlier), then publishes — the exact
publish step (a GitHub release, or nothing beyond the tag itself, since the marketplace is
read directly from the repository per §6's "why a plugin" close) is a task-level decision,
not a design one, since either way changes no spec.

### D6 · The real-project migration is manual, and is the change's own proof that update works

One project already registered on the old private marketplace is moved to `harnex` by
hand: install the plugin, run `/harnex:setup`'s adoption path, confirm its own files are
untouched except the pointer lines approved, then run `/harnex:update` and confirm nothing
unexpected changes. This is not a script this change builds — it is `C6`'s own exit
criterion exercised on a project that was never part of harnex's own test fixtures, the same
role `C1c`'s hand-run adoption walkthrough and `C5`'s scratch-project walkthrough already
played for their own changes. What it finds, if anything, is recorded in `docs/PLAN.md`'s
"What it taught us" convention, not guessed at here.

## What setup and update write

No new path is added to §6's ownership table. `update.py` writes a strict subset of what
`setup.py` can write — `.harnex/rules.md`, `.harnex/state/.gitignore`, the floor's entries in
`.claude/settings.json`, and the Playwright entry in `.mcp.json` when it is already present
and merely needs refreshing — and never `AGENTS.md`, `CLAUDE.md`, `.harnex.yml`, or
`openspec/config.yaml`, which stay setup's alone (D1). `.harnex/manifest.json` is written by
both, last, as it already is.

`.github/workflows/` is new, but it is not part of this table: it is harnex's own
repository tooling (D5), never generated into a harnessed project the way `AGENTS.md` or
`.harnex/rules.md` are.

## Guarantees

| Guarantee | Kind | What happens when it fails |
|---|---|---|
| Update never creates or writes into a project-owned file | Prevention (the branch that would write one does not exist in `"update"` mode — D1) | A test asserts no `Step` with `owner == "project"` ever carries `data is not None` when `build_plan` runs in `"update"` mode; a regression here fails that test before it fails anyone's project |
| A harness-owned file is overwritten only when its hash matches the record | Prevention + detection (reused unchanged from `_plan_harness_files`, `harness-ownership` spec) | Same as setup's own guarantee: an edited file stops the run and is named, never guessed at |
| Update refuses without a manifest, or without `.harnex.yml` | Prevention (checked before `build_plan` runs, not left to fall out of path classification — D1/D2) | If the check were skipped, a project with no manifest would have its harness-owned paths treated as simply absent and silently created, which is exactly the "guessing" `harness-ownership`'s own spec forbids; a dedicated test for each refusal keeps the check in place |
| Writes are atomic and the manifest is written last | Prevention (reused unchanged from `write_atomic` / `_plan_record`) | Same as setup's own guarantee: an interruption leaves no partial file, and a re-run recovers by content |
| The two plugin manifests and a release tag agree | Detection (a `pytest` check, and the release workflow's own check — D4) | A mismatch fails the check before it fails a `claude plugin install`; nothing silently ships a mismatched version |
| `pytest` and `openspec validate --all` run on every push and pull request | Detection (the `check` workflow — D5) | A contributor who skips running them locally still cannot merge a failing change on these two; the workflow failing to run at all (misconfigured YAML, say) is caught the same way any other CI outage is — by branch protection refusing to merge without a passing required check. The two `claude plugin validate --strict` steps are deliberately `continue-on-error: true` (Risks) — this guarantee does not yet cover them |

## Risks / Trade-offs

- **[Risk] The hand-rolled `.harnex.yml` reader (D2) diverges from what setup's own
  template renders, the moment someone edits `render_template`'s `harnex.yml` template
  without updating the reader** → **Mitigation:** a round-trip test renders the template
  through `setup.py` and reads it back through `update.py`'s reader, asserting the same
  `Answers`; it fails the moment the two disagree, rather than only when a real project's
  file trips the reader.
- **[Risk] A person edits `.harnex.yml` by hand into something still valid YAML but outside
  the flat shape the reader accepts (a nested mapping, say)** → **Mitigation:** named as a
  read error, reported the same way an unreadable answers document already is in setup —
  not a crash, and not a silent partial read.
- **[Risk] CI's `check` workflow needs network access for `jev`'s live backend or
  Playwright's download, and either is unavailable in the runner** → **Mitigation:** the
  repository's own checks already run against the `mock` decision backend and `C5`'s
  stubbed Playwright step (that design's D2); nothing CI runs depends on a live credential
  or a real browser download.
- **[Risk] The manual version bump (D4) is forgotten in one of the two manifest files** →
  **Mitigation:** the new `pytest` check fails locally before a release is attempted, and
  the release workflow fails again independently if a mismatched tag is pushed anyway.
- **[Risk] The real-project migration (D6) surfaces a gap this change's own tests did not
  anticipate** → **Mitigation:** exactly why it is scheduled as this change's own exit
  proof rather than skipped; a finding becomes a recorded lesson (`docs/PLAN.md`'s
  established convention) and, if it changes a requirement, a follow-up change — not a
  silent workaround inside this one.

## Migration Plan

Additive for every project that does not yet run the new plugin version: nothing about an
existing harnessed project changes until it installs the updated plugin and runs
`/harnex:update` for the first time, at which point only harness-owned paths and entries
move, and only if the harness's own content changed since that project's last refresh. No
rollback concern beyond the plugin's own version — a project can keep running an older
installed version indefinitely, since `update`'s own absence changes nothing (§6, "outside
a harnessed project the plugin does nothing" extends naturally to "a plugin version a
project never updates to changes nothing in that project either").

## Open Questions

- Whether the release workflow itself creates the `vX.Y.Z` tag and pushes it on a version
  bump landing on the default branch, or a person tags and pushes by hand and the workflow
  only reacts to the tag. Either answers D4 and D5 the same way at the spec level (the tag
  and the manifest must agree); which one is simpler to operate is a task-time call, left
  to `tasks.md`.
