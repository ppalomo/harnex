## 1. The decision-question file format and `phase.route`

- [x] 1.1 Write `plugin/orchestration/decisions/README.md` stating the file format from
      design.md D2 (frontmatter fields, the `option.<name>` convention, the `---`-delimited
      body), mirroring `plugin/context/rules/README.md`'s structure, and verify it names
      every field the parser in 1.2 accepts and none it does not.
- [x] 1.2 Add the question-file parser (in `plugin/scripts/decide.py` or a small shared
      module it imports) that reads `id`, `type`, `state_fields`, `option.*`,
      `rule_threshold`, refusing a duplicate key, a second colon-free line, or an unknown
      key, and verify with unit tests: a well-formed file parses to the expected dict; a
      duplicate key, an unknown key, and a missing `---` each raise a named error.
      (The format has one `---`, not a rule's two — fields have nothing before them to
      close off, matching design.md D2's own example exactly.)
- [x] 1.3 Add `plugin/orchestration/decisions/phase-route.yaml` (design.md D2's example)
      and verify `openspec validate --strict` and the layout test still pass with the new
      file present.

## 2. `decide.py`

- [x] 2.1 Implement the `mock` backend: for any question, return the unresolved shape from
      design.md D1 (`resolved: false`, `backend: "mock"`, `reason: "mock_backend"`, a
      `prompt` built from the question's `instructions` and its options), and verify with a
      unit test that it never opens a socket (patch `urllib` to raise if called).
- [x] 2.2 Implement the `jev` backend's request builder (design.md D3): build the
      OpenRouter Decisions request body for a `choice` question from the question file's
      `option.*` map and the caller's state, and verify with a unit test against the exact
      example request shape recorded in design.md's Context section.
- [x] 2.3 Implement the `jev` backend's response handling: a resolved decision when the
      top probability is at or above `rule_threshold`, else the unresolved shape with
      `reason: "below_threshold"`; verify with unit tests built from the exact example
      response recorded in design.md's Context section, at both above- and below-threshold
      probabilities.
- [x] 2.4 Implement the `jev` backend's failure handling: one retry on a network error or a
      5xx status, a fixed total time budget across both attempts, and the unresolved shape
      with a `reason` string for every other failure (missing key, 4xx, malformed JSON,
      both attempts failing) — and verify with unit tests: a stubbed hanging socket that
      never resolves before the budget, a stubbed 500 followed by a stubbed success, a
      stubbed 401, and a missing `OPENROUTER_API_KEY`, each asserting no exception escapes
      and the elapsed time stays within the stated budget.
- [x] 2.5 Implement the journal writer: append one line to `.harnex/state/journal.jsonl`
      per call, with `question`, `state_sha256`, `probabilities`, `confidence`, `decision`,
      `rule_applied`, `backend`, `cost_usd` (design.md D3), an empty `resolution`, for both
      resolved and unresolved outcomes, and verify with a unit test that one call produces
      exactly one well-formed JSON line.
- [x] 2.6 Implement the `ask` CLI verb (`decide.py ask --question <id> --state <file>
      --project <root>`) that reads the project's `decision_model`, dispatches to the right
      backend, prints the one JSON object from design.md D1 to stdout, and always exits 0
      on a resolvable request, and verify with an end-to-end test running the script as a
      real process (matching `C1c`/`C1d`'s precedent) against both backends.
      (Tested against `mock`; `jev` end-to-end is task 6.4's manual try, since this
      repository has no working OpenRouter key.)
- [x] 2.7 Verify the "never index by position" requirement (spec: decision-model, "`state`
      is passed as a keyed object") with a test asserting the request builder from 2.2
      refuses or rejects a list-typed state field rather than serialising it positionally.

## 3. The verifier

- [x] 3.1 Write `plugin/orchestration/roles/verifier.md`, the tool-agnostic role prompt
      from design.md D4 (reads artifacts from disk, reports coherence and gaps, refuses to
      fix or reopen a settled decision), following the role-prompt skeleton the existing
      `sdd` rules already assume.
- [x] 3.2 Write `plugin/agents/verifier.md` with minimum frontmatter (`name`,
      `description`, `tools: Read, Grep, Glob`), and verify with a test asserting its
      `tools` list contains none of `Edit`, `Write`, `Bash`.
- [x] 3.3 Verify the frontmatter-minimality convention (`AGENTS.md`: "agents... use the
      minimum frontmatter") holds for `verifier.md` alongside the existing check for other
      agent/skill frontmatter, extending that test rather than adding a parallel one.
      (No prior test existed for this; `tests/test_agent_and_skill_frontmatter.py` is new
      and is where 6.3's skill checks land too. It also confirmed, by fetching Claude
      Code's own docs, that an agent body cannot `@`-import another file — so the adapter's
      body is a verbatim copy of the role prompt, and the test walks that correspondence
      the way `C1d` walks rule-to-hook.)

## 4. The scope check

- [x] 4.1 Implement `plugin/feedback/scope_check.py check --change <name> --before
      <snapshot-file>` (design.md D5): diff a fresh `git status --porcelain=v1 --untracked-files=all` against the
      snapshot, and report any path outside `openspec/changes/<name>/` that is new in the
      diff, and verify with unit tests: a clean run reports nothing; a file written inside
      the change's directory reports nothing; a file written outside it is reported; a file
      already dirty before the snapshot is not reported even if still dirty after.
      (Named `scope_check.py`, underscore — matching every other script in the repo, not
      the hyphenated name this change's own artifacts first used. `--untracked-files=all`
      was added to both the snapshot and the live status call once a real test showed
      plain `git status --porcelain` collapses a brand-new directory — exactly what a
      change's own directory is — into one entry instead of listing its files, which would
      have hidden every file `propose` writes from the check meant to watch them.)
- [x] 4.2 Update `plugin/context/rules/sdd/the-proposal-is-the-scope.md` to
      `enforced_by: check` with the `**Enforced by:**` line from design.md D6, and verify
      the rule-format test and the rendering snapshot that includes the `sdd` set both
      still pass with the updated file.

## 5. Wiring the pillars together

- [x] 5.1 Add the "What is here" section to `plugin/orchestration/README.md` naming
      `../scripts/decide.py` and `../agents/verifier.md` (mirroring
      `plugin/tools/README.md`'s existing section), and update its "Filled by" line.
      (Also rewrote the "What does not" bullet about the decision client — it read as
      excluding `decide.py` from pillar 3 entirely, which contradicted this change's own
      proposal and design; now it says the same thing `tools/README.md` says about
      `setup.py`: kept at the plugin root, still this pillar's.)
- [x] 5.2 Write `plugin/orchestration/workflow.md` (design.md, proposal.md): the five
      phases, what each may write, entry/exit criteria for `explore` and `propose` in
      full, and `apply`/`verify`/`ship` named with their entry criteria and marked not yet
      implemented.
- [x] 5.3 Update `plugin/feedback/README.md`'s "Filled by" line to reflect that the
      decision journal's format is exercised by `C2` and the scope check has landed.

## 6. The `explore` and `propose` skills

- [x] 6.1 Write `plugin/skills/explore/SKILL.md` (design.md D7): prints the advice line via
      `decide.py ask --question phase.route`, then holds a conversation clarifying the
      idea; never creates a file under `openspec/` and never calls the verifier.
      (Also fixed here, not left implicit: an *unresolved* advice outcome — mock, low
      confidence, or a `jev` failure — never turns into a question to the person, since
      `explore`/`propose` cannot act on the answer anyway; the skill only prints it.)
- [x] 6.2 Write `plugin/skills/propose/SKILL.md`: prints the advice line; captures the
      pre-start `git status --porcelain=v1 --untracked-files=all` snapshot; drives the `openspec` CLI directly
      (`new change`, `status --json`, `instructions <id> --change <name> --json` per
      artifact) to write the proposal, specs, design where required, and tasks, asking the
      person in plain language at each point that needs their input; runs
      `scope_check.py check` once every required artifact exists and reports its findings;
      starts the verifier once against the change's directory and shows its review; never
      surfaces an artifact id or schema name to the person as something they must act on.
- [x] 6.3 Add frontmatter tests for both skills (name equals directory name, minimum
      frontmatter) alongside the existing skill/agent frontmatter checks.
      (Both already matched `tests/test_agent_and_skill_frontmatter.py`'s existing glob
      over `plugin/skills/*/SKILL.md` from 3.3 — no new test needed, and both pass.)
- [ ] 6.4 Manually try both skills end to end in a scratch project per proposal.md's "you
      try it": `/harnex:explore "an idea"`, then `/harnex:propose`, once with
      `decision_model: mock` and, if `OPENROUTER_API_KEY` is available by then, once with
      `jev` — recording any mismatch between OpenRouter's documented response shape
      (design.md's Context section) and what a real call actually returns, and fixing
      `decide.py` against the real shape rather than the assumed one.
      **Blocked in this session**: Claude Code resolves a plugin's skills once at session
      start; `explore` and `propose` were added to the harnex plugin mid-session, and this
      session's own skill listing does not carry them (confirmed by invoking both `explore`
      and `harnex:explore` directly — both `Unknown skill`). A fresh session, with the
      harnex plugin already installed and enabled (it is, at user scope, on this machine),
      is needed to run this manual try. Left for the person to run and report back.

## 7. Close-out

- [x] 7.1 Append this change's section to `docs/smoke.md` in the established format.
- [x] 7.2 Update `docs/PLAN.md` (§11 C2 marked delivered with its exit criterion met or
      named as partially met, per the manual try in 6.4; §13 if anything there is touched)
      to match what landed.
      (Marked delivered: exit criterion met by construction and by the automated tests;
      the one live "you try it" step is the fresh-session manual try 6.4 is blocked on.
      Also regenerated `06-roadmap` and `07-layout` via `docs/diagrams/build.py` — the
      "before committing" checklist calls for this when the layout or workflow changes,
      and both did.)
- [x] 7.3 Run `uv run --with pytest pytest`, `claude plugin validate plugin --strict`,
      `claude plugin validate . --strict`, and `openspec validate --all`, and confirm all
      pass before this change is considered ready to verify.
