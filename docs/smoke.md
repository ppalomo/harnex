# Manual checks

Every capability in harnex must be testable by hand, by the owner, with instructions.
This file is where those instructions live: one section per change, appended as each one
lands, newest at the bottom.

The automated tests (`uv run --with pytest pytest`) check what can be checked without
credentials and without a running agent. These checks are the other half: they exercise
the real host, the real CLI and, later, the real models.

## The format

Each section is:

```
## <change name> (<phase>)

**Delivers:** one sentence.

**Verified against:** the versions the check last passed on.

**Steps**
1. …

**Expect**
- …
```

Two rules keep this file honest. State what you expect to *not* happen when that is the
point of the check — a plugin that adds nothing is a result, not an omission. And record
the versions: a check that fails after a host upgrade should be readable as "the host
moved", not as "the harness broke".

---

## bootstrap-installable-plugin (C1a)

**Delivers:** the delivery vehicle — a plugin that installs from this checkout and
contributes nothing yet, with the five pillar directories fixed and the repository's
own checks in place.

**Verified against:** Claude Code 2.1.267.

**Steps**

1. From the repository root, validate both manifests:
   ```bash
   claude plugin validate plugin --strict
   claude plugin validate . --strict
   ```
2. Run the repository's own checks:
   ```bash
   uv run --with pytest pytest -q -rs
   ```
   Then run them again with your personal denylist, which is never committed:
   ```bash
   HARNEX_DENYLIST=~/.harnex-denylist uv run --with pytest pytest -q -rs
   ```
3. Register this checkout as a marketplace and install the plugin. The trailing slash
   matters — a bare `.` is rejected as a source:
   ```bash
   claude plugin marketplace add ./
   claude plugin install harnex@harnex
   ```
4. Look at what was installed:
   ```bash
   claude plugin list
   claude plugin details harnex
   ```
   In an interactive session, `/plugin` shows the same thing.
5. Put the machine back as you found it:
   ```bash
   claude plugin uninstall harnex@harnex
   claude plugin marketplace remove harnex
   ```

**Expect**

- Both validations print `Validation passed`. Strict treats warnings as errors, so this
  also proves the two fields that are easy to lose are present: `author` in the plugin
  manifest and `metadata.description` in the marketplace.
- The checks pass. On the first run one test is skipped, naming which half of the
  private-name check did not run; on the second nothing is skipped.
- The plugin installs as `harnex@harnex`, version `0.1.0`, scope user, enabled.
- `claude plugin details harnex` reports **0 skills, 0 agents, 0 hooks, 0 MCP servers**
  and `~0 tok` added to every session. This is the point of C1a: the vehicle installs and
  does nothing. A command appearing here would mean something landed in the wrong change.

---

## rule-sets-and-rendering (C1b)

**Delivers:** the rule file format, the six rule sets, and the renderer that turns a
chosen list of sets into the rules file a project reads — the same bytes every time, for
the same choice.

**Verified against:** Claude Code 2.1.267, Python 3.13 through `uv`.

**Steps**

1. From the repository root, render two sets to the screen:
   ```bash
   uv run plugin/scripts/render_rules.py --sets git,code --out -
   ```
2. Add a third and compare. The file should grow by exactly that set and change in no
   other way:
   ```bash
   uv run plugin/scripts/render_rules.py --sets git,code --out /tmp/two.md
   uv run plugin/scripts/render_rules.py --sets git,code,safety --out /tmp/three.md
   diff /tmp/two.md /tmp/three.md
   ```
3. Ask for the same three sets in another order, and with one of them repeated:
   ```bash
   uv run plugin/scripts/render_rules.py --sets safety,code,git,git --out /tmp/again.md
   diff /tmp/three.md /tmp/again.md
   ```
4. Ask for a set that does not exist, and for none at all:
   ```bash
   uv run plugin/scripts/render_rules.py --sets git,security --out /tmp/never.md; echo "exit $?"
   uv run plugin/scripts/render_rules.py --sets "" --out -; echo "exit $?"
   ls /tmp/never.md
   ```
5. Run the repository's own checks, then again with your personal denylist:
   ```bash
   uv run --with pytest pytest -q -rs
   HARNEX_DENYLIST=~/.harnex-denylist uv run --with pytest pytest -q -rs
   ```
6. Read one rendered rule against its source, and check the round trip:
   ```bash
   cat plugin/context/rules/canary/canary-ends-every-answer.md
   uv run plugin/scripts/render_rules.py --sets canary --out -
   ```
7. Tidy up: `rm -f /tmp/two.md /tmp/three.md /tmp/again.md`.

**Expect**

- Step 1 prints a header saying the file is generated and must not be edited by hand,
  then `## code` and `## git` with their rules. The sets come out alphabetically,
  whatever order you typed — that is deliberate, not a quirk.
- Step 2's `diff` shows exactly two things: the header's `Sets in this file:` line, which
  gains `safety`, and the whole `## safety` section, added. Nothing inside the `git` or
  `code` sections moves by a byte — a set renders the same beside any other, which is what
  lets `setup` offer the sets freely.
- Step 3's `diff` prints nothing. The order asked for, and a repeat, never reach the file.
- Step 4 fails twice with exit 2, naming the unknown set and listing the six sets held,
  and `ls` reports no such file: a refused rendering writes nothing.
- Step 5's checks pass. On the first run two tests are skipped, naming the half of the
  private-name check that did not run; on the second nothing is skipped.
- Step 6 shows the rule's four fields and its body in the source, and in the rendering
  the same body under its set, with the statement as a heading and the frontmatter gone.
  The `**Enforced by:**` line survives: it names the canary check of pillar 5, which
  `C1d` builds. Nothing enforces anything yet, and that is the right order.

---

## setup-writes-a-project (C1c)

**Delivers:** `/harnex:setup` — one command that brings a project, empty or already
working, to a harnessed state: the files it owns, the ones it only offers, the permission
floor merged entry by entry, and the committed record that makes all of it refreshable
later. Nothing project-owned changes without an explicit yes, and a second run changes
nothing at all.

**Verified against:** Claude Code 2.1.269 (permission syntax and rule order, plugin
manifest and `${CLAUDE_PLUGIN_ROOT}`), OpenSpec 1.11.0, Python 3.13 through `uv`.

**Steps**

1. Install the plugin from your checkout, if it is not installed already, and confirm what
   it now contributes:
   ```bash
   claude plugin marketplace add ./
   claude plugin install harnex@harnex
   claude plugin details harnex
   ```
2. Make a scratch project, commit it as it is — setup runs only on a git repository with
   nothing to commit (`C9`) — and open a session in it:
   ```bash
   mkdir -p /tmp/harnex-scratch && cd /tmp/harnex-scratch && git init -q
   printf '# scratch\n' > README.md && git add -A && git commit -qm "first commit"
   claude
   ```
3. Run `/harnex:setup`. Answer the questions: accept the directory name, keep all six
   sets, accept the proposed canary word, choose `mock`, and give any check command.
   **Read the plan it prints before you say yes.** Then say yes.
4. Read what landed, in this order:
   ```bash
   cat AGENTS.md CLAUDE.md .harnex.yml
   head -20 .harnex/rules.md
   cat .harnex/manifest.json
   cat .claude/settings.json
   cat .harnex/state/.gitignore
   git status --short --untracked-files=all
   ```
5. Run `/harnex:setup` again in the same session, before committing anything, and read
   what it says. Then commit what setup wrote and run `/harnex:setup` once more:
   ```bash
   git add -A && git commit -qm "harnessed"
   ```
6. Leave the session. Prove the same sequence from the script, which is what the command
   drives, and prove what it refuses — the hand edit is committed, as someone else's would
   be, so the tree is clean and the refusal is about the file, not the tree:
   ```bash
   cd ~/Developer/harnex     # your checkout
   cat > /tmp/harnex-answers.json <<'JSON'
   {"project_name": "scratch", "profiles": [], "sets": ["git", "code", "sdd", "safety", "canary", "language"],
    "features": [], "canary": "Hullaballoo!", "decision_model": "mock", "check_command": "make check",
    "approvals": {"pointer_agents": false, "pointer_claude": false, "adopt": []}}
   JSON
   uv run plugin/scripts/setup.py choices
   uv run plugin/scripts/setup.py plan --answers /tmp/harnex-answers.json --project /tmp/harnex-scratch
   echo "rules I wrote by hand" > /tmp/harnex-scratch/.harnex/rules.md
   git -C /tmp/harnex-scratch commit -qam "rules edited by hand"
   uv run plugin/scripts/setup.py write --answers /tmp/harnex-answers.json --project /tmp/harnex-scratch; echo "exit $?"
   git -C /tmp/harnex-scratch status --short
   ```
7. Restore the file the harness owns, by adopting it, check the tree afterwards, and
   commit the result:
   ```bash
   python3 - <<'PY'
   import json, pathlib
   p = pathlib.Path("/tmp/harnex-answers.json"); a = json.loads(p.read_text())
   a["approvals"]["adopt"] = [".harnex/rules.md"]; p.write_text(json.dumps(a))
   PY
   uv run plugin/scripts/setup.py write --answers /tmp/harnex-answers.json --project /tmp/harnex-scratch
   git -C /tmp/harnex-scratch status --short
   git -C /tmp/harnex-scratch commit -qam "rules adopted back"
   ```
8. Now an existing project. Copy one of your own — or build one that looks like one — and
   set it up:
   ```bash
   rm -rf /tmp/harnex-existing && mkdir -p /tmp/harnex-existing/.claude
   cd /tmp/harnex-existing && git init -q
   printf '# My project\n\nIt does a thing.\n' > AGENTS.md
   printf '# My project\n\nRead AGENTS.md.\n' > CLAUDE.md
   printf 'build/\n' > .gitignore
   cat > .claude/settings.json <<'JSON'
   {"permissions": {"allow": ["Bash(git *)"], "deny": ["Read(./secret.txt)"]}, "env": {"MY_VAR": "1"}}
   JSON
   git add -A && git commit -qm "before the harness"
   claude
   ```
   Run `/harnex:setup`, read the notices, say **no** to the pointer line in `AGENTS.md`
   and **yes** to the one in `CLAUDE.md`, and approve the plan. Then:
   ```bash
   git diff --stat
   git diff .claude/settings.json | head -30
   git diff AGENTS.md
   ```
9. Commit what setup wrote (`git add -A && git commit -qm "harnessed"`), run setup once
   more in that project and read the notices.
10. A fresh clone of the scratch project, committed since step 7:
    ```bash
    git clone -q /tmp/harnex-scratch /tmp/harnex-clone
    cd ~/Developer/harnex
    uv run plugin/scripts/setup.py plan --answers /tmp/harnex-answers.json --project /tmp/harnex-clone
    ```
11. Run the repository's own checks, then again with your personal denylist:
    ```bash
    uv run --with pytest pytest -q -rs
    HARNEX_DENYLIST=~/.harnex-denylist uv run --with pytest pytest -q -rs
    ```
12. Tidy up: `rm -rf /tmp/harnex-scratch /tmp/harnex-existing /tmp/harnex-clone /tmp/harnex-answers.json`.

**Expect**

- Step 1: harnex `0.1.0` with **1 skill (`setup`), 0 agents, 0 hooks, 0 MCP servers** and
  ~81 tokens always-on. One capability, one component: the host lists commands and skills in
  the same inventory, so `/harnex:setup` is the skill itself.
  Nothing else changed in any project you open: the plugin still does nothing until a
  project has been set up.
- Step 3: the questions come in the order the skill states, and **profiles and features are
  never asked about** — the harness holds none yet, so there is nothing to offer. The plan
  prints one line per path, eight of them, all `create`, and says that nothing has been
  written yet.
- Step 4: `AGENTS.md` is a brief with your check command in it and a `## Rules` section
  pointing at `.harnex/rules.md`; `CLAUDE.md` starts with the two `@` imports; `.harnex.yml`
  holds your seven answers, flat; the record holds a `sha256` for each of the two paths the
  harness owns and the exact permission entries it wrote; `.claude/settings.json` has 6
  `deny` and 36 `ask` entries and nothing else; `git status` shows the new files and
  **nothing under `.harnex/state/`** — the directory ignores itself, and your `.gitignore`
  was never touched.
- Step 5: the first rerun goes ahead even though nothing is committed: every uncommitted
  path is one setup itself just wrote, and the harness's own paths do not count against
  the clean tree (`C9`). It says "Nothing to do: this project is already set up as these
  answers describe." After the commit, the second rerun says the same. No file changes,
  the record included.
- Step 6: `choices` lists the six sets, empty profiles and features, the two backends and
  the proposed word. The first `plan` reports every path as `keep` or `unchanged`. After the
  rules file is edited by hand and committed, `write` **exits 1**, names the file, says it
  was edited after the harness wrote it, and offers adoption — and `git status` prints
  nothing, proving nothing was written.
- Step 7: adoption replaces only that file: `git status --short` shows `.harnex/rules.md`
  modified and nothing else, back to the harness's own rendering, and the tree is clean
  again once that is committed.
- Step 8: `git diff --stat` shows `CLAUDE.md` and `.claude/settings.json` and nothing else.
  `AGENTS.md` is **byte-identical** — you declined, so nothing was inserted. The settings
  diff adds the floor's entries and leaves `Read(./secret.txt)`, `Bash(git *)` and `env`
  exactly as they were. The notices told you that your `Bash(git *)` allow covers floor
  entries and has no effect on them, because the host resolves deny, then ask, then allow.
- Step 9: the notice about `AGENTS.md` is repeated, word for word — and would be without
  the commit too, since `CLAUDE.md` and the settings are the harness's own paths and do
  not count against the clean tree. A declined line is not remembered anywhere — its absence is what
  brings the notice back.
- Step 10: the clone is recognised from the committed record: every committed path is
  `unchanged`, and the only thing to write is `.harnex/state/.gitignore`, which is
  deliberately not committed. It asks nothing.
- Step 11: every check passes. Without the environment variable, four checks skip and say
  which half did not run.

---

## canary-enforces-itself (C1d)

**Delivers:** the canary check (`plugin/feedback/canary/canary.py`) and the plugin's
`Stop` hook that runs it at the end of every main-session answer. Inert without
`.harnex.yml` or without the `canary` set; warns the person, never the model, when the
project's word is missing from the end of an answer.

**Verified against:** Claude Code 2.1.267 (`Stop` hook payload shape, plugin hook
registration), Python 3.13 through `uv`.

**Steps**

1. Install the plugin from your checkout and confirm the hook it now contributes:
   ```bash
   claude plugin marketplace add ./
   claude plugin install harnex@harnex
   claude plugin details harnex
   ```
2. Set up a scratch project choosing only the `canary` set, starting from a committed
   repository as setup requires, and commit what it writes:
   ```bash
   mkdir -p /tmp/harnex-canary && cd /tmp/harnex-canary && git init -q
   printf '# canary\n' > README.md && git add -A && git commit -qm "first commit"
   cd ~/Developer/harnex
   cat > /tmp/harnex-canary-answers.json <<'JSON'
   {"project_name": "canary-smoke", "profiles": [], "sets": ["canary"], "features": [],
    "canary": "Hullaballoo!", "decision_model": "mock", "check_command": "make check",
    "approvals": {"pointer_agents": true, "pointer_claude": true, "adopt": []}}
   JSON
   uv run plugin/scripts/setup.py write --answers /tmp/harnex-canary-answers.json \
     --project /tmp/harnex-canary
   git -C /tmp/harnex-canary add -A && git -C /tmp/harnex-canary commit -qm "harnessed"
   grep -A3 "## Canary" /tmp/harnex-canary/AGENTS.md
   ```
3. Open a session in it (`cd /tmp/harnex-canary && claude`) and ask anything. Read the
   answer.
4. In the same session, ask it to answer without the word on purpose — the deliberate
   miss that proves the check is not blind, worth repeating each time you verify against
   a new host version, not only the first time: *"Answer in one short sentence and do
   not end it with the canary word."*
5. Leave the session. Remove the set and ask again from a fresh one:
   ```bash
   sed -i '' 's/  - canary/  - git/' /tmp/harnex-canary/.harnex.yml
   cd /tmp/harnex-canary && claude
   ```
   Ask it to answer without the word again.
6. A project that never ran setup:
   ```bash
   mkdir -p /tmp/harnex-canary-none && cd /tmp/harnex-canary-none && git init -q && claude
   ```
   Ask anything.
7. Confirm the mechanism itself headlessly, for a record that does not depend on reading
   an interactive transcript:
   ```bash
   cd /tmp/harnex-canary
   git checkout -- .harnex.yml   # sets: canary again
   claude -p "Answer in one short sentence, no canary word." \
     --dangerously-skip-permissions --debug-file /tmp/harnex-canary-debug.log > /dev/null
   grep systemMessage /tmp/harnex-canary-debug.log
   ```
8. Tidy up:
   `rm -rf /tmp/harnex-canary /tmp/harnex-canary-none /tmp/harnex-canary-answers.json /tmp/harnex-canary-debug.log`.

**Expect**

- Step 1: harnex `0.1.0` now lists **1 hook (`Stop`)**, marked "harness-only — no model
  context cost": a hook adds no always-on tokens to a session.
- Step 2: `AGENTS.md` states the word in its own `## Canary` section. `.harnex/rules.md`
  is a pure function of the chosen sets, so the rule there stays generic ("the word the
  project declares"); the word itself is the project's own fact, so it is written into
  `AGENTS.md` instead. Without this, a model has no way to learn its own canary word.
- Step 3: the answer ends with `Hullaballoo!`, and nothing is shown about the canary —
  the check has nothing to report.
- Step 4: a warning naming the word, saying this instruction was not followed and that
  the rules may no longer be in effect — **never** that the context is lost — and the
  session carries on; the model is not asked to continue or retry the word. This shows in
  an interactive session or the desktop app's transcript; `claude -p`'s plain-text output
  does not print it (see step 7 for how to confirm it fired anyway).
- Step 5: the same missing word, and no warning at all — removing the set makes the check
  inert, not lenient.
- Step 6: silence — the check goes no further than confirming `.harnex.yml` is not there.
- Step 7: the debug log holds one line naming the `Stop` hook's own output —
  `{"systemMessage": "The canary word \`Hullaballoo!\` is missing from the end of this
  answer. ..."}` — proof the check ran and found what was expected, independent of
  whether the interface you used rendered it.

---

## explore-and-propose (C2)

**Delivers:** `decide.py` (`decide()`, the `mock` and `jev` backends, the decision
journal), the `phase.route` question, the `verifier` role and its Claude Code adapter,
`scope_check.py`, and the `/harnex:explore` and `/harnex:propose` skills — a change
proposed and design-reviewed end to end without ever running `openspec` by hand. Requires
a fresh Claude Code session after installing this version of the plugin: skills are
resolved once at session start, so a session already open when the plugin updates will not
see them.

**Verified against:** Claude Code 2.1.269, `openspec` CLI (whichever version your `PATH`
resolves), Python 3.13 through `uv`. The OpenRouter Decisions endpoint shape in
`decide.py` is read from OpenRouter's own docs, not yet exercised against a live key —
step 6 is where that gets its first real check.

**Steps**

1. Install this version of the plugin, from a fresh session:
   ```bash
   claude plugin marketplace add ./
   claude plugin install harnex@harnex
   claude plugin details harnex
   ```
2. Set up a scratch project with `decision_model: mock` and the `openspec` CLI on its
   `PATH` (harnex never installs OpenSpec itself):
   ```bash
   mkdir -p /tmp/harnex-propose && cd /tmp/harnex-propose && git init -q
   printf '# propose\n' > README.md && git add -A && git commit -qm "first commit"
   cd ~/Developer/harnex
   cat > /tmp/harnex-propose-answers.json <<'JSON'
   {"project_name": "propose-smoke", "profiles": [], "sets": ["git", "sdd"], "features": [],
    "canary": "", "decision_model": "mock", "check_command": "make check",
    "approvals": {"pointer_agents": true, "pointer_claude": true, "adopt": []}}
   JSON
   uv run plugin/scripts/setup.py write --answers /tmp/harnex-propose-answers.json \
     --project /tmp/harnex-propose
   cd /tmp/harnex-propose && openspec init -q 2>/dev/null || true
   ```
3. Open a session in it (`cd /tmp/harnex-propose && claude`) and run
   `/harnex:explore "a small idea, e.g. add a health-check endpoint"`.
4. In the same session, run `/harnex:propose`. Watch the `Decision (advice):` line appear
   first, then the artifacts written under `openspec/changes/<name>/`, then the scope
   check's report, then the verifier's review.
5. Read the change's `.harnex/state/journal.jsonl` — one line per `decide.py` call, both
   from `explore` and `propose`.
6. If `OPENROUTER_API_KEY` is set, switch the project to `decision_model: jev` and repeat
   step 4 in a fresh session. Compare the request `decide.py` actually sent and the
   response it got back against `design.md`'s Context section in this change's own
   `openspec/changes/` (before it is archived) — record any mismatch and fix `decide.py`
   against the real shape.
7. Tidy up: `rm -rf /tmp/harnex-propose /tmp/harnex-propose-answers.json`.

**Expect**

- Step 1: harnex now lists **2 skills** more than `C1c` (`explore`, `propose`) and **1
  agent** (`verifier`).
- Step 3: no file is written under `openspec/`; the session ends with `explore` suggesting
  `/harnex:propose` once the idea feels clear, never asking which tool or model should run
  it.
- Step 4: `proposal.md`, every delta spec the proposal names, `design.md` where the schema
  needs one, and `tasks.md` all exist; the person is never asked to name an artifact id or
  a schema. The scope check reports nothing was written outside the change's own
  directory. The verifier's review says plainly whether it found a contradiction, and
  `propose` finishes either way — it does not block on the review.
- Step 5: at least two journal lines (one per `phase.route` call), each with `backend:
  "mock"`, `decision: null`, and an empty `resolution`.
- Step 6: a resolved decision with `backend: "jev"` when the top probability is at least
  `0.70`; either way, no exception, no hang past `decide.py`'s own time budget, and the
  request/response shapes match what `design.md` recorded from OpenRouter's docs — or a
  fix to `decide.py`, recorded here, if they do not.

---

## apply-through-codex (C3)

**Delivers:** the `builder` role and its two bindings (Codex, through its plugin, and a
Claude fallback subagent), `task.route` and `task.scope` (the first `noul`-typed
question), `decide_many()`, the path/protected-path checks (`task_scope_check.py`), the
`apply_loop.py` script (fingerprinting, run state, routing, acceptance, ticking), and
`/harnex:apply` — a change's tasks built end to end without the person writing code, the
loop itself checking and ticking, never the builder. Requires a fresh Claude Code session
after installing this version of the plugin, for the same reason `C2` does.

**Verified against:** every deterministic step (`decide.py`'s `noul`/`decide_many`
additions, `task_scope_check.py`, `apply_loop.py`'s fingerprint/run-state/route/accept/
tick CLI verbs) against `uv run --with pytest pytest` and a hand-run walkthrough of the
same CLI verbs against a real scratch git repository, standing in for the builder by hand
(both a normal accept and a protected-path refusal, on a clean and an already-dirty tree).
**Not yet run:** the full `/harnex:apply` skill through a live session — it needs the
`builder` agent type loaded, which needs this version of the plugin installed and the
session reloaded first (steps 1–2 below); and a live Codex call, still blocked by the
account entitlement gap [S1](decisions/2026-09-27-s1-delegating-to-codex.md) found, so
step 4's Codex branch is this change's own remaining "try it" step, same as `C2` left a
live `jev` call as its.

**Steps**

1. Install this version of the plugin, from a fresh session:
   ```bash
   claude plugin marketplace add ./
   claude plugin install harnex@harnex
   claude plugin details harnex
   ```
2. Set up a scratch project with `decision_model: mock` and the `openspec` CLI on its
   `PATH`:
   ```bash
   mkdir -p /tmp/harnex-apply && cd /tmp/harnex-apply && git init -q -b main
   printf '# apply\n' > README.md && git add -A && git commit -qm "first commit"
   cd ~/Developer/harnex
   cat > /tmp/harnex-apply-answers.json <<'JSON'
   {"project_name": "apply-smoke", "profiles": [], "sets": ["git", "sdd", "code"], "features": [],
    "canary": "", "decision_model": "mock", "check_command": "python3 -m py_compile greeting.py farewell.py",
    "approvals": {"pointer_agents": true, "pointer_claude": true, "adopt": []}}
   JSON
   uv run plugin/scripts/setup.py write --answers /tmp/harnex-apply-answers.json \
     --project /tmp/harnex-apply
   cd /tmp/harnex-apply && openspec init -q 2>/dev/null || true
   ```
3. Open a session in it (`cd /tmp/harnex-apply && claude`), run `/harnex:propose` for a
   two-task idea whose tasks each name a file in backticks (e.g. "a `greeting.py` that
   prints hello and a `farewell.py` that prints bye"), then run `/harnex:apply`.
4. Watch: the branch checked out before anything else, both tasks' `Decision:
   apply(<id>) → <binding> · confidence <n>` lines printed together before the first
   builder starts, then per task the check and its evidence, and the task ticked in
   `tasks.md` — never by the builder. For the Claude-routed task, confirm the `builder`
   subagent never touches `tasks.md` itself. If a task routes to Codex, confirm the
   branch from step 1 was already checked out before the call, per
   [S1](decisions/2026-09-27-s1-delegating-to-codex.md)'s finding that `/codex:rescue`
   has no `--cwd` of its own.
5. Break the check on purpose (edit the file `apply` just wrote to fail
   `check_command`), run `/harnex:apply` again for that same task, and watch the one fix
   attempt: accepted if it passes, escalated — not retried again — if it still fails.
6. Interrupt `/harnex:apply` mid-task (close the session) and run it again. Confirm the
   already-accepted task is untouched and the interrupted one resumes from its recorded
   state or asks, per `apply_loop.py`'s `resume_action`.
7. Read `.harnex/state/apply/<change>.json` and confirm every task's transitions are
   there, and `.harnex/state/journal.jsonl` for one `task.route` entry per task (and a
   `task.scope` entry for any task that declared no paths).
8. Tidy up: `rm -rf /tmp/harnex-apply /tmp/harnex-apply-answers.json`.

**Expect**

- Step 1: harnex now lists **1 skill** more than `C2` (`apply`) and **1 agent** more
  (`builder`).
- Step 4: the decision lines appear together, before any builder starts — the person
  sees the whole run's routing up front, not staggered between tasks (design.md D6). The
  files `greeting.py`/`farewell.py` exist, match what the task asked for, and `tasks.md`
  shows both ticked, each by the loop's own act.
- Step 5: the fix attempt either lands (a second, passing check, then ticked) or
  escalates once and stops — never a second fix attempt on the same failure.
- Step 6: run state shows the interrupted task's last recorded transition; nothing about
  an already-accepted task changes on the second run.
- Step 7: one journal line per `task.route` question (one per task, sharing no state —
  `decide_many`'s one batched call, design.md D2) and, for any paths-less task, one more
  for `task.scope`.

---

## update-and-release (C6)

**Delivers:** `/harnex:update` — refreshing `.harnex/rules.md`, the permission-floor
entries and the Playwright entry from a project's own recorded choices, asking nothing —
and the release shape around it: plugin versioning, `vX.Y.Z` tags, and the steps an owner
actually runs to pick up a harness change (`docs/PLAN.md`'s own C6 line: change a rule in
your harnex checkout, bump the version, `claude plugin update harnex`, `/harnex:update` in
the project).

**Verified against:** Claude Code 2.1.285, Python 3.13 through `uv`.

**Steps**

1. Set up a scratch project with the `git` and `sdd` sets:
   ```bash
   mkdir -p /tmp/harnex-update && cd /tmp/harnex-update && git init -q
   printf '# update\n' > README.md && git add -A && git commit -qm "first commit"
   cd ~/Developer/harnex
   cat > /tmp/harnex-update-answers.json <<'JSON'
   {"project_name": "update-smoke", "profiles": [], "sets": ["git", "sdd"], "features": [],
    "canary": "", "decision_model": "mock", "check_command": "make check",
    "approvals": {"pointer_agents": true, "pointer_claude": true, "adopt": []}}
   JSON
   uv run plugin/scripts/setup.py write --answers /tmp/harnex-update-answers.json \
     --project /tmp/harnex-update
   git -C /tmp/harnex-update add -A && git -C /tmp/harnex-update commit -qm "harnessed"
   ```
2. Change a rule in your harnex checkout, as if preparing a release — bump the plugin
   version too, the way a real release would (skip the version bump here if you only want
   to prove the refresh itself; it does not change what `update` does):
   ```bash
   printf '\nAn added sentence, for this check only.\n' >> \
     plugin/context/rules/git/conventional-commits.md
   git status --short plugin/context/rules/git/conventional-commits.md
   ```
3. Refresh the scratch project from this checkout and look at what moved:
   ```bash
   uv run plugin/scripts/update.py --project /tmp/harnex-update
   git -C /tmp/harnex-update status --short
   git -C /tmp/harnex-update diff --stat
   git -C /tmp/harnex-update add -A && git -C /tmp/harnex-update commit -qm "after update"
   ```
4. Edit `.harnex/rules.md` by hand, simulating someone's own edit landing after a run, and
   update again:
   ```bash
   echo "rules I wrote by hand" >> /tmp/harnex-update/.harnex/rules.md
   uv run plugin/scripts/update.py --project /tmp/harnex-update; echo "exit $?"
   git -C /tmp/harnex-update status --short
   ```
5. Put the rules file back, then change the rule again, to a second, different content:
   ```bash
   git -C /tmp/harnex-update checkout -- .harnex/rules.md
   printf 'A second added sentence, for this check only.\n' >> \
     plugin/context/rules/git/conventional-commits.md
   ```
6. Simulate an interruption — a run that finished writing the rules file for this second
   change but was killed before it reached the manifest, the same shape
   `tests/test_update_run.py`'s `test_an_interrupted_update_recovers_by_content` proves:
   write the rules file directly, by hand, to exactly the content this run would produce,
   without going through `update.py`, and leave the manifest stale, still recording the
   first change:
   ```bash
   uv run plugin/scripts/render_rules.py --sets git,sdd --out /tmp/harnex-update/.harnex/rules.md
   git -C /tmp/harnex-update status --short
   ```
7. Run update once more and confirm it finishes from where the interruption left it:
   ```bash
   uv run plugin/scripts/update.py --project /tmp/harnex-update
   git -C /tmp/harnex-update status --short
   ```
8. Undo both rule edits in your checkout and tidy up:
   ```bash
   git checkout -- plugin/context/rules/git/conventional-commits.md
   rm -rf /tmp/harnex-update /tmp/harnex-update-answers.json
   ```

**Expect**

- Step 3: the report says `Written:` and names `.harnex/rules.md` and `.harnex/manifest.json`
  only. `git status --short` in the scratch project shows exactly those two paths modified
  — nothing project-owned (`AGENTS.md`, `CLAUDE.md`, `.harnex.yml`) moves, and no new file
  appears. `git diff --stat` confirms the same two paths and nothing else.
- Step 4: update **stops**, exits non-zero, names `.harnex/rules.md` in its report, and
  calls it a conflict — edited after the harness wrote it — pointing at `/harnex:setup`'s
  own adoption path rather than writing anything. `git status --short` still shows only the
  hand edit: update wrote nothing on top of it.
- Step 6: after hand-writing the second change's rendering straight into the project, the
  tree shows only `.harnex/rules.md` changed — the manifest is still the one step 3
  committed, recording the *first* change, because this step stands in for the run having
  been killed right after the rules write and before the manifest write that would follow
  it.
- Step 7: the second run completes cleanly, reporting `Written:` with only
  `.harnex/manifest.json` this time — recognising the rules file already matches what this
  run would have written and finishing the one write the interruption left undone, rather
  than refusing it as a hand-edit conflict the way step 4 did. `git status --short`
  afterwards still shows `.harnex/rules.md` and `.harnex/manifest.json` modified against
  the step 3 commit — now the second change, both files — and nothing else.

---

## personal-local-setup (C7)

**Delivers:** a `visibility: local` choice in `/harnex:setup` — nothing it writes for a
project ever reaches that project's own version-control history, on an empty project or
on one with its own existing, committed `AGENTS.md`.

**Verified against:** Claude Code 2.1.285, Python 3.13 through `uv`, git 2.x.

**Steps**

1. Set up a scratch project that already looks like a team's own repository, committed,
   since setup runs only on a clean tree (`C9`):
   ```bash
   mkdir -p /tmp/harnex-local && cd /tmp/harnex-local && git init -q
   git config user.email t@t.com && git config user.name t
   echo "# an existing team brief" > AGENTS.md
   git add -A && git commit -qm "existing brief"
   cd ~/Developer/harnex
   ```
2. Build the answers document, `store_id` and `store_path` included — the store is not
   registered yet; since `C9` that is a line of the plan, run only after the yes to it:
   ```bash
   cat > /tmp/harnex-local-answers.json <<'JSON'
   {"project_name": "local-smoke", "profiles": [], "sets": ["git", "sdd"], "features": [],
    "canary": "", "decision_model": "mock", "check_command": "make check",
    "approvals": {"pointer_agents": false, "pointer_claude": false, "adopt": []},
    "visibility": "local", "tools": ["claude"], "store_id": "harnex-local-smoke",
    "store_path": "/tmp/harnex-local-store"}
   JSON
   ```
3. Plan, register the store the plan names (what the skill does after your yes), then
   write, with a scratch home directory so the one global offer never touches your own
   `~/.claude/settings.json`:
   ```bash
   mkdir -p /tmp/harnex-local-home
   uv run plugin/scripts/setup.py plan --answers /tmp/harnex-local-answers.json \
     --project /tmp/harnex-local --home /tmp/harnex-local-home
   openspec store setup harnex-local-smoke --path /tmp/harnex-local-store --json
   uv run plugin/scripts/setup.py write --answers /tmp/harnex-local-answers.json \
     --project /tmp/harnex-local --home /tmp/harnex-local-home
   ```
4. Look at what changed, from git's own point of view:
   ```bash
   git -C /tmp/harnex-local status --porcelain
   git -C /tmp/harnex-local status --porcelain --ignored
   cat /tmp/harnex-local/AGENTS.md
   cat /tmp/harnex-local/CLAUDE.local.md
   cat /tmp/harnex-local/.git/info/exclude
   ```
5. Run setup again with `store_path` left empty, as the skill does once a `store_id` is
   recorded: nothing is proposed, and the recorded `store_id` is reused rather than
   registering a second store:
   ```bash
   sed 's|"/tmp/harnex-local-store"|""|' /tmp/harnex-local-answers.json \
     > /tmp/harnex-local-rerun.json
   uv run plugin/scripts/setup.py plan --answers /tmp/harnex-local-rerun.json \
     --project /tmp/harnex-local --home /tmp/harnex-local-home
   ```

**Expect**

- Step 3's plan lists `AGENTS.md` and `CLAUDE.md` too, each `keep` — the plan reports
  every surveyed path, whether or not it writes it — but writes only
  `CLAUDE.local.md`, `.harnex/config.yml`, `.harnex/rules.md`, `.harnex/.gitignore`,
  `.git/info/exclude` and `.claude/settings.local.json`; `AGENTS.md`/`CLAUDE.md` never
  get a write action. It also shows "register store `harnex-local-smoke` at
  `/tmp/harnex-local-store`" as a step, and the global settings offer as a line naming
  `pluginConfigs."agents-md@builtin".options.instructionFiles` and its value, not
  approved — `/tmp/harnex-local-home/.claude/settings.json` does not exist yet.
- Step 4: plain `git status --porcelain` prints nothing at all — the existing `AGENTS.md`
  commit is the only history this repository has. `--ignored` shows `.harnex/` and the
  two root-level files as ignored, not merely absent from the listing.
  `/tmp/harnex-local/AGENTS.md` still reads "# an existing team brief", byte for byte.
  `CLAUDE.local.md` holds one line, `@.harnex/rules.md`. `.git/info/exclude` lists both
  `CLAUDE.local.md` and `.claude/settings.local.json`.
- Step 5: "Nothing to do" — no "register store" step, not a second insertion attempt,
  not a rewritten `.harnex/config.yml`. Nothing is committed, yet the rerun is not refused
  as an unclean tree (`C9`): everything step 3 wrote is ignored, and ignored files do not
  count — nor would the harness's own paths if they were not. The same holds in a git
  worktree or a subdirectory of a repository: the repository is found with
  `git rev-parse`, and the exclude entries land in that repository's own list, anchored
  to the project's prefix in a subdirectory.

---

## ship-asks-version-bump (C8)

**Delivers:** a version-bump question folded into `/harnex:ship`'s existing
commit-confirmation ask, offered only when the project being shipped carries a
releasable plugin manifest (`version_bump.py detect`'s own test); a chosen bump lands in
the same commit `ship` makes, and `ship`'s final report then states the exact
`git tag`/`git push` commands for the person to run once the pull request merges, without
`ship` ever cutting or pushing the tag itself. A project with no such manifest sees the
single yes/no ask `ship` always asked, unchanged.

**Verified against:** Claude Code 2.1.285, OpenSpec 1.11.0, Python 3.13 through `uv`.

**Steps**

1. Make a scratch project that mirrors this repository's own plugin-manifest shape — a
   root `.claude-plugin/marketplace.json` with one `plugins[]` entry and a matching
   `plugin/.claude-plugin/plugin.json` — set it up with the `git` and `sdd` sets, commit
   it, and push it to a throwaway GitHub repository (`gh repo create` with a scratch name,
   `--private` is fine) so `ship`'s own `gh pr create` step has somewhere to land:
   ```bash
   mkdir -p /tmp/harnex-shipbump && cd /tmp/harnex-shipbump && git init -q -b main
   git config user.email t@t.com && git config user.name t
   printf '# shipbump\n' > README.md && git add -A && git commit -qm "first commit"
   cd ~/Developer/harnex
   cat > /tmp/harnex-shipbump-answers.json <<'JSON'
   {"project_name": "shipbump-smoke", "profiles": [], "sets": ["git", "sdd"], "features": [],
    "canary": "", "decision_model": "mock", "check_command": "make check",
    "approvals": {"pointer_agents": true, "pointer_claude": true, "adopt": []}}
   JSON
   uv run plugin/scripts/setup.py write --answers /tmp/harnex-shipbump-answers.json \
     --project /tmp/harnex-shipbump
   mkdir -p /tmp/harnex-shipbump/plugin/.claude-plugin /tmp/harnex-shipbump/.claude-plugin
   cat > /tmp/harnex-shipbump/plugin/.claude-plugin/plugin.json <<'JSON'
   {"name": "shipbump-smoke", "version": "0.1.0", "author": "t"}
   JSON
   cat > /tmp/harnex-shipbump/.claude-plugin/marketplace.json <<'JSON'
   {"name": "shipbump-smoke", "owner": {"name": "t"}, "plugins": [
     {"name": "shipbump-smoke", "version": "0.1.0", "source": "./plugin",
      "description": "d", "metadata": {"description": "d"}}
   ]}
   JSON
   cd /tmp/harnex-shipbump && openspec init -q 2>/dev/null || true
   git add -A && git commit -qm "scratch project with a plugin manifest"
   gh repo create harnex-shipbump-scratch --private --source=. --remote=origin --push
   ```
2. Confirm the detector sees it exactly as `ship` would, before touching a session:
   ```bash
   cd ~/Developer/harnex
   uv run plugin/scripts/version_bump.py detect --project /tmp/harnex-shipbump
   ```
3. Make a branch and a small, ordinary edit — enough for `ship`'s direct path (no
   `openspec/changes/` directory exists for this branch, so `ship` never reaches the
   gated path in this scratch project):
   ```bash
   cd /tmp/harnex-shipbump && git checkout -qb a-change
   printf 'a line worth shipping\n' > NOTE.txt
   claude
   ```
   Run `/harnex:ship`. Read the single confirmation ask it shows.
4. Choose **patch** at the version question, then say yes.
5. Read what the session did, from outside it:
   ```bash
   git -C /tmp/harnex-shipbump log -1 --stat
   cat /tmp/harnex-shipbump/plugin/.claude-plugin/plugin.json
   cat /tmp/harnex-shipbump/.claude-plugin/marketplace.json
   ```
6. Read the session's final report.
7. In a fresh session on a second branch with another small edit, run `/harnex:ship`
   again, this time choosing **no bump** at the version question, to confirm the plain
   path still works:
   ```bash
   cd /tmp/harnex-shipbump && git checkout -qb a-second-change
   printf 'another line\n' >> NOTE.txt
   claude
   ```
8. A scratch project with no plugin manifest at all:
   ```bash
   mkdir -p /tmp/harnex-shipbump-none && cd /tmp/harnex-shipbump-none && git init -q -b main
   git config user.email t@t.com && git config user.name t
   printf 'hello\n' > file.txt && git add -A && git commit -qm "first commit"
   gh repo create harnex-shipbump-none-scratch --private --source=. --remote=origin --push
   git checkout -qb a-change
   printf 'world\n' >> file.txt
   claude
   ```
   Run `/harnex:ship`.
9. Tidy up:
   ```bash
   gh repo delete harnex-shipbump-scratch --yes
   gh repo delete harnex-shipbump-none-scratch --yes
   rm -rf /tmp/harnex-shipbump /tmp/harnex-shipbump-none /tmp/harnex-shipbump-answers.json
   ```

**Expect**

- Step 2: `{"found": true, ..., "current_version": "0.1.0", "candidates": {"patch":
  "0.1.1", "minor": "0.2.0", "major": "1.0.0"}}`.
- Step 3: one ask, not two — the version-bump question is folded into the same
  confirmation `ship` always asked, offering **no bump**, **patch** (`0.1.0 -> 0.1.1`),
  **minor** (`0.1.0 -> 0.2.0`) and **major** (`0.1.0 -> 1.0.0`), each stated with its
  resulting version, plus a brief explanation of what the three numbers mean.
- Step 5: the one commit the session made touches `NOTE.txt` and both manifest files
  together, each now at `0.1.1` — the bump landed inside the same commit `ship` made, not
  a separate one.
- Step 6: the final report states the pull request was opened, names the version bumped
  to (`0.1.1`), and gives the exact `git tag v0.1.1` / `git push origin v0.1.1` commands
  for after the pull request merges — making clear `ship` ran neither command itself.
- Step 7: choosing **no bump** leaves both manifest files exactly as step 5 left them —
  nothing in this commit touches them — and the final report says nothing about a tag.
- Step 8: this project has no `.claude-plugin/marketplace.json` at all, so the detector
  would report `"found": false`; `ship` asks exactly the single yes/no question it asked
  before this change, with nothing about a version in it, and its final report says
  nothing about a tag or a bumped version — proving the no-manifest project is left
  exactly as it would have been without this change.
