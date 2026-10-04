## 1. The detection-and-bump script

- [x] 1.1 Create `plugin/scripts/version_bump.py` (PEP 723 header, no dependencies,
  matching `ship_gate.py`'s own style) with a `detect(project)` function that reads the
  project's root `.claude-plugin/marketplace.json`, resolves its single `plugins[]`
  entry's `source`, reads that plugin's `.claude-plugin/plugin.json`, and returns a
  `found: True` result (manifest paths, `name`, `current_version`, and the three
  candidate `X.Y.Z` strings for patch/minor/major) only when exactly one entry exists and
  its `name`/`version` agree with the plugin manifest's own — `found: False` with a short
  reason for every other case (no marketplace file, zero or multiple entries, an
  unresolved `source`, a disagreement). Verify with unit tests covering every case in
  `tests/test_version_bump.py`, following `tests/test_ship_gate.py`'s fixture style.
- [x] 1.2 Add a `bump(project, level)` function that re-runs `detect`, refuses (raising a
  clear error) if it no longer finds the same single, agreeing manifest, and otherwise
  writes the chosen candidate version into both `plugin.json`'s `version` and the
  marketplace entry's `version` — preserving each file's existing key order via a
  parsed-JSON round trip, and using the same temporary-file-then-`os.replace` atomic
  write `ship_gate.record` already uses. It SHALL NOT touch the marketplace's own
  top-level `metadata.version`. Verify with a test asserting only the `version` field
  changed in each file (a line-level diff against the original fixture content) for
  each of `patch`/`minor`/`major`, and a test asserting `metadata.version` is untouched.
- [x] 1.3 Add a `main()` CLI with `detect --project <root>` and
  `bump --project <root> --level patch|minor|major` subcommands, each printing one JSON
  object to stdout (mirroring `ship_gate.py`'s `argparse` structure), `detect` always
  exiting 0 and `bump` exiting 1 with a plain JSON error when its re-detection fails.
  Verify by running both subcommands via `subprocess` against a fixture project in a new
  test, asserting stdout parses as the expected JSON and the exit code matches.

## 2. Teach `/harnex:ship` to ask and apply the bump

- [x] 2.1 In `plugin/skills/ship/SKILL.md` section 2.1 (the gated path) and section 3.1
  (the direct path), add a step that runs
  `uv run "${CLAUDE_PLUGIN_ROOT}/scripts/version_bump.py" detect --project .` before the
  existing confirmation ask, and reads its `found` field.
- [x] 2.2 Extend section 2.2's (and 3.1's) confirmation ask: when `detect` reported
  `found: true`, the same turn that asks for the person's explicit yes also asks the
  version-bump question — one short explanation of `X.Y.Z`, and four choices (no bump,
  patch, minor, major) each showing the concrete candidate version `detect` returned.
  When `found: false`, the ask is unchanged from today.
- [x] 2.3 In section 2.3 (and 3.2), before `git add -A`/`git commit`: when the person
  agreed to ship and chose a level other than "no bump," run
  `uv run "${CLAUDE_PLUGIN_ROOT}/scripts/version_bump.py" bump --project . --level <level>`
  so the manifest changes are staged and committed in the same commit `ship` was already
  making. When the person declined to ship, or chose no bump, skip this entirely — no
  write happens.
- [x] 2.4 In section 4 (Finish), add: when a bump was made, state the exact
  `git tag vX.Y.Z` and `git push origin vX.Y.Z` commands for the person to run once the
  pull request merges; say nothing about a tag otherwise.
- [x] 2.5 Add a line to `plugin/skills/ship/SKILL.md`'s "What this skill never does" list:
  cut or push a release tag, or open a GitHub release, on its own.

## 3. Documentation

- [x] 3.1 Update `docs/releasing.md` steps 1–3 (bump both manifests, run the check
  command, commit the bump) to say they are normally already done by `/harnex:ship`'s
  version-bump question and its own commit, and are manual steps only for a release cut
  outside `ship`. Steps 4–5 (tag, push) are unchanged — still the person's own manual
  step, after the pull request merges.
- [x] 3.2 Add `../scripts/version_bump.py` to `plugin/orchestration/README.md`'s "What is
  here" list, one line, alongside `ship_gate.py`'s own entry.
- [x] 3.3 Add this change's section to `docs/smoke.md`: the manual steps to run
  `/harnex:ship` against a scratch project carrying a plugin manifest and confirm the
  version-bump question appears, a chosen bump lands in the commit, and the final report
  names the tag/push reminder; and against a scratch project with no manifest, confirming
  nothing changes.

## 4. Close out

- [x] 4.1 Run `uv run --with pytest pytest`, `claude plugin validate plugin --strict`,
  `claude plugin validate . --strict`, and `openspec validate --all`, and confirm all
  pass.
- [x] 4.2 Update `docs/PLAN.md` with a new `C8 · ship asks the version bump` roadmap
  entry (Delivers / You try it / Tests / Exit, matching the existing phases' own format),
  and mark `C6`'s exit notes as no longer owing the tag question to a future change — it
  is this one.
