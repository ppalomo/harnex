---
name: propose
description: Turn an idea into a reviewable change — proposal, specs, design and tasks — without the person ever running openspec themselves. Use when the person is ready to commit an idea to a change, whether or not they explored it first.
---

# Proposing a change

You drive the `openspec` CLI yourself so the person never has to. They see a plain
conversation, one advice line, the finished artifacts, and a review — never an artifact id,
a schema name, or a raw command's output pasted at them as something to interpret.

## 1. Print the advice line, once, before anything else

Same as `explore`'s step 1: build `{"phase": "propose", "task": "<one paragraph on what is
being proposed>", "profiles": [...]}`, run `decide.py ask --question phase.route`, and
print `Decision (advice): propose → <decision> · confidence <confidence>` or `Decision
(advice): propose → unavailable (<reason>)`. Never ask the person to pick a tool or model
for it — this phase runs in the main session too.

## 2. Local visibility: resolve the change's own store, if there is one

Read the project's recorded choices: `.harnex/config.yml` if it exists (`local`
visibility), otherwise `.harnex.yml` (`shared`, or no recorded choices yet — skip the
rest of this step). Under `local` visibility, every `openspec` call below takes
`--store <store_id>` (the id recorded there), and the change's artifacts live in that
store's own root, never under this project's `openspec/`. Nothing else in this skill
changes: it is the one flag, carried on every `openspec` call that follows.

## 3. Snapshot the working tree before anything is written

```
git status --porcelain=v1 --untracked-files=all > <a temporary file>
```

Keep that file's path; the scope check at the end needs it. This has to happen before the
change directory exists, or the change's own new files would already be "before" state.
This snapshot is always of the project's own tree, whatever visibility applies: under
`local` visibility the change's artifacts never appear in it at all, which is exactly
step 6's point.

## 4. Learn what the person wants, and name the change

If the idea is not already clear from the conversation (including a prior `/harnex:explore`
run), ask what they want to build. Derive a short kebab-case name from it. Then:

```
openspec new change "<name>"  # [--store <id>, local visibility only]
```

If a change with that name already exists, tell the person and ask whether to continue it
or pick a different name — do not silently overwrite or silently rename it.

## 5. Write every required artifact, asking only in plain language

```
openspec status --change "<name>" --json  # [--store <id>, local visibility only]
```

tells you which artifacts the schema requires and their dependency order. For each one
that is `ready`:

```
openspec instructions <artifact-id> --change "<name>" --json  # [--store <id>, local visibility only]
```

gives you its template and rules. Write it to the path it names, reading any completed
dependency from disk first (never from what you remember writing). Ask the person for
whatever the artifact actually needs from them — what problem this solves, what it should
and should not do, how it should work — in their own words; never ask them to name a
"capability", an "artifact", or a "schema". Re-check `openspec status` after each write:
one artifact can unblock another. Keep going until every artifact the change's own schema
requires exists.

## 6. Check the change stayed inside its own directory

```
uv run "${CLAUDE_PLUGIN_ROOT}/feedback/scope_check.py" check --change "<name>" --before <the snapshot file> --project .
```

This always checks the project's own tree — never `--store`, whatever visibility
applies. Show the person whatever it reports. If it names a path, say so plainly — it is
a report, not a failure, and finishing this phase does not depend on it being clean.

## 7. Start the verifier once, and show its review

Start the `verifier` subagent (the `Agent` tool, `subagent_type: verifier`) with the
change's directory to review. Present its review exactly as it comes back — do not
summarise away a finding, and do not revise an artifact on its behalf. Whether to act on
what it found is the person's call.

## 8. Finish

Tell the person where the artifacts live — `openspec/changes/<name>/` under `shared`
visibility, or the resolved store's own root under `local` — and that reviewing or
revising them is the next step. Do not imply a command exists to build them if it does
not yet.

## What this skill never does

- Write anything outside the new change's own directory without reporting it (step 6).
- Ask the person to name an OpenSpec concept instead of describing what they want.
- Call the verifier more than once per run, or edit an artifact after it has reviewed.
- Tick anything, since there is no `tasks.md` execution here — that is `apply`'s job.
