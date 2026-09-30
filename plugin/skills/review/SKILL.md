---
name: review
description: Review a change's diff for code quality — bugs, simplification opportunities, and efficiency concerns — without blocking verify or ship. Use when the person wants an independent review of work that has a diff.
---

# Reviewing a change

You give the person an independent, read-only code-quality review of a change's diff. This
is a recommended step they may run whenever a change has a diff: it is separate from
`verify` and `ship`, and nothing it finds changes `ship`'s own gate.

## 1. Print the advice line, once, before anything else

Build a small state document:

```json
{"phase": "review", "task": "<one paragraph on what is being reviewed>", "profiles": []}
```

`profiles` comes from the project's `.harnex.yml` if it exists (its `profiles` list);
otherwise leave it empty. Then run:

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/decide.py" ask --question phase.route --state <file> --project .
```

Read the one JSON object it prints:

- If `"resolved": true`, print `Decision (advice): review → <decision> · confidence
  <confidence>`.
- Otherwise, print `Decision (advice): review → unavailable (<reason>)`.

Either way, **do not ask the person to pick a tool or model.** The line is advisory only:
this phase runs in the main session, and the person has no routing choice to make. Then
move straight on.

## 2. Read the change's diff from disk

Read the whole diff against the branch's base commit: the merge-base of the current branch
and the project's default branch. This is the same base-commit concept `apply_loop.py`'s
fingerprint uses: the diff against that base, plus untracked files. Use `git diff` for the
former; if untracked files are relevant, identify them with `git status --porcelain=v1
--untracked-files=all` and read their contents too.

A diff is the only precondition. Do not require `verify` or `ship` to have run, and do not
run either command here.

## 3. Start the reviewer once, and show its review

Start the `reviewer` subagent (the `Agent` tool, `subagent_type: reviewer`) with the
change's directory and the diff to review, always setting `model: opus`. This caller step
is the one and only place the reviewer's fixed-model contract is enforced: do not look up
who built the code, compute a binding, or read a journal or other run-time state.

Present its review exactly as it comes back — do not summarise away a finding, and do not
revise the diff on its behalf. Whether to act on what it found is the person's call.

## 4. Finish

Tell the person the review is complete. This skill never writes anything, never blocks,
never requires `verify` or `ship` to have run first, and never affects `ship`'s own gate.

## What this skill never does

- Write anything.
- Block, or require another command to have run first.
- Affect `ship`'s disagreement rule.
- Call the reviewer more than once per run.
