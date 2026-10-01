## 1. `build_plan` gains an update mode

- [x] 1.1 Add a `mode: Literal["setup", "update"]` parameter to `_plan_project_files` and
      `build_plan` in `plugin/scripts/setup.py`, defaulting to `"setup"`. In `"update"`
      mode, a missing project-owned path (`AGENTS.md`, `CLAUDE.md`, `.harnex.yml`,
      `openspec/config.yaml`) is reported with a notice naming the path and saying setup
      creates it, instead of the existing `CREATE` step (design.md D1). Every other branch
      is unchanged. Verify: existing `tests/test_setup_survey.py` and
      `tests/test_setup_write.py` pass unchanged (default mode); a new test calls
      `build_plan(..., mode="update")` on a project missing `AGENTS.md` and asserts no
      `Step` for that path carries `data is not None`, and that a notice names it.
- [x] 1.2 Add a test asserting the general guarantee, not just one fixture: for every
      `Step` `build_plan` produces in `"update"` mode across a matrix of survey states
      (nothing present, everything present and current, a project file missing, a harness
      file edited by hand), `owner == "project"` never has `data is not None`. Verify: the
      test fails if 1.1's branch is ever reverted or bypassed.

## 2. `.harnex.yml` reader

- [x] 2.1 Add a reader in `plugin/scripts/update.py` (or a shared module both scripts
      import, if that reads cleaner) that parses the flat shape `.harnex.yml`'s own header
      documents — `key: value` and `key:` followed by `  - item` lines — into the same
      values `read_answers` already validates, with every approval flag `False` and
      `adopt` empty (design.md D2). Any other construct is a read error, reported the same
      way a `SetupError` already is. Verify: a unit test feeds it the real `.harnex.yml` in
      this repository and asserts the parsed values match; a second test feeds it a
      deliberately malformed file (a nested mapping) and asserts a clear error, not a crash
      or a silent partial read.
- [x] 2.2 Add the round-trip test design.md's Risks names: render `.harnex.yml` through
      `setup.py`'s own `render_template` for a representative set of answers, read it back
      through 2.1's reader, and assert the result equals the original `Answers` (approvals
      aside, which setup's render never varies). Verify: the test fails if the template and
      the reader ever disagree about the file's shape.

## 3. `update.py`

- [x] 3.1 Write `plugin/scripts/update.py`: reads `.harnex.yml` (2.1) and
      `.harnex/manifest.json` (`setup.py`'s existing `read_manifest`); refuses with a
      named reason, writing nothing, when `.harnex.yml` is absent (points to setup) or
      present with no manifest (points to setup's adoption); otherwise calls
      `setup.build_plan(..., mode="update")`, stops on any conflict the same way setup's
      CLI already does, and otherwise applies the plan (`setup.apply_plan`,
      `write_atomic`) in one pass, no approval gate (design.md D3). Reports every path it
      touched, the way setup already reports its plan. Verify: unit tests for both refusal
      cases, for a conflict (an edited harness file) stopping without writing, and for a
      clean run rewriting `.harnex/rules.md` after a rule changed and leaving everything
      else byte-identical.
- [x] 3.2 Verify an interrupted update recovers by content: a test writes one harness file
      to its new content and stops before the manifest write (simulating an interruption),
      then runs update again and asserts it completes, with every path ending in the same
      state an uninterrupted run would reach. Verify: the test (`harness-update` spec's
      fresh-clone and interruption scenarios, reusing `harness-ownership`'s existing
      interruption test pattern from `C1c` as a template).
- [x] 3.3 Verify a fresh clone updates unaided: a test clones (or simulates a clone of) a
      harnessed project — committed paths present, `.harnex/state/` absent — and asserts
      `update.py` restores `.harnex/state/.gitignore`, asks nothing, and reports every
      other committed path unchanged. Verify: the test passes without any input beyond the
      project root.

## 4. `/harnex:update`

- [x] 4.1 Write `plugin/skills/update/SKILL.md`: state what the command does and does not
      do (no questions, no project-file writes — point to `/harnex:setup` for either),
      run `update.py`, and present its report plainly, including every notice (a missing
      pointer line, a missing project file, a Playwright entry not yet approved). Verify:
      a fixture run against this repository's own `.harnex.yml` produces a report with
      "nothing to do" (nothing in this repository is out of date when the task is done).

## 5. Versioning

- [x] 5.1 Add a test to `tests/test_manifests.py` asserting
      `plugin/.claude-plugin/plugin.json`'s `version` equals the `harnex` plugin entry's
      `version` inside `.claude-plugin/marketplace.json` (design.md D4). Verify: the test
      fails if either file is bumped alone, passes today since both already read `0.1.0`.
- [x] 5.2 Document the release steps (bump both manifests to the same version, commit, tag
      `vX.Y.Z`, push the tag) in `AGENTS.md` or a short `docs/releasing.md` it points to —
      a person tags by hand (design.md's Open Question, resolved here: manual tag, CI
      reacts to it rather than creates it, since a human decision to cut a release should
      not be inferred from a commit alone). Verify: the document names every step in order
      and the command for each.

## 6. CI

- [x] 6.1 Add `.github/workflows/check.yml`: on every push and pull request, run
      `uv run --with pytest pytest`, `claude plugin validate plugin --strict`,
      `claude plugin validate . --strict`, and `openspec validate --all` (design.md D5,
      mirroring `AGENTS.md`'s "Before committing" list exactly). Verify: pushed to a
      branch and observed green in the repository's Actions tab; the manifest-validation
      steps' own skip-when-absent behaviour (`AGENTS.md`'s "Tests" section) does not apply
      here since the runner installs the CLI — if it cannot be installed in CI, the
      workflow installs it rather than silently skipping validation that a contributor's
      own machine would have run.
- [x] 6.2 Add `.github/workflows/release.yml`: triggered on a pushed `vX.Y.Z` tag, re-runs
      6.1's checks, then asserts the tag name matches both manifests' `version` (5.1's
      check, generalised to the tag) and publishes (a GitHub release at minimum). Verify:
      tested against a throwaway pre-release tag before `v0.1.0` itself is cut, confirming
      a mismatched tag fails the workflow rather than publishing anyway.

## 7. README

- [x] 7.1 Rewrite `README.md` for a stranger: drop the "status: early" / "planned"
      framing, document all five commands plus `setup` and `update` as delivered, add the
      "verified against" table (Claude Code, Codex CLI, OpenSpec versions this release was
      tested with — `plugin-delivery` delta spec), and order the installation section so
      following it start to finish reaches a harnessed project with no other document
      needed. Verify: a fresh reading against the `plugin-delivery` delta's two new
      scenarios — the versions are stated, and every step a stranger needs is present.
- [x] 7.2 Update `docs/smoke.md` with an update section: steps to change a rule, bump the
      version, refresh the plugin, run `/harnex:update`, and confirm only
      `.harnex/rules.md` and the manifest changed; edit `.harnex/rules.md` by hand and run
      update again, confirming it stops and names the file; interrupt it and confirm a
      second run completes (`AGENTS.md`'s own "Tests" convention of one section per
      change). Verify: the section is runnable by someone who has not read this change's
      other artifacts.

## 8. Real-project migration

- [ ] 8.1 Migrate one project currently on the old private marketplace: install `harnex`,
      run `/harnex:setup`'s adoption path, confirm its own files are untouched except the
      pointer lines explicitly approved, then run `/harnex:update` and confirm it reports
      nothing unexpected. Record what the migration needed — and anything this change's
      design did not anticipate — the same way `C1c` and `C5` recorded their own hand-run
      walkthroughs (design.md D6). Verify: the project's own git history shows the
      migration commit, and this change's own "What it taught us" (task 10) names any gap
      found.
- [ ] 8.2 Remove that project's registration from the old private marketplace once 8.1's
      `/harnex:update` run confirms a clean state. Verify: the old marketplace's listing no
      longer names the project.

## 9. Full verification

- [x] 9.1 Run `uv run --with pytest pytest`, `claude plugin validate plugin --strict`,
      `claude plugin validate . --strict`, and `openspec validate --all`; fix anything they
      catch. Verify: all four exit 0.
- [ ] 9.2 Tag `v0.1.0` per 5.2's steps, and confirm 6.2's release workflow passes on the
      pushed tag. Verify: the tag is visible on the repository and the workflow run is
      green.

## 10. Plan sync

- [x] 10.1 Update `docs/PLAN.md` to match what landed:
      - §11: mark `C6` **delivered**, fill in "What it taught us" from 8.1's migration
        findings and anything else this change's own verification surfaced that its
        design did not already predict.
      - §6: the "Update, whenever harnex changes" paragraph loses its forward-looking
        phrasing now that `/harnex:update` is real, and the ownership table gains nothing
        new (design.md: no new path) but is checked against what `update.py` actually
        reads and writes.
      - §2: goal 3 ("a `setup` that generates everything a project needs, and an `update`
        that refreshes what is the harness's without touching what is the project's") is
        now met in full; note it if the goal's own wording needs correcting against what
        was actually built.
      - §14 Risks: the "Codex plugin behaviour" and "Jev is alpha" risks are unaffected;
        add a line if CI or the migration surfaced a new one worth tracking.
      Regenerate diagrams if the roadmap's own shape changed
      (`python3 docs/diagrams/build.py`). Verify: grep `docs/PLAN.md` for `C6` — no
      section still calls it unscheduled or "not yet implemented," and the roadmap table
      of contents (if `06-roadmap` changed) matches the regenerated diagram.
