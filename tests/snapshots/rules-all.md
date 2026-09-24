# Rules

These are the rules every agent working in this project follows. They come from the
harness, from the rule sets this project chose. Nothing here is specific to this
project; anything that is belongs in the project's own working instructions.

Generated file — do not edit it by hand. It is rendered from the sets recorded in
`.harnex.yml`, and `update` will stop rather than overwrite a file that was edited
after it was written. To change which rules apply, change the sets. To change a rule,
change it in the harness.

Sets in this file: canary, code, git, language, safety, sdd.

## canary

### End every answer with the canary word the project declares

The canary is a cheap, continuous test that the instructions are still in the context. A
model that has lost them keeps answering fluently and stops following them, and there is
no other signal that distinguishes that from a model that simply disagreed. A missing
canary word means the instructions are gone: compact, or start again.

**Enforced by:** the canary check of pillar 5, which reads the last answer at the end of
each turn and warns when the word is absent.

## code

### Run the project's check command before saying a task is done

"Done" is a claim about the state of the repository, and the only evidence for it is the
check passing on the tree as it stands. A task reported done on a tree that was never
checked moves the failure to whoever picks the work up next, with the context gone.
Report the command you ran and what it said.

**Enforced by:** the check command of pillar 5, run by the build loop before a task is
accepted.

### Change only what the task asks for, and say what you saw but did not touch

A task is also a promise about what will not move. An improvement made in passing is
unreviewed, untested against its own intent, and hides inside a diff the reviewer is
reading for something else. When you find something worth fixing, name it in the report
and leave it; it becomes the next task or the next change.

**Enforced by:** the scope question of pillar 3, asked of the decision model with the
task's text and the paths that changed.

### Put a test where the thing it tests lives, following the layout already in the project

A test found next to its subject is read when the subject is read, and deleted when the
subject is deleted. Where the project already has a convention for that, it wins; the
rule is to follow the layout in front of you, not to import one.

## git

### Do the work of one change on one branch of its own

A change is the unit that is proposed, built, verified and shipped, so it is also the
unit that is reviewed and, if it goes wrong, the unit that is abandoned. Work from two
changes on one branch cannot be shipped separately and cannot be abandoned separately.
Branch before the first edit, not after.

### Commit only in the shipping phase, after the person has said yes

Work in progress is worth nothing to the history and everything to the working tree: a
commit made mid-task freezes a state nobody chose to keep, and a commit made without
being asked takes a decision that belongs to the person. Build, check, report — then ask.

**Enforced by:** the shell guard of pillar 4, which asks the person before any command
that writes to the history.

### Write commit messages in the conventional form, in English, saying what changed and why

`type(scope): summary`, a blank line, then the reason. The type and the scope let a
reader scan a history they did not write; the reason is the part no diff can recover. The
summary says what the change does, not what you did to make it.

### Never add an AI author or co-author line to a commit or a pull request

The history records who is accountable for a change, and that is the person who approved
it, whatever wrote the lines. A co-author line naming a model makes the record wrong in a
way no later commit can fix, and it is read by tools that count contributors. Leave the
authorship exactly as the person's own work would leave it.

## language

### Write everything that is committed in English

Code, comments, documentation, rules, commit messages, specifications and command names
are read by people and by agents who do not share a first language, and a repository that
mixes two languages forces every reader to hold both. Speak to the person in whatever
language they use; write to the repository in English.

## safety

### Never print, commit or send a credential, and ask before reading one

Reading a credential from the environment to use it is ordinary work. Putting one into a
message, a file, a log line or a commit is not, and it cannot be undone: once a value has
been written down somewhere it did not belong, it has to be replaced rather than deleted.
When a task seems to need the value itself, that is the moment to ask.

**Enforced by:** the shell guard of pillar 4, which asks before any command that would
read a store of credentials or echo one.

### Ask the person before deleting anything you were not asked to delete

Deleting a file, a branch, a directory or a remote is the one action whose cost is
unbounded and whose benefit is usually tidiness. Inside the paths a task declares,
deletion is part of the work; outside them it is a surprise, and a surprise the person
may only notice much later.

**Enforced by:** the shell guard of pillar 4, which asks before any command that removes
something.

### Ask the person before running a command whose effect cannot be undone

Reversibility is the whole difference between a mistake and an incident. A command that
rewrites history, resets a tree, overwrites a store or drops state leaves nothing to fall
back on, so the person decides, not the agent — and they decide with the exact command in
front of them, not a description of it.

**Enforced by:** the shell guard of pillar 4, which classifies every command before it
runs and asks whenever it is not certain the command is safe.

### Ask the person before sending anything to a remote

Publishing is the point at which work stops being local and becomes something other
people, and other systems, act on. It can start a pipeline, notify a team or expose a
draft, and none of that can be taken back by deleting the branch afterwards.

**Enforced by:** the shell guard of pillar 4, which asks before any command that writes
to a remote.

## sdd

### Take the brief from the change's artifacts on disk, re-read, not from the conversation

The artifacts are what was agreed and what the next agent will read; the conversation is
what one context happened to remember. Re-read them at the start of a task, even when you
believe you wrote them, because a compaction or a fresh context is exactly when the
difference bites.

### Never mark a task done from inside the work that was meant to do it

A task list that is ticked by whoever did the work records an intention, not an outcome.
Ticking is the orchestrator's act, taken after the check has passed and the evidence has
been read. Report what you did and what the check said, and leave the list alone.

### Treat the proposal as the boundary of the change, and widen it by revising it, never in passing

The proposal is what the person approved. Work that falls outside it has not been
approved, however obviously good it is. When the boundary turns out to be wrong, stop and
revise the proposal — which costs a paragraph — rather than quietly delivering something
else.
