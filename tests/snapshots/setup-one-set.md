===== .claude/settings.json
{
  "permissions": {
    "deny": [
      "Read(~/.ssh/**)",
      "Read(~/.aws/**)",
      "Read(~/.config/gh/**)",
      "Read(**/id_rsa)",
      "Read(**/id_ed25519)",
      "Read(**/*.pem)"
    ],
    "ask": [
      "Read(.env)",
      "Read(.env.*)",
      "Read(*.env)",
      "Read(!.env.example)",
      "Read(!.env.sample)",
      "Bash(cat .env*)",
      "Bash(printenv *)",
      "Bash(git push *)",
      "Bash(git * push *)",
      "Bash(git remote add *)",
      "Bash(git remote set-url *)",
      "Bash(gh pr create *)",
      "Bash(gh pr merge *)",
      "Bash(gh release create *)",
      "Bash(gh repo create *)",
      "Bash(rm *)",
      "Bash(/bin/rm *)",
      "Bash(/usr/bin/rm *)",
      "Bash(rmdir *)",
      "Bash(git branch -d *)",
      "Bash(git branch -D *)",
      "Bash(git remote remove *)",
      "Bash(sudo *)",
      "Bash(dd *)",
      "Bash(mkfs *)",
      "Bash(bash -c *)",
      "Bash(sh -c *)",
      "Bash(git reset --hard *)",
      "Bash(git clean *)",
      "Bash(git rebase *)",
      "Bash(git filter-branch *)",
      "Bash(git filter-repo *)",
      "Bash(git checkout -- *)",
      "Bash(git restore *)",
      "Bash(git commit *)",
      "Bash(git * commit *)"
    ]
  }
}
===== .harnex/manifest.json
{
  "entries": {
    ".claude/settings.json": {
      "ask": [
        "Bash(/bin/rm *)",
        "Bash(/usr/bin/rm *)",
        "Bash(bash -c *)",
        "Bash(cat .env*)",
        "Bash(dd *)",
        "Bash(gh pr create *)",
        "Bash(gh pr merge *)",
        "Bash(gh release create *)",
        "Bash(gh repo create *)",
        "Bash(git * commit *)",
        "Bash(git * push *)",
        "Bash(git branch -D *)",
        "Bash(git branch -d *)",
        "Bash(git checkout -- *)",
        "Bash(git clean *)",
        "Bash(git commit *)",
        "Bash(git filter-branch *)",
        "Bash(git filter-repo *)",
        "Bash(git push *)",
        "Bash(git rebase *)",
        "Bash(git remote add *)",
        "Bash(git remote remove *)",
        "Bash(git remote set-url *)",
        "Bash(git reset --hard *)",
        "Bash(git restore *)",
        "Bash(mkfs *)",
        "Bash(printenv *)",
        "Bash(rm *)",
        "Bash(rmdir *)",
        "Bash(sh -c *)",
        "Bash(sudo *)",
        "Read(!.env.example)",
        "Read(!.env.sample)",
        "Read(*.env)",
        "Read(.env)",
        "Read(.env.*)"
      ],
      "deny": [
        "Read(**/*.pem)",
        "Read(**/id_ed25519)",
        "Read(**/id_rsa)",
        "Read(~/.aws/**)",
        "Read(~/.config/gh/**)",
        "Read(~/.ssh/**)"
      ]
    }
  },
  "format": 1,
  "paths": {
    ".harnex/rules.md": "32b59a22d62506f16a5fea9b97afe50a030ff5bd4f471517a289ab939968a057",
    ".harnex/state/.gitignore": "ff73664601b6084ee71a6c73e1e9e27f039c023bf6fce320496df7614f8b8365"
  }
}
===== .harnex/rules.md
# Rules

These are the rules every agent working in this project follows. They come from the
harness, from the rule sets this project chose. Nothing here is specific to this
project; anything that is belongs in the project's own working instructions.

Generated file — do not edit it by hand. It is rendered from the sets recorded in
`.harnex.yml`, and `update` will stop rather than overwrite a file that was edited
after it was written. To change which rules apply, change the sets. To change a rule,
change it in the harness.

Sets in this file: git.

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

**Enforced by:** the permission floor of pillar 4, which asks the person before a
command that writes to the history, even when nothing of the harness is running; and the
shell guard of the same pillar, which is what can tell the shipping phase from any
other.

### Write commit messages in the conventional form, in English, saying what changed and why

`type(scope): summary`, a blank line, then the reason. The type and the scope let a
reader scan a history they did not write; the reason is the part no diff can recover. The
summary says what the change does, not what you did to make it.

### Never add an AI author or co-author line to a commit or a pull request

The history records who is accountable for a change, and that is the person who approved
it, whatever wrote the lines. A co-author line naming a model makes the record wrong in a
way no later commit can fix, and it is read by tools that count contributors. Leave the
authorship exactly as the person's own work would leave it.
===== .harnex/state/.gitignore
# Runtime state the harness writes while it works: decision journal, apply run state.
# It ignores itself so that the project's own ignore file is never touched.
*
===== .harnex.yml
# The project's answers to the harness's questions.
#
# This file belongs to the project: the harness reads it and never rewrites it. Change a
# value here and run setup again to re-render what the harness owns. The shape is flat on
# purpose — scalars, and three lists — so that every hook and command can read it without
# resolving a dependency first.
project_name: scratch
profiles:
sets:
  - git
features:
canary: ""
decision_model: mock
check_command: make check
===== AGENTS.md
# scratch — working instructions

This file is the project's own brief, and it stays the project's: the harness created it
once and never rewrites it. Everything an agent needs that is true of this project and of
no other belongs here. Anything true of every project belongs in the harness instead.

## What this project is

Say what it does, who uses it, and what it deliberately is not. An agent that cannot answer
this from this file asks you rather than assuming.

## How work is done here

- The check that must pass before anything is called done: `make check`.
- Where things live, and what belongs in each place.
- The conventions a newcomer would get wrong.

## What is off limits

The paths, the data and the actions that are never touched without asking you first.

## Rules

Every agent working in this project follows the rules in `.harnex/rules.md`. Read that file
before you start, and follow it as if it were written here. It is generated from the rule
sets recorded in `.harnex.yml`: to change which rules apply, change the sets; to change a
rule, change it in the harness.
===== CLAUDE.md
@AGENTS.md
@.harnex/rules.md

# scratch

This file is the project's own, and the harness never rewrites it. It imports two things:
the project's brief and the rules the harness renders. Anything you want an agent to know
that is true of this project belongs in `AGENTS.md`, so that every tool reads the same
brief.
===== openspec/config.yaml
schema: spec-driven

# Shown to an agent when it creates a change's artifacts.
context: |
  Read AGENTS.md for what this project is, how work is done here and what is off limits,
  and .harnex/rules.md for the rules every agent follows. Neither is restated here.

rules:
  proposal:
    - Include a "Non-goals" section
  design:
    - For every guarantee the change makes, say whether it is instruction, prevention or
      detection, and what happens when the component providing it fails
  tasks:
    - Each task states how its completion is verified
