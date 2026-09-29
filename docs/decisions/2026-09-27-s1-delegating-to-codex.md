# S1 · delegating to Codex

**Date:** 2026-09-27, corrected 2026-09-28, updated 2026-09-28 with a live run ·
**Phase:** S1 (before C2) · **Status:** answered from source and tests, and now from one
live run — the restriction is per-model, not account-wide: `gpt-5.6-terra` negotiates
successfully end to end, `gpt-5.1-codex-max` still returns the identical 400 in the same
session · **Verified against:** `codex@openai-codex` plugin 1.0.6, `codex-cli` 0.158.0

## The question

§10's build loop and §4's role matrix assume answers to four things about `/codex:rescue`
before any code depends on them: does it take a task reliably, and can it be pointed at a
branch or worktree; how are its job status and result read back, and what survives an
interruption; what does its sandbox let it do to `.git` and to paths outside the
workspace; what evidence comes back. Timeboxed, run against a scratch repository, no code
under `plugin/`.

## What was attempted

A throwaway scratch repo (git-init'd, one commit), then a live `task` run through
`codex-companion.mjs` — the script `/codex:rescue` itself shells out to, one call, no
retries, per `commands/rescue.md` and `agents/codex-rescue.md`. Every model tried
(`gpt-5.1-codex-max`, the account's own default in `~/.codex/config.toml`, down through
`gpt-5.1-codex`, `gpt-5-codex`, `gpt-5.1`, `gpt-5`, `o3`, `gpt-4o`, and plain `o4-mini`)
returned the same:

```
warning: Model metadata for `<model>` not found. Defaulting to fallback metadata; this can degrade performance and cause issues.
400 invalid_request_error: '<model>' is not supported when using Codex with a ChatGPT account
```

reproduced both through `codex-companion.mjs task` (which drives `codex app-server` over
JSON-RPC, never the `exec` subcommand) and bare `codex exec`, unchanged after updating
`codex-cli` from 0.155.1 to the then-latest 0.158.0, and **unchanged after the machine's
owner re-ran `codex login` from scratch mid-spike.** **This is not the account/plan
restriction the first pass of this note assumed** — the plugin's own README is explicit
that "ChatGPT subscription (incl. Free) or OpenAI API key" both work, and the plugin's own
readiness check agrees this account is fine:

```
node codex-companion.mjs setup --json
→ "ready": true, "auth": { "available": true, "loggedIn": true,
   "detail": "ChatGPT login active for <the owner's account>", "verified": true }
```

So the login is genuinely active and verified, and still every model tried gets the
identical "metadata not found" warning and the identical 400 — including `o4-mini`, which
is not a Codex-family model and has no plan-gating reason to fail the same way. `codex
doctor`'s websocket check shows `server model present: false` for the session. The
evidence rules out a stale token (fresh login didn't change anything) and rules out
"ChatGPT accounts need an API key" (the plugin's own docs and diagnostic both say
otherwise, and auth is `verified: true`). What's left is a model-capability negotiation
that fails between this specific account and the backend for every model tried, at a layer
neither `codex login` nor the plugin can self-diagnose further — most plausibly an
OpenAI-side entitlement or rollout gap on the account itself (e.g. Codex enablement at
chatgpt.com not fully active for headless use), which is outside what this spike, or
harnex, can resolve from the terminal.

**Every answer below still comes from reading `scripts/codex-companion.mjs`,
`scripts/lib/{workspace, git, codex, job-control, tracked-jobs, state}.mjs`,
`hooks/session-lifecycle-hook.mjs`, `tests/runtime.test.mjs`/`git.test.mjs` (which drive
the same code against a fake Codex fixture), and now also `codex exec --help`, `codex
doctor`, and the plugin's own `setup --json` diagnostic — not from a completed live task
run.** That remains the exit criterion this note cannot fully meet; see "What would reopen
this."

## The answers

**1. Reliability and targeting.** The command is a thin, one-shot forwarder: one `Bash`
call to `node codex-companion.mjs task ...`, stdout returned verbatim, no interpretation
or retry on the plugin's side — reliability is Codex's, not the wrapper's. It never
creates a branch or worktree: `resolveWorkspaceRoot(cwd)` just walks up to the git root of
whatever `cwd` is and runs there (`workspace.mjs:3-9`); a full-source grep for `worktree`
finds nothing except an unrelated test fixture path. `task`'s only value options are
`model`, `effort`, `cwd`, `prompt-file` (`codex-companion.mjs:762-767`) — no `--base` or
`--branch`. **Pointing it at a branch means the caller checks out that branch (or sets up
a worktree) first and passes `--cwd` at that directory.** §10 must supply its own
isolation; nothing on the Codex side does it.

**2. Job status/result readback; interruption.** `task` (foreground) blocks and returns
`{status, threadId, turnId, rawOutput, touchedFiles, reasoningSummary}`
(`codex-companion.mjs:511-529`). `task --background` spawns a **detached** process
(`spawn(..., {detached:true, stdio:"ignore"}); child.unref()`,
`codex-companion.mjs:671-681`) that outlives the invoking turn and even a crash of the
parent. State is a JSON record per job id, outside the repo, keyed by a slug+hash of the
repo path (`state.mjs:29-43`) — no collision with `.harnex/state/`. `/codex:status` and
`/codex:result` read that record back, and an explicit job id lets a **new session**
recover a job a prior session launched (`job-control.mjs:256-279`).

Two gaps matter to §10's recovery contract:

- **Nothing checks liveness of a "running" job's pid.** `runTrackedJob`
  (`tracked-jobs.mjs:142-204`) only flips status on normal completion or an in-process
  error. If the detached worker dies uncleanly (OOM, machine crash), the record stays
  `status: "running"` with a stale pid forever, and `/codex:result` just reports "still
  running" (`job-control.mjs:270-272`). `apply` cannot trust "running" at face value; it
  needs its own staleness judgment (e.g. no progress-log growth for N minutes) before
  treating a job as recoverable rather than lost.
- **A clean session end kills that session's own jobs.** The `SessionEnd` hook
  (`hooks/hooks.json`, `session-lifecycle-hook.mjs`) explicitly kills any job whose
  `sessionId` matches the ending session — proven in `runtime.test.mjs:1804-1924`. A
  background rescue survives across sessions only if the session ends **uncleanly**
  (a crash), not on a normal exit or `/clear`. §10's "look up the Codex plugin's job status
  first" holds for a crash; it does not help after the person quits normally mid-task.

**3. The sandbox, on `.git` and outside the workspace.** `approvalPolicy` is hardcoded to
`"never"` for every call (`codex.mjs:67,80`): Codex, once dispatched, never itself pauses
for approval — every ask/deny in the loop has to come from harnex's own guard. `sandbox`
is `"read-only"` unless `--write` is passed, giving `"workspace-write"`
(`codex.mjs:68,81`; `codex-companion.mjs:491`) — this is Codex CLI's own sandbox concept
(writes confined to cwd/tmp; network typically off), not something the plugin narrows or
widens. **The plugin itself never runs a git command as part of a task** — every
`git commit`/`checkout` in the tests is fixture setup, never something
`codex-companion.mjs` issues. Whether the model, inside its own sandbox, chooses to run
`git commit` is between it and that sandbox; nothing in the plugin checks HEAD or refs
before or after, and no protected-path check exists on this side at all — both are on
harnex's own `apply` to add, exactly as §10 already assumes, and this spike could not
exercise the live case to confirm or deny it further.

**4. What evidence comes back.** Not a diff. `task`'s payload is `{status, threadId,
turnId, rawOutput, touchedFiles, reasoningSummary}` — a file-path list and the model's
final text, not a diff (`codex.mjs:126ff`, `codex-companion.mjs:511-517`). A diff exists
only for `/codex:review`/`/codex:adversarial-review`, a different command
(`collectReviewContext` in `git.mjs`). **For `task`, the caller must run `git diff`/`git
status` in the workspace itself once the job reports done.**

## What this confirms and corrects in the plan

- §10's "evidence is bound to the tree it describes" (fingerprint before/after, `git diff`
  read by `apply`) was already the right design: Codex's `task` returns no diff, so
  harnex's own fingerprinting is the *only* source of evidence, not a second one layered
  on top of something Codex provides.
- §10's "a task left *delegated* is looked up in the Codex plugin's job status first" is
  correct, with one addition the plan should carry: recovery-by-lookup is sound mainly
  after a crash, since a clean session end kills the session's own background jobs. A
  task interrupted by the person quitting normally is not recoverable this way, and
  `apply` needs a staleness rule (not just "running"/"done") because a dead pid is not
  reported as such.
- §4's row for the Codex builder ("destructive commands … Codex's own sandbox", "credentials
  never leave the machine … Codex sandbox") is **unconfirmed by this spike**, not
  confirmed: `approvalPolicy: "never"` and a `read-only`/`workspace-write` toggle are
  what the source shows, but whether that sandbox actually stops a live model from
  writing outside the workspace or touching credentials was never observed running,
  only asserted by the CLI's own contract. Record it as read from source, not measured.
- Branch/worktree isolation for a delegated task is entirely harnex's to build — checkout
  or worktree, then `--cwd` — as §10 assumed, now confirmed rather than assumed.

## 2026-09-28 update — a live run, model-specific, not account-wide

The entitlement gap above is corrected, not confirmed: this account does not fail to
negotiate *any* model, it fails to negotiate the eight models this spike happened to try.
The owner opened Codex interactively and could select `gpt-5.6-terra`, one of OpenAI's
current flagship models — named by generation (`gpt-6`, `gpt-5.6`) crossed with a
capability tier (`astra`, `sol`, `luna`, plus `terra` as a 5.6-only mid tier):
`gpt-6-astra`, `gpt-6-sol`, `gpt-6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`.
None of these six was among the eight models originally tried.

Three live calls, against a fresh scratch repository (git-init'd, one commit — same
method as the original attempt), same session, same machine:

1. `codex exec --model gpt-5.6-terra --sandbox read-only "Reply with the single word:
   pong"` — succeeded, no metadata warning, no 400. `pong` back, 7,025 tokens.
2. `codex-companion.mjs task --model gpt-5.6-terra --cwd <scratch> --prompt-file …` — the
   actual mechanism `/codex:rescue` shells out to, not `codex exec` directly — asked to
   write `hello.txt`. With the plugin's default sandbox (no `--write`) it refused,
   telling the model itself the workspace was read-only; with `--write` it reported
   `Applying 1 file change(s)` and created the file, confirmed on disk and as
   `?? hello.txt` in `git status --short`.
3. `codex exec --model gpt-5.1-codex-max --sandbox read-only "Reply with the single word:
   pong"`, immediately after, same account, same session — the identical `Model metadata
   … not found` warning and the identical 400 the original spike recorded.

**Confirmed by observation for the first time**, closing the gap C3 was left to budget
for: §3's sandbox claim (`read-only` blocks a write; `--write` allows one confined to the
workspace) and §4's evidence claim (`task`'s payload is progress text and a touched-file
list, not a diff — the caller reads `git status`/`git diff` itself, exactly as §10
already assumed). **Still not retested live:** answer 2 — job status, interruption,
background recovery — since this was a foreground `task` call, not `--background`; that
part of S1 stands only on source and the fake-fixture tests, unchanged.

**What this corrects in §4 and §13 of the plan:** the restriction is per-model, not
account-wide. `gpt-5.6-terra` is confirmed live; the other five current flagship models
are untested — this update has no evidence either way for them, only that they are not
among the eight already ruled out. Until C3's own config picks a default, treat
`gpt-5.6-terra` as the one model this account is known to reach, and re-run the one-line
check below before relying on any other.

## What would reopen this

Mostly resolved by the update above — a model does negotiate for this account, so the
account-wide entitlement question is closed. What is still open:

- **Background-job and interruption recovery**, watched live rather than only through the
  fake fixture in `tests/runtime.test.mjs` — `task --background`, kill the session
  uncleanly, recover from a fresh one, confirm the pid-staleness gap §10 already assumes.
- **Whether the other five current flagship models negotiate for this account** —
  `gpt-6-astra`, `gpt-6-sol`, `gpt-6-luna`, `gpt-5.6-sol`, `gpt-5.6-luna` are each a
  one-line check before anything in the harness relies on them:
  `codex exec --model <name> --sandbox read-only "reply pong"`.
