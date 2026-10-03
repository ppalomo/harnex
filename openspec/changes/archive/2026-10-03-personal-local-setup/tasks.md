## 1. Visibility choice and local-visibility config

- [x] 1.1 Add a `visibility` choice (`shared`/`local`, default `shared`) to
      `plugin/scripts/setup.py`'s choices, and verify a test asserts `shared` when the
      key is absent from a project's recorded answers.
- [x] 1.2 Add `.harnex/config.yml`, `local` visibility's own answers file — a new path,
      not a rename of `.harnex.yml` — read the same way `.harnex.yml` is read today, and
      verify a render-then-read round-trip test matches `.harnex.yml`'s own existing
      round-trip test.

## 2. `CLAUDE.local.md` and `.git/info/exclude`

- [x] 2.1 Write `CLAUDE.local.md` (one line, `@.harnex/rules.md`) under `local`
      visibility, and verify a test asserts `AGENTS.md` and `CLAUDE.md` are never
      created or modified, whether or not they already exist, under `local` visibility.
- [x] 2.2 Add `CLAUDE.local.md` to `.git/info/exclude` on `local`-visibility setup, and
      verify `git status --porcelain` reports nothing after a fresh `local` setup in a
      real git repository, both for an empty project and for one with an existing
      committed `AGENTS.md`.

## 3. `.harnex/` under local visibility

- [x] 3.1 Widen `.harnex/`'s self-ignoring `.gitignore` (today's `*` under
      `.harnex/state/`) to the whole directory, for `local` visibility only, and verify
      `shared` visibility's existing `.harnex/state/.gitignore` test still passes
      unchanged.
- [x] 3.2 Verify, with a new test, that every path written under `.harnex/` in a
      `local`-visibility project is reported untracked by `git status --porcelain`,
      matching the `local-visibility` capability's own requirement.

## 4. The permission floor and MCP entries under local visibility

- [x] 4.1 Write the permission floor's entries to `.claude/settings.local.json` instead
      of `.claude/settings.json` under `local` visibility, and verify
      `.claude/settings.json` is byte-identical before and after a `local`-visibility
      setup run.
- [x] 4.2 Register the Playwright MCP entry (for a UI profile) with
      `claude mcp add --scope local` under `local` visibility instead of writing
      `.mcp.json`, and verify `.mcp.json` is untouched — absent or byte-identical — after
      setup.

## 5. A local OpenSpec store

- [x] 5.1 Register a local OpenSpec store (`openspec store setup`) on first
      `local`-visibility setup, keyed to the project's git repository the way Claude
      Code's own auto-memory keys its per-project directory, record the store id in
      `.harnex/config.yml`, and verify a second setup run on the same project reuses the
      recorded id rather than registering a second store.
- [x] 5.2 Add store resolution to `plugin/skills/propose/`, `plugin/skills/apply/`,
      `plugin/skills/verify/` and `plugin/skills/ship/` — the ones that actually touch
      `openspec`, which revealed this task's own original file list was wrong on two
      counts: `plugin/skills/explore/` and `plugin/skills/review/` never call `openspec`
      at all (nothing to resolve there — fixed by a one-line `profiles` source note
      instead, shared with `verify`'s own step 1); and `plugin/scripts/apply_loop.py`
      and `plugin/feedback/scope_check.py` don't go through the `openspec` CLI either —
      they read/write `openspec/changes/<name>/tasks.md` by a path computed directly
      from `--project`, which a `--store` flag on a bare `openspec` call could never
      reach. `apply_loop.py` gained a `--changes-root` parameter (`tasks_md_path`,
      `load_tasks`, `tick_task`) so `tasks.md` can live in the resolved store's own root
      instead; `scope_check.py` needed nothing, since under local visibility a change's
      artifacts never appear in the *project's* own `git status` at all, which is exactly
      what the check already correctly treats as reportable. Separately,
      `plugin/scripts/verify_checks.py` read only `.harnex.yml` for `check_command`, the
      same gap 8.1 found in `update.py` — fixed the same way, checking
      `.harnex/config.yml` first.

## 6. The guided question list

- [x] 6.1 Add the roles/tools question to `local` visibility's question list in
      `plugin/skills/setup/`, stating — at the point Codex is chosen — that it will not
      see the project's rules under `local` visibility, and verify a test asserts the
      statement appears whenever Codex is among the answers.
- [x] 6.2 Verify, with a test, that `local` visibility asks every question `shared`
      visibility asks (profiles, rule sets, features, canary word, decision backend,
      check command) from the same fixed list, plus the roles/tools question, in that
      order.

## 7. The one-time global settings offer

- [x] 7.1 Add the `~/.claude/settings.json` offer
      (`pluginConfigs."agents-md@builtin".options.instructionFiles =
      "claude-md-and-agents-md"`) to `local`-visibility setup, shown and written only
      after an explicit yes, and verify it is never offered under `shared` visibility.
- [x] 7.2 Verify, with a test, that declining the offer leaves `~/.claude/settings.json`
      unchanged, that setup states the consequence at decline time, and that the notice
      repeats on a later `local`-visibility setup run while the setting is still absent.

## 8. The ownership record under local visibility

- [x] 8.1 Keep `.harnex/manifest.json` written and read exactly as today under `local`
      visibility, and verify, with a test, that it is never committed (covered by task
      3.1's directory-wide self-ignore) while a later `update` run still reads it
      correctly. Required extending `plugin/scripts/update.py` itself: it read only
      `.harnex.yml` and had no way to find `.harnex/config.yml` at all, which would have
      made every local-visibility project unupdatable — `read_recorded_choices` now
      checks for `.harnex/config.yml` first, `.harnex.yml` otherwise.

## 9. Final checks

- [x] 9.1 Run `uv run --with pytest pytest`, `claude plugin validate plugin --strict`,
      `claude plugin validate . --strict`, and `openspec validate --all`, and verify all
      four pass. All four pass.

## 10. Documentation

- [x] 10.1 Update `docs/PLAN.md`: add the `C7 · a personal, local-only setup` entry to
      §11 with its exit criterion, and extend §6's ownership table with the `local`
      case, and verify `docs/PLAN.md` still describes the repository as it is. Also
      added a `docs/smoke.md` section (every other delivered phase has one; this one
      was implied, not its own task — hand-run against a real git repository and a
      real registered OpenSpec store, matching exactly what is documented).
