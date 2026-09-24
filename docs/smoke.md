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
