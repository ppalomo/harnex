---
name: apply
description: Run a change's tasks through a builder — Codex or a Claude fallback subagent — one at a time, checked and ticked by the loop itself, never by the builder. Use when the person is ready to turn a proposed change's tasks.md into code.
---

# Applying a change

You drive `plugin/scripts/apply_loop.py` for every deterministic step — routing, checks,
fingerprints, run state, ticking — and you drive the builder yourself, since starting one
is a session-level action no script can take. The person sees the routing decision for
every task up front, then one task at a time: what changed, what the check said, and
whether it was accepted, fixed once, or escalated. They never see a fingerprint, a run-state
transition, or raw `git status` output as something to interpret.

The script is at `${CLAUDE_PLUGIN_ROOT}/scripts/apply_loop.py`. Run it with `uv run`.

## 1. Which change, and is it ready

If the person named a change, use it. Otherwise look at `openspec/changes/` and ask if
more than one has an unticked `tasks.md`. Run `openspec status --change <name> --json` —
`apply` needs `tasks` to already be `done` (proposal, specs, design and tasks all exist);
if it is not, say what is missing and stop, rather than guessing at what the person wants
built.

## 2. Put the change on its own branch

Codex has no way to target a branch or worktree of its own — isolation is `apply`'s own
job. Check out a branch named after the change (creating it from the project's default
branch if it does not exist yet) before anything else runs. Every builder call in this
run happens with that branch checked out.

## 3. Read the tasks, and route every one of them at once

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/apply_loop.py" route --project . --change <name>
```

This reads every unticked task from `tasks.md`, asks `task.route` for all of them
together — one call, each task's own text and declared paths embedded in its own
question, per `docs/PLAN.md` §10's isolation and §8's routing table — and prints one
`Decision: apply(<task id>) → <binding> · confidence <n>` line per task before any
builder starts, so the person sees the whole run's routing up front. A task whose line
says `→ ask (...)` was not resolved; ask the person which binding to use for it before
that task's turn comes, rather than guessing.

## 4. For each task, in order

### 4.1 Snapshot, then start the routed builder

```
git status --porcelain=v1 --untracked-files=all > <a temporary "before" file>
git rev-parse HEAD    # keep this — step 4.3's `accept` call needs it as --head-before
```

Then start the task's own routed builder, passing exactly what
`plugin/orchestration/roles/builder.md` says it is handed: the task's own text, its
declared paths if it has any, and the project's own check command (read from
`AGENTS.md`, or the profile it names).

- **Claude fallback:** start the `builder` subagent (the `Agent` tool,
  `subagent_type: "builder"`).
- **Codex:** `/codex:rescue --wait <the task's own text>`, run with the branch from
  step 2 already checked out, so the call lands in the right tree — the command itself
  takes no `--cwd` of its own to pass. If the person asked for the background form
  instead, record the job id `apply_loop.py`'s run state needs for recovery (step 6)
  before moving on.
- **Human:** tell the person what the task asks for and wait for them to say they are
  done.

Record the task's transition to `delegated`:

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/apply_loop.py" state-transition --project . \
    --change <name> --task-id <id> --status delegated \
    --data '{"binding": "<codex|claude|human>"}'
```

### 4.2 Snapshot again, and check what changed

```
git status --porcelain=v1 --untracked-files=all > <a temporary "after" file>
```

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/apply_loop.py" check --project . \
    --paths "<the task's declared paths, one per line, or empty>" \
    --before <before file> --after <after file>
```

If the task declares no paths, `check`'s own `declared_violations` is empty by
construction (there is nothing declared to compare against) — ask `task.scope` instead,
once, with the same before/after diff as its `changed_paths`:

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/apply_loop.py" scope --project . \
    --change <name> --task-id <id> --after <after file>
```

### 4.3 Run the check command, and decide whether to accept

Run the project's own check command (from `AGENTS.md`, or the profile it names) and note
its exit code. Take a fingerprint of the tree the check ran against:

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/apply_loop.py" fingerprint --project . --base <the branch's base commit>
```

Then ask whether every fact holds — the builder reported done, the check exited 0, no
declared-path or protected-path violation, `task.scope` (if asked) said in scope, `HEAD`
and the branch's refs did not move, and the fingerprint at acceptance still matches the
one the check ran against (a fresh `fingerprint` call, compared to the one just taken):

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/apply_loop.py" accept --project . \
    --builder-done <true|false> --check-exit-code <n> \
    --check-result <the check verb's JSON, saved to a file> \
    --scope-result <the scope verb's JSON, saved to a file, or omit> \
    --head-before <HEAD before the builder ran> --head-after <HEAD now> \
    --fingerprint-at-check <fingerprint> --fingerprint-at-acceptance <fingerprint>
```

`accepted: true` and no `reasons` means every fact held — go to 4.5. Anything else means
not accepted, whatever the builder or the check said on its own — go to 4.4.

### 4.4 One fix attempt, then escalate

Not accepted, and the run state's own `fixed` field for this task is not yet `true`
(check `state-show` — this is what makes the one-attempt limit survive an interruption,
not just the current conversation's own memory of it): record the attempt before making
it —

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/apply_loop.py" state-transition --project . \
    --change <name> --task-id <id> --status checked --data '{"fixed": true}'
```

— then hand the same builder the check's own output and the current diff, and ask for
exactly one fix. Repeat 4.2–4.3 once. Still not accepted after that, or `fixed` was
already `true` when you got here: transition to `escalated`, tell the person what was
seen and why, and stop the run — do not attempt a further fix on your own, and do not
move on to the next task.

### 4.5 Accept and tick

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/apply_loop.py" state-transition --project . \
    --change <name> --task-id <id> --status accepted
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/apply_loop.py" tick --project . --change <name> --task-id <id>
```

The loop ticks; the builder never does — this is the only place in the whole run
`tasks.md` is written. Tell the person the task landed, with the check's own evidence,
then move to the next task.

## 5. When every task is either accepted or the run stopped on an escalation

Say which tasks landed and which, if any, is still open. Do not commit, open a PR, or
touch `openspec/` beyond `tasks.md`'s own ticks — that is `ship`'s job (`C5`), not this
one.

## 6. Resuming an interrupted run

Before step 3, check for existing run state:

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/apply_loop.py" state-show --project . --change <name>
```

A task already `accepted` is untouched — never revisit it. A task `delegated` to Codex:
look its job up with `/codex:status <job-id>`; if the lookup fails, or shows no progress
past a few minutes, treat it as unrecoverable rather than trusting `running` at face
value — nothing checks a job's own liveness, and a normal session ending already killed
it, so "resume" usually means "the job is gone," not "the job is still running." Show
the person the diff since the task's own base fingerprint and ask: keep it and check it,
discard it (a destructive action, so it asks), or delegate again — never re-delegate onto
a tree the base fingerprint no longer matches without asking first. A task `checked` but
not yet `accepted`: re-run 4.3 from its recorded state rather than re-delegating. Anything else
(`queued`, or no state at all): start it fresh at step 4.

## What this skill never does

- Tick a task itself before its check has passed, or on the builder's own report alone.
- Let a builder touch `tasks.md`, `openspec/`, or `.harnex/`, whatever the task declares.
- Retry a failed check more than once per task before escalating.
- Re-delegate a Codex job onto a tree that no longer matches its own base fingerprint
  without asking first.
- Commit, open a pull request, or run `verify` or `ship`'s own steps.
