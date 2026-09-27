## Context

See proposal.md for why. What exists today:

- The `canary` rule (`plugin/context/rules/canary/canary-ends-every-answer.md`) declares
  `enforced_by: hook` and says the check "reads the last answer at the end of each turn".
  Its reason still says a missing word "means the instructions are gone", which §3 of the
  plan has since softened to a signal.
- Setup writes the project's choices to `.harnex.yml`, and `plugin/scripts/setup.py` holds
  the one reader of that file, `parse_choices`, which refuses anything it does not
  understand.
- The plugin declares no hook. `plugin/hooks/` does not exist yet; the layout test already
  accepts it as a directory the host reads.
- The existing rule-format test walks from a rule to "an enforcer line"; its docstring
  says C1d walks the other way.

Evidence gathered for this design, on Claude Code `2.1.267` in a scratch project whose
`CLAUDE.md` asked for the word:

- The `Stop` input carries `last_assistant_message` with the answer's full text, plus
  `session_id`, `cwd`, `hook_event_name`, `stop_hook_active` and others.
- The `SubagentStop` input carries the same field and `agent_type`. A `general-purpose`
  subagent ended with the word; an `Explore` subagent did not, because it is not given the
  project's instructions.

## Goals / Non-Goals

**Goals:**

- One script, one hook, one reader of `.harnex.yml`: nothing about the canary is stated
  or parsed twice.
- The inert path — no `.harnex.yml`, or the set not chosen — costs one file lookup and
  prints nothing, because the hook fires in every project on a machine where the plugin is
  installed.
- The check's input is tested against payloads the host really produced.

**Non-Goals:**

- A general hook framework. `C4`'s guard brings the second hook; shared plumbing is
  extracted then, if two scripts actually share it.
- Making the model comply. The check observes; the rule instructs.

## Decisions

### D1 · `Stop` only, not `SubagentStop`

Subagents do not all receive the project's instructions — the built-in `Explore` does not
— so a check on `SubagentStop` would warn on answers that were never asked for the word.
A signal that fires when nothing is wrong teaches the person to ignore it, which destroys
the only value it has. The recording is kept as a fixture and the reasoning as a decision
note, so the question is not reopened without new evidence.

*Alternative:* `SubagentStop` with a matcher listing the agent types known to receive the
instructions. Rejected for now: that list is the host's to change, not harnex's. When
`C2` adds harnex's own `verifier`, whose prompt harnex writes, a `SubagentStop` hook
matched on harnex's agent types becomes a sound option and reuses this script.

### D2 · Warn through `systemMessage`, exit 0, never block

The script always exits 0. When there is something to say, it prints one JSON object with
a `systemMessage`, which the host shows to the person as a warning. It never prints
`decision: block`, never exits 2, and never adds context for the model.

*Alternatives:* blocking with a reason would make the model continue and append the word —
hiding exactly the signal the check exists to raise, and risking a loop. Writing to stderr
with a non-zero exit shows the text as a *failed hook*, which mislabels a finding as a
fault.

### D3 · The project root is `CLAUDE_PROJECT_DIR`, else the input's `cwd`

The host sets `CLAUDE_PROJECT_DIR` for hooks to the directory the session started in; the
input's `cwd` is where the shell is now, which can be a subdirectory. The script looks for
`.harnex.yml` only at that root and does not walk up: a parent directory's choices are not
this project's.

### D4 · One reader: the canary imports setup's `parse_choices`

`.harnex.yml` is "flat on purpose, so that every hook and command can read it". The
script adds `plugin/scripts/` to its path and calls the reader setup already uses, so the
file has one schema and one error message per fault. Importing `setup.py` costs its
module load, which is standard library and the renderer — well inside the budget.

*Alternatives:* a second small reader of two keys would drift from the first on the first
format change. Extracting the reader into its own module now is a refactor with one new
caller; it is the right move when `C2`'s `decide.py` becomes the third reader, and is
noted there.

### D5 · What "ends with the word" means

Strip trailing whitespace, then any trailing run of `*`, `_` and `` ` `` (with whitespace
between them), then compare the end of the text with the word exactly, case included. The
rule says *end* every answer, so a word in the middle does not count; models routinely set
a closing word in bold or code, and that formatting is not non-compliance.

### D6 · The hook command and its time budget

```json
{ "hooks": { "Stop": [ { "hooks": [ {
  "type": "command",
  "command": "uv run --quiet \"${CLAUDE_PLUGIN_ROOT}/feedback/canary/canary.py\"",
  "timeout": 5 } ] } ] } }
```

`uv run`, as every harness script is run (decision 9). The script carries the same inline
metadata block as `setup.py` (`requires-python`, no dependencies), so `uv` runs it in an
isolated environment and never syncs the project's own environment, even in a project
that has one. The script's own work is one file read and one string comparison; the
declared 5 seconds leave room for `uv`'s start-up on a cold cache. The real-process test
asserts a run finishes well inside the declared timeout.

### D7 · Failing without lying

The body of the script runs inside one handler. An unexpected error prints a
`systemMessage` saying the canary was not checked and why, and exits 0. A malformed input
on stdin is handled the same way. A missing or empty `last_assistant_message` prints
nothing: a turn can end with no text to judge — interrupted, or ending on a tool call —
and a warning there would be noise. A timeout or a crash the handler cannot catch is left to the host, which reports a
non-blocking hook error and ends the turn.

### D8 · The rule names its script by path, and the test walks both ways

The rule's enforcer line becomes: `**Enforced by:** the canary check,
\`feedback/canary/canary.py\` (pillar 5), run by the plugin's Stop hook …`. A new test
reads `plugin/hooks/hooks.json`, collects every script a hook command runs (the path after
`${CLAUDE_PLUGIN_ROOT}/`), and checks that each `enforced_by: hook` rule names one of them
and that each of them is named by some rule. Paths, not prose, so the check cannot be
satisfied by a sentence that merely sounds right.

### D9 · Fixtures: recorded, sanitised, varied in code

`tests/fixtures/hooks/2.1.267/` holds the three recorded inputs — `stop.json`,
`subagent-stop-general-purpose.json`, `subagent-stop-explore.json` — with paths replaced
by `/project` and `/transcripts/…` and identifiers by fixed placeholders. The cases the
tests need (word missing, field absent, field empty, word in bold) are derived in the test
from the recorded `stop.json` by changing one field, never written by hand, so the shape
every case is tested against is the host's.

## What setup and update write

No new file, key or settings entry. The hook reads `.harnex.yml`, which belongs to the
project (§6) and which it never writes. The revised rule reaches a project through
`.harnex/rules.md`, which is harness-owned and is re-rendered by setup — and later by
`update` — like any other change to a rule's text. `plugin/hooks/hooks.json` lives in the
plugin, not in the project.

One thing setup writes does change: `AGENTS.md`, for a project that chooses the `canary`
set, gains a `## Canary` section naming the word — found while trying the check by hand
(a model given only the rule has no way to learn the word `.harnex/rules.md` deliberately
never states, since that file is a pure function of the chosen sets and the word is the
project's own fact). This is not a new question, key or file: `setup.py` already held the
answer in `answers.canary`; it now also renders it into the one project file a model
actually reads. It reaches only a project set up (or adopting `AGENTS.md` fresh) after this
change — `AGENTS.md` is created once and setup never rewrites it, so an already-harnessed
project keeps stating the rule with no word beside it until it re-creates the file.

## Guarantees and what happens when they fail

| Guarantee | Kind | When the component fails |
|---|---|---|
| Every answer ends with the word | **instruction** (the rule, in `.harnex/rules.md`) | The model does not follow it; that is what the check is for. |
| A missing word is reported to the person | **detection** (the Stop hook) | If the script errors, it says the canary was not checked. If it crashes past its handler or times out, the host shows a non-blocking hook error. If the plugin is disabled or the host stops sending `last_assistant_message`, nothing is reported: the check goes blind silently — the smoke check per host version is what catches that. |
| The check never blocks work | **prevention**, by construction: the script exits 0 and emits no block decision | A timeout ends the hook, not the turn. |
| The check acts only where chosen | **prevention**, by construction: the inert path returns before reading any answer | A malformed `.harnex.yml` produces a warning, not silence and not a guess. |

The presence of the word proves nothing about the other rules; the design claims no more
than a missing word reveals.

## Risks / Trade-offs

- [The host renames or drops `last_assistant_message`] → The check goes silent, not wrong.
  The fixtures are re-recorded with each "verified against" host version, and the smoke
  check asks for a deliberate miss, so a blind check shows up in the manual run.
- [A hook on every turn in every project] → The inert path does no parsing; the cost is
  `uv`'s start-up per answer. Measured in the real-process test; if it proves noticeable,
  a plain `python3` command is the fallback, at the price of pinning a host Python.
- [The model learns to append the word by habit, after losing the other rules] → Accepted
  and stated: the warning is a signal of non-compliance, not a certificate of compliance.
- [Importing `setup.py` couples pillar 5 to pillar 2's module] → Deliberate (D4), and
  bounded: the canary uses one function and one error type. Extracted when a third reader
  appears.

## Migration Plan

None for projects: a project that chose the `canary` set starts getting the check when the
plugin is updated, and one that did not sees nothing. A project re-running setup after this
change sees `.harnex/rules.md` planned as updated, because the rule's text changed.
Rollback is removing `plugin/hooks/hooks.json`.
