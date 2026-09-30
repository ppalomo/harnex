## 1. The check-and-facts script

- [x] 1.1 Write `plugin/scripts/verify_checks.py`: reads `check_command` from `.harnex.yml`,
      runs it, captures exit status and output, and writes a facts file under
      `.harnex/state/verify/` carrying that result plus a fingerprint of the working tree
      it ran against (reusing `apply_loop.py`'s existing fingerprint function — factor it
      into a shared helper both scripts import, rather than duplicating it). Verify: a unit
      test runs it against a fixture project with a trivial `check_command` (e.g. `true` /
      `false`) and asserts the facts file's exit status, output, and fingerprint.
- [x] 1.2 Add the Playwright step: when the project's profile is a UI stack, drive
      Playwright MCP against the running app and add its findings to the same facts file;
      when no UI profile is declared, skip the step entirely and record that nothing ran
      (design.md D2, D6). Verify: a fixture test for a UI-profile project (Playwright
      client stubbed) and one for a non-UI project, asserting the facts file's Playwright
      section is present only in the first.
- [x] 1.3 Give the script an internal-error path distinct from a failing `check_command`:
      if it crashes before the facts file is written — interpreter missing,
      `check_command` unset in `.harnex.yml`, the script itself raising — it exits
      signalling that no facts file exists, rather than writing a partial one. Verify: a
      unit test removes `check_command` from a fixture `.harnex.yml` and asserts no facts
      file is written and the script's exit communicates the internal-error case.

## 2. The verifier's extended inputs and severity

- [x] 2.1 Update `plugin/orchestration/roles/verifier.md` per the `verifier` delta spec:
      read the diff and the facts file when both are handed to it (a `verify` call), report
      where the diff does not satisfy a spec it claims to implement, report the
      check-command/Playwright facts as given, and carry a severity (`blocking` /
      `advisory`) on every finding. Leave the `propose`-time behaviour (no diff, no facts
      file, no severity distinction beyond what already exists) unchanged when neither is
      handed to it. Verify: the review's own report format documents both modes plainly
      enough that a fresh reading of the file tells them apart.
- [x] 2.2 Mirror the same content into `plugin/agents/verifier.md`, the Claude Code
      adapter. Verify: the existing correspondence test between `roles/verifier.md` and
      `agents/verifier.md` passes unchanged (it compares content, not behaviour, so an
      edit to one without the other fails it).

## 3. The reviewer role

- [x] 3.1 Write `plugin/orchestration/roles/reviewer.md` per the `reviewer-role` spec: no
      write capability, reads the diff from disk, reports code quality (bugs,
      simplification, efficiency) and not spec coherence, never blocks, always runs on the
      fixed model `opus` regardless of which builder built the code under review
      (design.md D4). Mirror it into `plugin/agents/reviewer.md`. Verify: extend the
      correspondence test (2.2) to cover this pair too, and a tool-list check that neither
      adapter grants edit, write, or command-execution capability.

## 4. `/harnex:review`

- [x] 4.1 Write `plugin/skills/review/SKILL.md`: print the advice line, read the change's
      diff, start the reviewer (always on `opus`, per 3.1 — no binding computation needed),
      and present its findings exactly as returned. Never write anything, never block,
      never require `verify` or `ship` to have run. Verify: covered by the full walkthrough
      (group 8).

## 5. `verify`'s and `ship`'s gate

- [x] 5.1 Write `plugin/scripts/ship_gate.py`: given a change directory, determines whether
      the most recent `/harnex:verify` run's review is fingerprinted to the current working
      tree and whether it contains a finding marked `blocking`; returns a clear go/refuse
      result naming the reason (no run found, stale fingerprint, or a blocking finding).
      Verify: unit tests for all three refusal cases and the pass-through case, per the
      `verify-and-ship-commands` spec's four `ship`-gate scenarios.

## 6. `/harnex:verify`

- [x] 6.1 Write `plugin/skills/verify/SKILL.md`: print the advice line, run 1's script; if
      it signals an internal error, report it and stop without starting the verifier
      (spec's internal-error requirement); otherwise start the verifier with the diff and
      the facts file, and present every finding with its severity. Record the run (its
      fingerprint and findings) where 5.1's gate can find it. Verify: covered by the full
      walkthrough (group 8).

## 7. `/harnex:ship`

- [x] 7.1 Write `plugin/skills/ship/SKILL.md`: call 5.1's gate; on refusal, report the
      reason and stop. On pass-through, show any non-blocking findings, ask the person for
      an explicit yes, and only on yes: `git commit`, push, `gh pr create` (design.md D5),
      archive the change, and sync its deltas into `openspec/specs/`, in that order. If the
      `gh` step fails, stop there and report which step failed rather than continuing past
      it (design.md's Risks). Verify: covered by the full walkthrough (group 8).

## 8. Playwright MCP in setup, and doc corrections

- [x] 8.1 Before writing it, widen the naming rule `plugin/tools/mcp/playwright.md` would
      otherwise violate: `AGENTS.md`'s "Technologies are named only in
      `plugin/tools/profiles/`" and `plugin/tools/README.md`'s matching "this is the only
      place a technology may be named" both predate `mcp/` ever holding a file — `mcp/`'s
      own "What belongs here" entry already implies naming a server, so the two sentences
      already disagreed with each other before this change, just never triggered. Edit both
      to read `plugin/tools/profiles/` and `plugin/tools/mcp/` as the two places. Then write
      `plugin/tools/mcp/playwright.md` documenting what the server is for and that it is
      project-owned, written only for a UI profile. Verify: `uv run --with pytest pytest`'s
      layout/private-name check still passes with the new file present, against the widened
      rule.
- [x] 8.2 Extend `plugin/scripts/setup.py` per the `project-setup` delta spec: survey
      `.mcp.json` for the Playwright entry, add it to the plan only when the project's
      recorded profiles include a UI stack and the entry is missing, write it only on
      explicit yes, record it in the manifest by entry, and leave every other `.mcp.json`
      entry untouched. Re-evaluate the same condition on every `/harnex:update` run.
      Verify: unit tests for a UI-profile project with no entry yet (proposed, written on
      yes), a non-UI project (never proposed), an already-present entry (left
      byte-identical), and a later profile change in each direction (design.md's Risks;
      `project-setup` spec's scenarios).
- [x] 8.3 Correct `plugin/orchestration/workflow.md`: fix `apply`'s entry, still marked "not
      yet implemented, arrives in `C3`" though delivered and archived; replace the `verify`
      and `ship` entries' "not yet implemented, arrives in `C5`" with what this change
      actually built. Verify: the file names no phase from `C1`–`C5` as not yet
      implemented.
- [x] 8.4 Update `plugin/orchestration/README.md`: its "Filled by" section to record `C5`
      delivered, mirroring how `C3`'s and `C4`'s own lines already read, and its "What is
      here" bullet list to add `../agents/reviewer.md` alongside the existing
      `../agents/verifier.md` and `../agents/builder.md` entries. Verify: both sections name
      the reviewer.

## 9. Full verification

- [x] 9.1 Run `uv run --with pytest pytest`, `claude plugin validate plugin --strict`,
      `claude plugin validate . --strict`, and `openspec validate --all`; fix anything they
      catch. Verify: all four exit 0.
- [x] 9.2 Manual walkthrough on the scratch project, recorded as this change's own
      `smoke.md`: run a real change through `explore` → `propose` → `apply` → `review` →
      `verify` → `ship`. Confirm `review`'s findings never affect `ship`; confirm `verify`'s
      severity-carrying findings are shown; confirm `ship` refuses with a named reason when
      no `verify` run exists yet, and again when the tree is deliberately dirtied after a
      `verify` run (stale fingerprint); confirm it proceeds once a fresh, clean `verify` run
      exists and the person says yes; confirm the resulting commit carries no AI author or
      co-author line. The Playwright/UI path is exercised separately, by the person, against
      their own UI-profile project (proposal's Non-goals) — not required for this task.

## 10. Plan sync

- [x] 10.1 Update `docs/PLAN.md` to match what landed, everywhere the reopened decision 4
      and the new role touch it, not only its own numbered entry:
      - §12 decision 4: name four roles (architect, builder, verifier, reviewer) instead of
        three.
      - §11: remove "a separate `reviewer` role" from the "later, not scheduled" list, mark
        `C5` **delivered**, fill in its "What it taught us" from anything this change
        learned that the design did not already predict, and correct any roadmap line that
        still describes `verify` or `ship` as not yet implemented.
      - §4: add a `reviewer` row to the role table (player, may-write, must-refuse,
        commands) and to the "What holds a role to its boundary" matrix, alongside the
        existing `architect` / `builder · Codex` / `builder · Claude subagent` / `verifier`
        columns.
      - §3: add the reviewer to Claude's actor row, alongside "architect (main session),
        verifier (fresh-context subagent), builder fallback."
      - §5: add `reviewer.md` to the repository layout's `agents/` listing, alongside
        `builder.md`, `verifier.md`.
      - §6: add a row to the ownership table for `.mcp.json` (**shared, by entry**),
        matching how `.claude/settings.json` is already documented there.
      Regenerate diagrams if the workflow's actual shape differs from what they show
      (`python3 docs/diagrams/build.py`). Verify: grep `docs/PLAN.md` for `architect,
      builder, verifier` and for every section named above — none still lists three roles
      or omits the reviewer where builder and verifier already appear.
