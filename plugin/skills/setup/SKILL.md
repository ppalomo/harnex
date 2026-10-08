---
name: setup
description: Bring a project to a harnessed state — ask what it needs, show the plan, and write only after an explicit yes. Use when setting a project up with the harness for the first time, or when re-running setup after changing the project's choices.
---

# Setting a project up

You ask the questions and show what would happen. Every filesystem step is the script's,
so that the whole sequence can be checked without a session. You never write a file the
script would write, and you never approve anything on the person's behalf.

The script is at `${CLAUDE_PLUGIN_ROOT}/scripts/setup.py`. Run it with `uv run`.

## 1. Check the working tree is clean, then learn what is on offer

Before asking anything, under either visibility, run in the project root:

```
git rev-parse --show-toplevel
git rev-parse --show-prefix
git status --porcelain=v1 -z --untracked-files=all -- .
```

Setup runs only inside a git repository with nothing to commit apart from the harness's
own paths; the plan refuses anything else as a conflict, so check it first rather than
asking questions for a plan that will refuse them. The repository is whatever
`git rev-parse` finds, so a worktree and a project in a subdirectory of a repository both
work; the trailing `-- .` keeps the status to the project's own subtree. The status
lists its paths relative to the repository's root, not the project's: strip the prefix
`git rev-parse --show-prefix` printed (empty at the top of a repository, `sub/dir/` in a
subdirectory) from the front of each path before comparing it with the harness's own
paths below, or a project in a subdirectory would see its own `AGENTS.md` as
`sub/dir/AGENTS.md` and stop on it. `-z` is what makes that stripping safe: without it,
git quotes a path holding a space or a non-ASCII character (`"sub/dir/my file"`), and the
prefix no longer sits at the front of it. With `-z` each entry is the two status letters,
a space and the path exactly as it is, ended by a NUL byte rather than a newline; a
rename or copy (`R` or `C`) is followed by one more NUL-ended field, the original path,
which is checked the same way. If `git rev-parse` fails, there is no repository: stop and tell the person to run `git init`
and commit first. The harness's own paths do not count — `AGENTS.md`, `CLAUDE.md`,
`.harnex.yml`, anything under `.harnex/`, `openspec/config.yaml`,
`.claude/settings.json`, `.mcp.json`, `CLAUDE.local.md` and
`.claude/settings.local.json` — so a rerun before the person commits what setup wrote, or
after an interrupted run, goes ahead. If the command lists any other path, stop, show
those paths exactly as it listed them, and say to commit or stash them first. An
untracked `.env` is the common case: the person can exclude it themselves (for instance
by adding it to `.git/info/exclude`) and run setup again; you do not do it for them here.
Setup never runs `git init`, commits or stashes to get past this. The script's own
conflict is what enforces it; this check only spares the person the questions.

Once the tree is clean:

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" choices
```

It prints the rule sets, profiles and features the harness holds, the decision backends,
the two visibilities, the builder's two tools, and the canary word setup proposes. Offer
nothing that is not in that output: when a list is empty, there is nothing to ask about,
and the answer is an empty list.

Then look for the project's already-recorded answers: `.harnex/config.yml` if the project
is local visibility, otherwise `.harnex.yml`. If either is there, those are the project's
answers — take them as given and do not ask again, visibility included. Setup never
rewrites either file.

## 2. Ask, in this order, only what you cannot derive

The questions below are more than a question tool takes in one call: `AskUserQuestion`
accepts at most 4 questions per call, each with 2 to 4 options, and a call that exceeds
either limit fails with "Invalid tool parameters". Ask in batches of at most 4, keeping
the order, and fold a question into its neighbour only when the answers are independent
(the name and the visibility, for instance). A list longer than 4 — the rule sets — is a
multi-select question that proposes the whole list in its description, or a plain
question in the conversation, never more than 4 options.

1. **Project name** — propose the directory's name.
2. **Visibility** — `shared` (the default: the project's team, via source control) or
   `local` (the person running it alone — nothing setup writes ever reaches this
   project's own history). Propose `shared`. If the person is unsure, ask what they are
   setting the harness up for: a team decision, or their own use of a repository that
   is not theirs to add tooling to.
3. **Rule sets** — list the sets on offer with one line each on what the set is for, and
   propose all of them. A project can drop any of them later by editing its answers file.
4. **Profiles**, then **features** — ask only if the harness holds any.
5. **Canary word** — only if the `canary` set was chosen. Propose the word from `choices`
   and say what it is for: every answer ends with it, and a missing word is the cheapest
   sign that the rules may have dropped out of the context.
6. **Decision backend** — `mock` asks the person on every decision, `jev` calls the model
   and needs a key in the environment. Propose `mock`.
7. **Check command** — the command that must pass before anything is called done. You
   cannot derive it and there is no default: ask, and if the person does not know, find
   the project's own check and propose it for confirmation.
8. **Tools** (`local` visibility only) — which of the builder's two bindings, `claude`
   and `codex`, the person wants active for this project. Propose both. If `codex` is
   among them, say so before recording it: under `local` visibility the apply loop
   (`/harnex:apply`) hands Codex the rules — its prompt starts with an instruction to
   read `.harnex/rules.md` and follow it — but Codex used outside apply will not have
   them, since `AGENTS.md` is never written under `local` visibility.
9. **Store location** (`local` visibility only) — asked only when no store id is
   recorded and no store is already registered under the id setup would use; step 3
   says how to choose that id and look it up, so work that out before asking. Where the
   OpenSpec store for this project's changes should live, as a folder path outside the
   project's own directory: the script refuses a path inside it, since registering there
   would create an `openspec/` directory in the project. Ask it as a plain question;
   propose no path of your own, and never adopt the one the `openspec` tool suggests
   (`~/openspec/<id>`) unless the person gives it as their answer.

## 3. Local visibility: resolve the store before planning, register nothing yet

Skip this section under `shared` visibility. Nothing here changes anything — the one
command it runs only lists what is registered — and the registration is a line of the
plan, run only after the person's yes (step 6).

If the project's already-recorded `.harnex/config.yml` holds a `store_id`, reuse it —
put it in `store_id`, leave `store_path` empty, and do not ask where the store lives or
register a second one. Otherwise, choose `<id>` the way Claude Code's own auto-memory
keys a project's memory directory: from the git repository, so every worktree and subdirectory of the same repository shares one
store. Then, before asking where it lives, see whether a store is already registered
under that id:

```
openspec store list --json
```

It prints `{"stores": [{"id": …, "root": …}, …]}`. If an entry's `id` is the id you
chose — a run interrupted after registering the store and before writing leaves exactly
that behind — reuse it: put the id in `store_id`, leave `store_path` empty, set
`store_registered` to `true`, and do not ask where the store lives or register it again.
Only when no entry has that id, put it in `store_id`, and the person's answer to the
store location question in `store_path`. A `store_id` already recorded needs neither
`store_path` nor `store_registered`.

## 4. Show the plan before anything is written

Write the answers to a file outside the project — the session's temporary directory —
shaped like this, then plan:

```json
{
  "project_name": "…",
  "profiles": [], "sets": ["…"], "features": [],
  "canary": "…", "decision_model": "mock", "check_command": "…",
  "approvals": {
    "pointer_agents": false, "pointer_claude": false, "mcp_playwright": false,
    "global_instructions": false, "adopt": []
  },
  "visibility": "shared",
  "tools": [],
  "store_id": "", "store_path": "", "store_registered": false
}
```

Under `local` visibility, `visibility` is `"local"`, `tools` holds the chosen bindings,
and `store_id`, `store_path` and `store_registered` come from step 3. `store_registered`
is `true` only when the store list held the id and no `store_id` is recorded; the script
refuses it alongside a `store_path`, since a store already registered is not registered
again. Under `shared` visibility, leave `visibility` as `"shared"`,
`tools`/`store_id`/`store_path` empty and `store_registered` `false` — the script refuses
any of them without `local` visibility, the same way it refuses a canary word without the
`canary` set, and refuses a first `local` setup with no `store_path` and no
`store_registered`.

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" plan --answers <file> --project <project root>
```

Show the person the plan as the script printed it, every line of it. Do not summarise the
conflicts away and do not reorder the lines. It is the one plan for the whole run: the
exclude entries — `.env` among them when `jev` is chosen — the "register store" step and
the global setting's line all appear in it, and the person's single yes to it covers
them. There is no second plan.

## 5. Approvals are the person's, one by one

The approvals in the answers document start `false` and an empty list. Set one only after
the person has said yes to that exact thing, in this turn:

- **`pointer_agents` / `pointer_claude`** (`shared` visibility only) — the plan's notices
  show the exact line and where it goes. Ask for each file separately. If the person
  declines, say what does not work — the notice says it — and carry on: the rest of
  setup is unaffected, and the notice returns on every later run until the line is
  there.
- **`mcp_playwright`** (`shared` visibility, a UI profile) — the plan's notice shows the
  exact entry it would add to `.mcp.json`.
- **`global_instructions`** (`local` visibility only) — the plan's notice, when it
  appears, explains that without this one-time, machine-wide setting, this project's own
  `CLAUDE.local.md` will stop Claude Code from reading its `AGENTS.md`. It changes the
  person's own `~/.claude/settings.json`, not anything of this project's — say so, so
  the person knows it is not scoped to the project they are setting up.
- **`adopt`** — only for a path the plan reports as a conflict, and only after you have
  shown the difference between what is there and what the harness would write. Adoption
  replaces the file.

A silence, a "sounds good" about something else, or your own judgement that it is
obviously fine are not a yes. If you are unsure whether the person agreed, ask again.

## 6. Run the plan's own commands, then write

A conflict left standing means nothing is written, by design: say which conflicts remain
and what resolves each — a tree that is not clean among them, which the person resolves,
never you. Otherwise, once the person has approved the plan, and only then, run what the
plan names but the script never runs: if the plan has the "register store" step, run
`openspec store setup <id> --path <path>` with exactly the id and path that step shows.
If it fails, stop and say why: nothing has been written yet.

Then write, with the same answers file — do not plan again and do not ask again:

```
uv run "${CLAUDE_PLUGIN_ROOT}/scripts/setup.py" write --answers <file> --project <project root>
```

The script surveys again before it writes, so an approval given against a plan that has
since gone stale writes nothing and says why. Report the paths it wrote, and every side
effect beyond them, by name:

- The store registration — its id and its path — if you ran it; if the plan showed
  "reuse store `<id>`" instead, say the store was reused, not registered.
- `.env` added to `.git/info/exclude`, if `jev` was chosen and the plan's exclude step
  carried it.
- The global setting, if it was approved and written: the file
  (`~/.claude/settings.json`), the key
  `pluginConfigs."agents-md@builtin".options.instructionFiles` and the value
  `"claude-md-and-agents-md"`.

Under `shared` visibility, tell the person what to do next: read `AGENTS.md` and fill in
what only they know, since the harness deliberately knows nothing about their project.

Under `local` visibility there is no `AGENTS.md` to point at — say instead that
`CLAUDE.local.md` is theirs to read or edit freely, and:

- If a UI profile is chosen and the plan's notice named a Playwright entry, offer to run
  it now, after the person's yes — this script never runs it for you:
  ```
  claude mcp add playwright --scope local -- npx @playwright/mcp@latest
  ```
- If the plan still shows the `global_instructions` notice (the person has not yet
  approved it, this run or an earlier one), repeat it rather than letting it pass
  silently.

## What this skill never does

- Write, edit or create any of the project's files itself. The script writes; you ask.
- Set an approval the person did not give, or adopt a file to get past a conflict.
- Run `claude mcp add` without the person's yes, or `openspec store setup` before the
  person's yes to the plan that shows it.
- Ask the questions before the working tree is known to be clean.
- Run `git init`, commit or stash — not to get past the clean-tree check, not ever.
- Choose where the store lives: the path is the person's answer, never a default they
  did not see.
- Show a second plan to approve what the first one already showed.
- Re-render `.harnex.yml`, `.harnex/config.yml`, `AGENTS.md`, `CLAUDE.md`,
  `CLAUDE.local.md` or the OpenSpec config. They belong to the project (or, under local
  visibility, to the person alone): setup creates them when they are absent and never
  rewrites them.
