# Pillar 4 · Control & Guardrails

The immune system: what happens *before* an action runs, and what always stops for a
human. Two layers, because one hook cannot promise what it cannot deliver.

## What belongs here

- **The permission floor**, `floor.json`: the harness's deny and ask patterns written in
  the host's own permission syntax, each entry naming the rule it comes from. Setup merges
  these entries, and only these, into the project's permission file. The floor is what
  still holds when nothing of the harness is running — and the answer to what the host's
  syntax cannot express is in the same file, as `guard_only`, with the reason.
- **The shell guard** under `guard/`: the pattern lists, the script that classifies a
  command before it runs, and the risk question it asks when the deterministic lists do
  not decide.
- **The approvals**: the actions that always stop for the person, with the reason each is
  on the list.

## What does not

- **The statement of a safety rule.** It is stated once in pillar 1; this directory is
  where it is enforced, and the rule file names this enforcement.
- **Checks that run after the fact.** A verification that reads a result belongs to
  pillar 5. The line is the moment: control decides before, feedback judges after.
- **Routing decisions.** Which tool runs a phase is pillar 3.

## What each layer promises, and what it does not

- **The guard never allows on its own error.** An unreachable backend, a timeout, a
  missing key, an unparseable command, any exception inside the script: the answer is
  *ask*, never *allow*. That is guaranteed by the script and tested.
- **The guard cannot answer for its own failures.** If the interpreter is missing, the
  script does not start, it hangs past the hook's timeout or it prints malformed output,
  the host treats the hook as a non-blocking error and carries on with its normal
  permission flow. There is no fail-closed setting. This is why the floor exists.
- **The floor holds without us.** Its entries live in the project's permission file, so
  the host applies them whether or not any harness component runs. The host resolves deny,
  then ask, then allow, and an allow cannot carve an exception out of either.
- **The floor is coarser than the guard.** It matches commands as they are written. It
  does see a subcommand inside a pipeline, a subshell or a command substitution; it does
  not see a command reached through a wrapper, an environment runner or an absolute path
  it does not name, and it cannot tell a deletion inside the task's declared paths from
  one outside them. Those gaps are recorded, not assumed away.
- **One thing defeats both**: a permission mode that bypasses permissions altogether. No
  harness can defend against it, and setup says so rather than claiming otherwise.

## Filled by

`C1c` — the permission floor and its merge into a project. Then `C4` — the guard script,
its pattern lists, the hook that runs it before a shell command, and the risk question;
`C4` also regenerates this floor from the same patterns, so the two layers cannot drift.
