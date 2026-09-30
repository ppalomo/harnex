---
name: verify
description: Verify a change against its specs and recorded check facts, then leave a fresh severity-carrying review for ship to gate. Use when the person wants to verify an implemented change before shipping it.
---

# Verifying a change

You run the project's check-and-facts step deterministically, then give the verifier a
fresh, read-only view of the change. The verifier's review is evidence for a later `ship`
run; this skill presents and records it, but does not decide whether the person may proceed.

## 1. Print the advice line, once, before anything else

Build a small state document:

```json
{"phase": "verify", "task": "<one paragraph on the implemented change being verified>", "profiles": []}
```

`profiles` comes from the project's `.harnex.yml` if it exists (its `profiles` list);
otherwise leave it empty. Then run:

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/decide.py" ask --question phase.route --state <file> --project .
```

Read the one JSON object it prints:

- If `"resolved": true`, print `Decision: verify → <decision> · confidence <confidence>`.
- Otherwise, print `Decision: verify → ask (<reason>)`, then ask the person directly which
  binding to use for the verifier: `codex`, `claude-<model>`, or `human`. Use their answer
  as the binding and proceed to step 2.

The resolved binding controls the step-4 handling below. Print the line before running
checks or reading the diff.

## 2. Run the check-and-facts script and distinguish its two exit-1 cases

Name the change from the current branch:

```
git branch --show-current
```

Find the project's default branch, then compute the branch's base commit as its merge-base
with the current branch. Keep that exact commit as `<base-ref>` for this whole run. It is
the same base-commit concept `review` uses: do not use `HEAD`, a remote tip, or a different
base for the diff, facts, or review record.

Confirm `openspec/changes/<change-name>/` exists before proceeding. If it does not, say so
plainly and stop rather than guessing the change path.

Run the script, capturing stdout, stderr, and its exit status separately:

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/verify_checks.py" --project . --base <base-ref>
```

Do **not** use its exit status alone. A check command that ran and failed exits non-zero
too, but still writes normal facts. Instead parse stdout as exactly one JSON object.

- If stdout is empty and stderr starts `verify-checks: internal-error: no facts file was
  written:`, report that stderr message plainly and stop. Do not start the verifier and do
  not write a ship-gate record.
- If stdout parses, this is the normal path regardless of the script's exit status. Keep
  its `facts_file`, `fingerprint`, and `base_ref` values; do not recompute the fingerprint
  or substitute another base ref.
- Any other unparseable stdout is also an internal failure with no trustworthy facts file:
  report stdout and stderr plainly, then stop without starting the verifier or writing a
  record.

## 3. Read the reviewed inputs from disk

Read the whole diff against `<base-ref>` from disk. Include untracked files too: identify
them with `git status --porcelain=v1 --untracked-files=all` and read their contents, as
`review` does. Save this complete diff evidence to a temporary file for the verifier.

Read the facts file at the exact `facts_file` path from the JSON object in step 2. Do not
glob `.harnex/state/verify/` for a different check run.

## 4. Start the verifier once, and show its review unchanged

Use the step-1 binding mechanically where the host supports it. In every Claude-subagent
case, hand the `verifier` the current change's directory, the complete diff file, and the
facts-file path, and tell it to read both from disk. Do not ask it to run the check command
or Playwright.

- For `claude-<model>`, start the `verifier` with the `Agent` tool,
  `subagent_type: verifier`, and `model: <model>` (for example, `claude-opus` means
  `model: opus`).
- For `codex`, state plainly that this binding is not currently actionable: the verifier is
  a Claude-only role prompt. Fall back to starting the `verifier` as a Claude subagent
  without a model override.
- For `human`, do not start an `Agent` subagent. Give the person those same three paths and
  ask them to provide the verifier review; use that returned review in the following steps.

Present the verifier's review exactly as returned. Every finding, including its
`blocking` or `advisory` severity, must be shown without summarising, omitting, or revising
it.

## 5. Record this exact review for `ship`

From the same returned review, make one finding object for every finding it names:

```json
[{"severity": "blocking|advisory", "summary": "the finding exactly as returned"}]
```

Use `[]` only when the verifier plainly found no findings. Save that JSON list to a
temporary file, then record it with the facts JSON's unchanged base ref and fingerprint:

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/ship_gate.py" record --project . \
  --change <current-branch-name> --base-ref <facts-json-base-ref> \
  --fingerprint <facts-json-fingerprint> --findings-json @<findings-file>
```

This writes the stable `.harnex/state/verify/<change>.json` record that `ship` reads. Do
not skip this fresh record after a normal verifier run, including one containing a blocking
finding.

## What this skill never does

- Start the verifier after the check-and-facts step signals an internal error.
- Block the person itself; `ship` applies any later refusal.
- Skip recording a fresh, normal verifier run.
- Summarise away a finding or its severity.
