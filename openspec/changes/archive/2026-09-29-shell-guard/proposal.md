## Why

Every safety rule in `plugin/context/rules/safety/` already says `enforced_by: guard` and
names "the shell guard of the same pillar" in its own body — C1c wrote them that way on
purpose, ahead of the mechanism. Right now that mechanism does not exist: the only thing
standing between the agent and a destructive command is the permission floor, which is
coarse by design (§9) and cannot see a command reached through a wrapper, an absolute
path, or a subshell, nor tell a deletion inside a task's declared paths from one outside
them. §4's role matrix and §9 of `docs/PLAN.md` already assume a script that classifies
every command before it runs and asks a decision model about the residue; this change
builds it, closing C4.

## What Changes

- A PreToolUse hook on `Bash`, `guard.py`, that parses a command (splitting on `; && || |`,
  an unparseable command treated as ambiguous) and classifies every part: an entry in the
  read-only allowlist → allow silently; a deny pattern → deny with a reason; an ask
  pattern → ask the person; anything left → the decision model, asked `guard.risk` with
  the command, cwd and branch as state, a 3-second timeout and one retry. Deny never comes
  from the model alone — only from a deterministic pattern. An exception anywhere in the
  guard's own splitting or matching — not the decision-model call, which has its own
  failure path — also resolves to ask, journalled distinctly from a backend failure.
- `patterns.yaml`, the allow/ask/deny pattern lists every `enforced_by: guard` rule feeds —
  the four `safety/*.md` rules and `git/commits-only-when-shipping.md`, the complete set
  today — with a per-role variant keyed on the `agent_type` field Claude Code adds to a
  subagent's tool call, so a role's own list (the builder's, for instance) applies without
  touching the main session's.
- A `guard.risk` decision question — `Score: read_only / reversible / destructive`, state
  `command, cwd, branch, is_worktree`, the type §8 of `docs/PLAN.md` already reserves and
  `decide.py` already lists in `QUESTION_TYPES` but explicitly refuses to build a request
  or parse a response for ("decide.py does not yet build a request for type `score`") —
  asked only for the residue the deterministic lists leave undecided.
- A journal recording every guard decision — allow is not journalled, deny and ask are,
  each with the command and which pattern or decision produced it.
- The permission floor (`plugin/control/floor.json`, from C1c) becomes generated output
  from the same `patterns.yaml` the guard reads, rather than hand-authored, so the two
  layers cannot state different things for the same rule. Every `patterns.yaml` entry
  that names a pattern is one the guard enforces regardless of provenance; the ones the
  host's own permission syntax cannot express are marked so at the entry level and land in
  `floor.json`'s existing `guard_only` section, never in a list the guard itself skips. A
  `guard_only` reason that names no specific command — most of today's do not — carries no
  pattern at all and matches nothing; it exists only so the generated floor still reads
  what is already committed.
- **BREAKING** (internal only, nothing installed changes shape): `floor.json` moves from a
  hand-maintained file to a build artifact; anyone editing it directly loses the edit on
  the next generation. Its format and its entries are unchanged.

## Non-goals

- **A Codex-side guard.** Codex runs under its own sandbox through the Codex plugin (S1);
  a guard hook on that side is a later feature per §9, not this change. This leaves one of
  §4's own promises unmet by C4: its builder·Codex row currently says the ask "has to come
  from harnex's own guard, once C4 lands" — this change's guard hooks `Bash` in the main
  session and Claude subagents only, so a command Codex runs inside its own sandbox is
  still outside its reach. §4 is corrected to say so at plan-sync (`tasks.md` 8.1), not
  reopened here.
- **Calibrating `guard.risk`'s thresholds against real traffic.** The thresholds in
  diagram 05 are the starting point; tuning them from the decision journal is listed in
  §11 as later work, unscheduled.
- **A fail-closed mode.** §9 already settled that a hook failure falls back to the floor
  and the session's permission mode, never to a blanket deny; this change does not reopen
  that decision.
- **Reworking the text or `Enforced by:` lines of the four `safety/*.md` rules or of
  `git/commits-only-when-shipping.md`.** They already name the guard correctly, written
  ahead of it by C1c (or, for the commit rule, C1c's floor entry); this change makes what
  they describe real, not different.
- **Adding a deny-severity pattern for a Bash command.** No rule today asks for one — the
  four safety rules and the commit rule all resolve to *ask*; `plugin/control/floor.json`
  carries no `deny`-listed `Bash(...)` entry, only `deny` for reading a credential file
  directly. `patterns.yaml` v1 carries forward exactly this severity; diagram 05's own
  deny-box examples beyond what a rule states today are illustrative of what the mechanism
  supports, not a claim that anything resolves there yet.

## Capabilities

### New Capabilities
- `shell-guard` (pillar 4, control — `docs/PLAN.md` §8 already places its question file
  at `plugin/control/guard/`, alongside `patterns.yaml`, rather than in pillar 3's
  `orchestration/decisions/` with the routing questions): the PreToolUse hook,
  `patterns.yaml`, per-role lists, the `guard.risk` decision question, and the guard's own
  journal of deny/ask decisions.

### Modified Capabilities
- `permission-floor`: `floor.json` is no longer hand-authored — it SHALL be generated from
  the same pattern source the guard reads, so a rule's coverage in the floor and in the
  guard cannot drift apart. The existing requirement that the floor is "derived from the
  harness's own statements" is tightened to name the shared source and the regeneration
  check.
- `decision-model`: `decide.py` gains request-building and response-parsing for the
  `score` question type — an externally observable addition to the interface, the same
  kind C3 made for `noul`. `score`'s own three-way rule (a threshold per named option,
  not "highest probability wins") is new; `choice` and `noul` are unchanged.

## Impact

- New: `plugin/control/guard/patterns.yaml`, `plugin/control/guard/guard.py` (or
  equivalent layout settled in design), `plugin/control/guard/generate_floor.py` — a
  maintainer step run by hand after editing `patterns.yaml`, like
  `docs/diagrams/build.py`, never called by setup or at runtime —
  `plugin/control/guard/guard-risk.yaml`, a `PreToolUse` entry in `plugin/hooks/hooks.json`,
  the guard's journal file under `.harnex/state/`.
- Changed: `plugin/control/floor.json` becomes generated rather than committed by hand (its
  entries are expected to be unchanged, since it already reflects every safety rule);
  `plugin/control/README.md`'s "Filled by" line, marking C4 done.
- Tests: fixture-driven runs of `guard.py` over recorded hook stdin for every row of
  diagram 05's table, including the internal-error path (an exception during
  classification, distinct from a `guard.risk` backend failure); the hook as a real
  process with the backend stubbed to hang, the script crashing, the interpreter missing,
  and the hook killed at its timeout; floor and pattern lists compared entry by entry,
  both ways (nothing in one without the other).
- Phase: C4 of `docs/PLAN.md` §11. Exit criterion: the table in diagram 05 holds for every
  fixture, with the backend on and off; for every way the hook itself can fail, the floor
  still covers every deny and ask pattern.
