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
2. Make an empty scratch project and open a session in it:
   ```bash
   mkdir -p /tmp/harnex-scratch && cd /tmp/harnex-scratch && git init -q
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
5. Run `/harnex:setup` again in the same session and read the plan.
6. Leave the session. Prove the same sequence from the script, which is what the command
   drives, and prove what it refuses:
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
   uv run plugin/scripts/setup.py write --answers /tmp/harnex-answers.json --project /tmp/harnex-scratch; echo "exit $?"
   git -C /tmp/harnex-scratch status --short
   ```
7. Restore the file the harness owns, by adopting it, and check the tree afterwards:
   ```bash
   python3 - <<'PY'
   import json, pathlib
   p = pathlib.Path("/tmp/harnex-answers.json"); a = json.loads(p.read_text())
   a["approvals"]["adopt"] = [".harnex/rules.md"]; p.write_text(json.dumps(a))
   PY
   uv run plugin/scripts/setup.py write --answers /tmp/harnex-answers.json --project /tmp/harnex-scratch
   git -C /tmp/harnex-scratch status --short
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
9. Run setup once more in that project and read the notices.
10. A fresh clone of the scratch project:
    ```bash
    cd /tmp/harnex-scratch && git add -A && git commit -qm "harnessed"
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
- Step 5: "Nothing to do: this project is already set up as these answers describe." No
  file changes, the record included.
- Step 6: `choices` lists the six sets, empty profiles and features, the two backends and
  the proposed word. The first `plan` reports every path as `keep` or `unchanged`. After the
  rules file is edited by hand, `write` **exits 1**, names the file, says it was edited
  after the harness wrote it, and offers adoption — and `git status` proves nothing else was
  written.
- Step 7: adoption replaces only that file, and the tree is clean again.
- Step 8: `git diff --stat` shows `CLAUDE.md` and `.claude/settings.json` and nothing else.
  `AGENTS.md` is **byte-identical** — you declined, so nothing was inserted. The settings
  diff adds the floor's entries and leaves `Read(./secret.txt)`, `Bash(git *)` and `env`
  exactly as they were. The notices told you that your `Bash(git *)` allow covers floor
  entries and has no effect on them, because the host resolves deny, then ask, then allow.
- Step 9: the notice about `AGENTS.md` is repeated, word for word. A declined line is not
  remembered anywhere — its absence is what brings the notice back.
- Step 10: the clone is recognised from the committed record: every committed path is
  `unchanged`, and the only thing to write is `.harnex/state/.gitignore`, which is
  deliberately not committed. It asks nothing.
- Step 11: every check passes. Without the environment variable, four checks skip and say
  which half did not run.
