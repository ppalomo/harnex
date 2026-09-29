## 1. The shared pattern source and the generated floor

- [x] 1.1 Write `plugin/control/guard/patterns.yaml`, transcribed exactly from what
      `plugin/control/floor.json` already commits to, and nothing else (design.md, D2):
      - Every `entries` row becomes a `floor: yes` entry, carrying that row's own
        `pattern`, `list`, and `rule`, across all five rule ids
        (`credentials-never-leave-the-machine`, `pushes-ask`, `deletions-ask`,
        `destructive-commands-ask`, `commits-only-when-shipping`). Every `Bash(...)` entry
        among them is `list: ask` — none is `deny` today; `credentials-never-leave-the-
        machine`'s six `Read(...)` entries (`~/.ssh/**`, `~/.aws/**`, `~/.config/gh/**`,
        `**/id_rsa`, `**/id_ed25519`, `**/*.pem`) are the only `deny` rows in `floor.json`
        and are transcribed as `deny` too, unchanged.
      - Five of `floor.json`'s six `guard_only` reasons — all four rows tagged
        `destructive-commands-ask` (an unlisted absolute path, an environment runner, an
        exec wrapper, and "whether a command is destructive often depends on the task")
        plus the one row tagged `credentials-never-leave-the-machine` (the credential-
        intent reason) — become `floor: no` **notes**: `rule` and `why` only, no
        `pattern`, matching nothing.
      - The sixth — the one row tagged `deletions-ask`, `find`'s own `-delete`/`-exec`
        options — becomes a real `floor: no` entry with a `pattern`
        (`Bash(find * -delete*)`, `Bash(find * -exec*)`), `list: ask`.
      - Add a read-only allowlist (`ls`, `cat`, `git status`, `git diff`, `git log`, …) as
        new `floor: no` entries, each with a real `pattern`, no floor counterpart today.
      Do **not** add diagram 05's own further examples (`docker`, `kubectl`, a
      deny-severity `sudo`, `reset --hard`, `curl | sh`, or `rm -rf` outside cwd) — they
      are the diagram's own illustration of the mechanism's shape, not part of v1 (design's
      Non-Goals); growing coverage to match them is later, unscheduled work (§11). Verify:
      every rule id currently in `plugin/control/floor.json` appears in `patterns.yaml`
      with the same severity; every `guard_only` reason survived, five as pattern-less
      notes and one (`find`) with a real pattern; and no rule id or matched pattern appears
      in `patterns.yaml` that isn't already in `plugin/control/floor.json` today or in the
      new read-only allowlist.
- [x] 1.2 Write `plugin/control/guard/generate_floor.py`, reading `patterns.yaml` and
      emitting the exact `floor.json` shape: each `floor: yes` entry into `entries`, each
      `floor: no` entry into `guard_only` (carrying its `why`), dropping the `floor` flag
      itself since `floor.json`'s own format has no such field. This script is a
      maintainer step, run by hand after editing `patterns.yaml` — like
      `docs/diagrams/build.py` — never called by setup or by `guard.py` at runtime. Verify:
      running it produces output byte-identical to the committed `plugin/control/floor.json`.
- [x] 1.3 Add a regeneration test to `tests/test_floor.py` that runs the generator into a
      temp file and diffs it against the committed `plugin/control/floor.json`. Verify: the
      test passes on the committed files and fails when a pattern is added to
      `patterns.yaml` without regenerating `floor.json`.

## 2. `decide.py`: the `score` question type

- [x] 2.1 Extend `plugin/scripts/decide.py`'s question parsing: collect
      `rule_threshold.<option-name>` dotted fields into a map (mirroring `option.*`),
      require at least one for a `score` question, and forbid the flat `rule_threshold`
      and `rule_threshold_low` fields for `score`. Verify: unit tests in
      `tests/test_decide.py` for a `score` file missing every per-option threshold and one
      declaring the flat fields, both raising `DecisionError` naming the file.
- [x] 2.2 Implement `_question_payload` for `score`, building the request's `criteria` from
      every declared `option.*`. Verify: a unit test asserts the built payload's shape
      against a fixture request.
- [x] 2.3 Implement `parse_response` for `score`: read one independent probability per
      option, resolve to the first declared option (in file order) whose probability meets
      its own threshold, or return unresolved carrying every probability. Verify: unit
      tests for one option crossing, two options crossing (earliest wins), none crossing,
      and the `mock` backend.
- [x] 2.4 Write `plugin/control/guard/guard-risk.yaml` — type `score`, options `destructive`,
      `read_only`, `reversible` in that order, `rule_threshold.destructive: 0.30`,
      `rule_threshold.read_only: 0.85`, `state_fields: command, cwd, branch, is_worktree`.
      Verify: `decide.py ask --question guard.risk --decisions-dir plugin/control/guard/
      --state -` loads the question and returns the `mock` backend's unresolved answer
      with no error.

## 3. `guard.py`: parsing and classification

- [x] 3.1 Implement command splitting in `plugin/control/guard/guard.py`: top-level `;`,
      `&&`, `||`, `|` via `shlex`, any unparseable or backtick/`$(`-bearing segment marked
      ambiguous. Verify: unit tests for a compound command, a quoted argument containing an
      operator character, and an unparseable command, each landing on the expected path.
- [x] 3.2 Implement allow/deny/ask matching against `patterns.yaml`'s default lists,
      skipping a pattern-less note entry (D2) rather than matching or erroring on it.
      Verify: unit tests covering an allowed read-only command, a deny match, and an ask
      match, each citing the matched rule; and a list containing a note entry ahead of a
      real one, asserting the note is skipped and the real pattern still matches.
- [x] 3.3 Implement per-role list overrides keyed on `agent_type` (additions only; a role
      `allow` entry in `patterns.yaml` is rejected at load time). Verify: unit tests for a
      role-restricted command denied for that role and allowed for the main session, and
      for a role `allow` entry raising a load-time error.
- [x] 3.4 Wire the residue path to `decide.py ask --question guard.risk` (3 s timeout, one
      retry), mapping a resolved `read_only` to allow and everything else — resolved
      `destructive`, resolved `reversible`, unresolved, or any backend failure — to ask.
      Verify: unit tests with the backend stubbed to hang, to return a stubbed 5xx-then-
      success, to be `mock`, and to be missing a key — every case resolving to ask, none to
      allow.
- [x] 3.5 Implement the guard's own journal at `.harnex/state/guard/journal.jsonl` (deny
      and ask entries only, never allow). Verify: unit tests assert a deny and an ask each
      append one line with `command`, `agent_type`, `outcome`, `source`, and that an
      allowed command appends nothing.
- [x] 3.6 Wrap the classification pipeline (3.1–3.3) in one exception handler that resolves
      to ask and journals `source: internal_error` with the exception's message, distinct
      from a `guard.risk` backend failure (3.4). Verify: a unit test forces an exception
      inside the matcher (a malformed `patterns.yaml` entry, a monkeypatched raise) and
      asserts the outcome is ask and the journal records `source: internal_error`.

## 4. The hook

- [x] 4.1 Add the `PreToolUse` entry for `Bash` to `plugin/hooks/hooks.json`, calling
      `plugin/control/guard/guard.py` through `uv run --quiet`, with a declared timeout
      above the script's own budget. Verify: a fixture-driven test in `tests/test_guard.py`
      runs the hook as a real process against a recorded stdin payload for every row of
      diagram 05's table — allow, deny, ask, the `guard.risk` outcomes, the backend-failure
      box, and the internal-error box (3.6) — and asserts the documented outcome.
- [x] 4.2 Add fixture tests for the hook's own failure modes: interpreter missing, script
      crashing, hook killed at its timeout, malformed stdout. Verify: each asserts nothing
      is attributed to the guard and Claude Code's normal permission flow is left to
      decide (per `plugin/control/README.md`'s existing guarantee).

## 5. Per-role content

- [x] 5.1 Author the builder role's own stricter additions in `patterns.yaml` from §4's
      role matrix in `docs/PLAN.md` (write only inside declared paths, never tick
      `tasks.md`, never touch `openspec/` or `.harnex/`). Verify: a unit test asserts a
      builder-tagged call is denied or asked for a command the main session's own lists
      alone would allow.

## 6. Rule and doc corrections

- [x] 6.1 Re-read `plugin/context/rules/safety/*.md` against what actually got built;
      correct any line that no longer matches (expected: none, since they were written
      ahead of the mechanism). Verify: `uv run --with pytest pytest` still passes the rule-
      to-enforcer walk.
- [x] 6.2 Update `plugin/control/README.md`'s "Filled by" line to record `C4` delivered.
      Verify: the line names this change.

## 7. Full verification

- [x] 7.1 Run `uv run --with pytest pytest`, `claude plugin validate plugin --strict`,
      `claude plugin validate . --strict`, and `openspec validate --all`; fix anything they
      catch. Verify: all four exit 0.
- [x] 7.2 Manual walkthrough on a scratch project, recorded as this change's own
      `smoke.md`: `ls` runs with no prompt; `rm -rf /tmp/harnex-test` asks, with a reason
      (v1 carries no deny-severity Bash pattern — design.md's Non-Goals and diagram 05's
      "none today" deny box, not a deny demonstration); `git push` asks; with the API key
      unset, an ambiguous command asks and says the backend was unreachable; with the
      guard script renamed to break the hook, `git push` still asks, from the floor.
      Verify: the transcript for each step matches diagram 05.

## 8. Plan sync

- [x] 8.1 Update `docs/PLAN.md`: mark `C4` **delivered**, fill in its "What it taught us"
      from anything this change learned that the design did not already predict, and
      correct §4's builder·Codex row, which currently reads "the ask has to come from
      harnex's own guard, once C4 lands" — this change's guard hooks `Bash` in the main
      session and Claude subagents only; it does not reach a command Codex runs inside its
      own sandbox (confirmed non-goal, and diagram 05's own note), so that cell's ask still
      depends on Codex's own sandbox until a Codex-side hook is built, later, not here. Also
      correct §11's C4 "you try it" line, which currently reads "`rm -rf
      /tmp/harnex-test`: denied, with the reason" — v1 carries no deny-severity Bash
      pattern (every rule resolves to ask); change it to read "asks, with the reason,"
      matching `tasks.md` 7.2 and diagram 05's own "none today" deny box. Regenerate
      diagrams if anything else in the guard's actual shape differs from diagram 05's
      assumptions (`python3 docs/diagrams/build.py`).
