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
