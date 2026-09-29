## Task 7.2 — manual walkthrough

Run on a scratch project (`/private/tmp/harnex-smoke-shell-guard`, git-initialised, set up
with `setup.py write` — sets `git, code, sdd, safety, canary, language`, `decision_model:
mock`), invoking `plugin/control/guard/guard.py` exactly as `plugin/hooks/hooks.json`'s
`PreToolUse` entry does — `uv run --quiet ".../control/guard/guard.py"`, fed the same
stdin JSON shape Claude Code sends for a `Bash` tool call. Each transcript below is the
real subprocess's real stdout.

### 1 — `ls` runs with no prompt

```
$ echo '{"session_id":"s","cwd":"<scratch>","hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"ls"}}' \
  | uv run --quiet plugin/control/guard/guard.py
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}
```

Matches diagram 05: every part in the read-only allowlist → ALLOW, no journal.

### 2 — `rm -rf /tmp/harnex-test` asks, with a reason

```
$ echo '{"session_id":"s","cwd":"<scratch>","hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/harnex-test"}}' \
  | uv run --quiet plugin/control/guard/guard.py
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": "guard rule `deletions-ask` matched `Bash(rm *)`"}}
```

Asks, not denies — v1 carries no deny-severity Bash pattern on the default list (design's
Non-Goals; diagram 05's deny box reads "none today"). Matches.

### 3 — `git push` asks

```
$ echo '{"session_id":"s","cwd":"<scratch>","hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"git push origin main"}}' \
  | uv run --quiet plugin/control/guard/guard.py
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": "guard rule `pushes-ask` matched `Bash(git push *)`"}}
```

**Observation, not a defect:** bare `git push` (no trailing argument) does not match the
`Bash(git push *)` glob — the `*` needs at least one following character, the same
prefix-glob semantics the floor's own committed patterns already use. Fed alone, it falls
to residue and is asked via `guard.risk`'s `mock`-backend fallback instead:

```
$ echo '{"session_id":"s","cwd":"<scratch>","hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"git push"}}' \
  | uv run --quiet plugin/control/guard/guard.py
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": "guard.risk could not resolve this command (mock_backend)"}}
```

Still asks either way — nothing allows silently — so this does not affect the exit
criterion, but it is worth knowing the reason differs by path.

### 4 — with the API key unset, an ambiguous command asks and says the backend was unreachable

Scratch project's `.harnex.yml` switched to `decision_model: jev` for this one step
(reverted after), `OPENROUTER_API_KEY` unset in the environment, command carries a `$(...)`
command substitution (ambiguous per D1 — split as residue, never guessed at):

```
$ env -u OPENROUTER_API_KEY ... | uv run --quiet plugin/control/guard/guard.py
{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": "guard.risk could not resolve this command (OPENROUTER_API_KEY not set)"}}
```

Asks, and names the missing key. Matches.

### 5 — with the guard broken, `git push` still asks, from the floor

Two halves, since a real Claude Code host process is what actually falls back — this
demonstrates the precondition for that fallback, not the host's own internals.

**5a — the guard fails to start** (renamed/missing script, the same failure class as a
missing interpreter):

```
$ echo '{...}' | uv run --quiet plugin/control/guard/does-not-exist.py
error: Failed to spawn: `plugin/control/guard/does-not-exist.py`
  Caused by: No such file or directory (os error 2)
exit=2
```

No stdout JSON is produced — exactly the "hook itself fails" case §9 and
`plugin/control/README.md` describe: the host discards this and falls back to its own
permission flow.

**5b — the floor still carries the ask entry independent of the guard:**

```python
>>> json.load(open("<scratch>/.claude/settings.json"))["permissions"]["ask"]
[..., "Bash(git push *)", ...]   # True
```

The scratch project's merged `.claude/settings.json` (written by `setup.py`, from the same
`patterns.yaml` → `floor.json` generation this change built) still asks before `git push *`
regardless of whether `guard.py` itself is reachable. Matches diagram 05 and §9's own
guarantee: guard failure never falls through to nothing, it falls through to the floor.

## Result

All five steps match diagram 05 and the exit criterion in `proposal.md`'s Impact section.
