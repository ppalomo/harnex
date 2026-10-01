## Why

`decision-model`'s `jev` backend reads `OPENROUTER_API_KEY` from the process
environment only. The only way to make it available today is to export it somewhere that
reaches every `claude` session — a shared shell profile, for instance — which puts one
key in front of every project a person works on and has nothing to do with which project
is actually running. A project-local, gitignored `.env` is the convention the harness
already treats specially (`credentials-never-leave-the-machine`, `plugin/control/guard/patterns.yaml`,
asks before any `Read` or `cat` of `.env*`), but nothing reads one yet.

## What Changes

- `decide.py`'s `jev` backend, before treating the key as absent, reads a `.env` file at
  the project root (the same `--project` it already takes) for an `OPENROUTER_API_KEY=`
  line — only when the variable is not already set in the process environment, so an
  explicit environment still wins and nothing here changes behavior for a session that
  already exports the key itself.
- The `.env` parser is a stdlib-only, few-line reader for flat `KEY=VALUE` lines (no
  interpolation, no export syntax, no third-party dependency) — the same minimalism C1b
  chose for the rule frontmatter and for the same reason: nothing here needs a shell.
- `setup.py`'s plan gains a purely informational notice, shown only when the project's
  answer for `decision_model` is `jev`: the project needs a `.env` with
  `OPENROUTER_API_KEY=` at its root, and the person is responsible for keeping it out of
  version control. `project-setup` already has a settled rule that setup never modifies
  the project's own version-control exclusions (`.harnex/state/.gitignore` ignores
  itself precisely so the project's own ignore file is never touched); this notice keeps
  that rule intact — setup never reads, writes, or touches `.env` or `.gitignore` for it.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `decision-model`: the `jev` backend's key resolution gains a project-local `.env`
  fallback, tried only when the environment does not already carry the key.
- `project-setup`: the plan gains a purely informational `.env` notice, shown only when
  `jev` is chosen; it reads and writes nothing.

## Impact

- **Pillar(s):** orchestration (`plugin/scripts/decide.py`, the decision interface) and
  context (`plugin/scripts/setup.py`, project setup).
- **Code:** `plugin/scripts/decide.py` (key resolution order), `plugin/scripts/setup.py`
  (the new, purely informational notice — no write path, no `.gitignore` touched), their
  existing tests.
- **No new dependency, no new committed template beyond the notice text itself** — the
  `.env` file is never committed and the harness never writes to it.
- **Phase:** this is a follow-on fix to `C2 · explore and propose`'s `decision-model`
  capability (`decide.py`, delivered in change `explore-and-propose`) and to `C1c · setup
  writes a project`'s `project-setup` capability, not a new roadmap phase. It does not
  reopen either phase's design — `decide(question_id, state)`'s interface and return
  shapes are unchanged, only where the `jev` backend looks for its key.
- **Exit criterion:** a project with `decision_model: jev` and no exported
  `OPENROUTER_API_KEY` resolves the key from its own `.env` and nothing else on the
  machine; a project with the key already exported behaves exactly as before; setup's
  plan shows the notice only when `jev` is chosen and never reads or writes `.env` or
  `.gitignore`.

## Non-Goals

- No general-purpose `.env`/dotenv library, and no support for values beyond
  `OPENROUTER_API_KEY` — this is one key, read one way, for one backend.
- No shared, cross-project credentials file or shell-profile integration — explicitly
  rejected in favor of a file scoped to the project that uses it.
- No change to the guard's existing `.env` protection rules
  (`credentials-never-leave-the-machine`) — this change is a reader, not a new exposure.
- No mechanism for the harness itself to write, print, or transmit the key's value; the
  person always types it into their own `.env`.
