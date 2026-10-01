## Context

`decide.py`'s `main()` is the only place that reads `OPENROUTER_API_KEY` today
(`os.environ.get("OPENROUTER_API_KEY")` at `plugin/scripts/decide.py:612`), and passes it
straight through to `decide()`'s existing `api_key` parameter, which `call_jev_many`
already treats as "absent" the same way whether it is `None` or empty
(`plugin/scripts/decide.py:456`). Nothing downstream of that one call site needs to
change — the fallback is a key-resolution concern, not a `decide()`/`decide_many()`
interface concern.

`project-setup` already has a settled rule this design must not cross:
"Runtime state stays out of the project's history without touching the project's
rules" — the state directory ignores itself (`.harnex/state/.gitignore` is `*`)
specifically so setup never has to modify the project's own `.gitignore`
(`plugin/scripts/setup.py:67`, `STATE_IGNORE_BODY`). See proposal.md - Why.

The guard already carries five `credentials-never-leave-the-machine` patterns matching
`.env`, `.env.*` and `*.env` at the project root (`plugin/control/guard/patterns.yaml`),
asking before any `Read` or `cat` touches them.

## Goals / Non-Goals

**Goals:**
- `jev` works with the key sitting in a project-local, gitignored `.env` at the project
  root, with zero shell setup and zero shared state between projects.
- The environment variable still wins when both are present — nothing changes for a
  session that already exports the key.
- No new dependency, no new write path in `setup.py`, no change to `decide()`'s or
  `decide_many()`'s signature.

**Non-Goals:**
- Reading, writing, or gitignoring `.env` from `setup.py`. It only prints a notice.
- Supporting more than one key, or a general-purpose dotenv format (comments,
  multi-line values, `export` prefixes, interpolation). One key, one line shape:
  `OPENROUTER_API_KEY=<value>`, optionally quoted.
- Changing where `.harnex.yml`, the journal, or any other harness-owned file lives.

## Decisions

**The `.env` file stays at the project root, not inside `.harnex/state/`.**
`.harnex/state/` already ignores itself entirely and was the first location considered,
since it needs no `.gitignore` reasoning at all. Rejected: the guard's existing
`credentials-never-leave-the-machine` patterns (`Read(.env)`, `Read(.env.*)`,
`Read(*.env)`) match the conventional root-level name; a file at
`.harnex/state/.env` would sit two directories deep and — unverified here, since it is
out of this change's scope to touch `plugin/control/` — may not match those patterns at
all, silently losing the "ask before reading a credential" protection this whole change
exists to work alongside. Root-level `.env` is also the convention every other tool
already looks for, so nothing about a project changes just because it uses `jev`.

**Key resolution happens once, in `main()`, not inside `call_jev_many`.**
`call_jev_many` and `decide()`/`decide_many()` already take `api_key` as a plain
parameter and have no notion of a project path search order — only `main()` has both
the resolved `project` path and the moment before the first call. A small
`resolve_api_key(project: Path) -> str | None` function reads
`os.environ.get("OPENROUTER_API_KEY")` first and only then looks at
`project / ".env"`, returning `None` if neither carries it. `main()`'s one call site
becomes `api_key=resolve_api_key(project)`; every other caller of `decide()` (tests
included) is unaffected because they already pass `api_key` explicitly.

**The `.env` parser is a few lines of stdlib, matching one line shape only.**
Alternatives considered: a dependency such as `python-dotenv`. Rejected for the same
reason C1b kept the rule frontmatter dependency-free (§"What it taught us", C1b) — this
harness's own scripts start instantly under `uv run` with no install step, and the
format needed is one key on one line, not general dotenv syntax. The parser reads lines
matching `KEY=VALUE` (first `=` splits it), skips blank lines and lines starting with
`#`, strips a matching pair of surrounding quotes from `VALUE`, and looks only for the
literal key `OPENROUTER_API_KEY` — anything else in the file is ignored, not
validated, since this change does not aim to be a `.env` linter.

**Setup's notice is informational only, matching `project-setup`'s existing rule.**
The original proposal draft had setup add a `.gitignore` line on explicit approval, the
same pattern the Playwright `.mcp.json` entry uses. That directly contradicts the
settled "SHALL NOT modify the project's own version-control exclusions" requirement, so
the notice carries no write at all: it names the file and the key, once, every run
where `decision_model` is `jev`, and touches neither `.env` nor `.gitignore`. The
person's own `.gitignore` — or a project convention that already excludes `.env` — is
entirely their concern, same as it is for every other tool that reads one.

## Risks / Trade-offs

- **[Risk]** A person sets `decision_model: jev`, never notices the notice, and commits
  a `.env` carrying their key. → **Mitigation:** the notice names the exact risk in its
  own text ("keep this out of version control"); the guard already asks before any
  agent reads or cats `.env*` at the root, so at minimum an agent working in the
  project cannot silently exfiltrate it. Enforcing that the file is actually gitignored
  is out of scope — see Non-Goals.
- **[Risk]** A malformed `.env` (wrong quoting, no `=`) silently yields no key rather
  than an error. → **Mitigation:** this is the same shape `decide()` already returns
  for "no key at all" (`_unresolved(..., reason="OPENROUTER_API_KEY not set")`,
  `plugin/scripts/decide.py:456`) — a malformed line degrading to "absent" rather than
  a parse error is consistent with the interface's existing contract of never raising
  to its caller for a backend failure.
- **[Trade-off]** Because `main()` only reads the file when the environment variable is
  unset, a stale or wrong value sitting in a checked-out `.env` never shadows a
  correctly exported key — but it also means a person who intentionally wants to
  override an exported key with the project's `.env` cannot. Accepted: the reverse
  (environment always wins) is the safer default and matches how every other
  environment-first credential convention behaves.

## Migration Plan

No migration: this is purely additive. A project with no `.env` and no exported key
behaves exactly as it does today (`mock`-shaped unresolved outcome). Rollout is: land
the code, update `docs/PLAN.md`'s C2 entry to note the fallback exists and its C1c
entry to note the notice. No flag, no staged rollout — the fallback only ever engages
when the environment variable is already absent, so there is nothing to roll back that
could regress an existing setup.
