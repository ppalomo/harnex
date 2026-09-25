# The permission floor in the host's own syntax

**Date:** 2026-09-25 · **Phase:** C1c · **Status:** answered, and two claims in the plan
corrected · **Verified against:** Claude Code 2.1.269
(`code.claude.com/docs/en/permissions`)

## The question

`docs/PLAN.md` §13 asked: *whether Claude Code's permission syntax can express every deny
and ask pattern closely enough for the floor, and which patterns must stay guard-only.*

It matters because the floor is the only thing left when the guard's hook itself fails
(§9). A floor that quietly fails to express a rule would be a guarantee with no mechanism —
exactly what the plan's guarantee-by-kind discipline exists to prevent.

## What the host's documentation says

1. **Rule order.** "Rules are evaluated in order: deny, then ask, then allow. The first
   match in that order determines the outcome, and rule specificity doesn't change the
   order." And: "An allow rule can't carve an exception out of a deny rule. The same
   precedence applies between ask and allow: a matching ask rule prompts even when a more
   specific allow rule also matches the same call."
2. **Compound commands are seen by deny and ask.** "Deny and ask rules apply when any
   subcommand matches them, including a command nested inside a subshell, a command
   substitution, or a control-flow body such as a `for` loop." A deny or ask rule also
   "matches past any leading assignment".
3. **What escapes a prefix rule.** The documentation's own table: `Bash(rm *)` does not
   match `/bin/rm -rf build/` or `bash -c 'rm -rf build/'`; `Bash(git push *)` does not
   match `git -C . push origin main` or `git -c push.default=current push origin main`.
   Environment runners are not stripped ("a rule like `Bash(devbox run *)` matches whatever
   comes after `run`"), `find` with `-exec` or `-delete` is not covered by a `Bash(find *)`
   rule, and exec wrappers such as `watch`, `setsid`, `ionice` and `flock` cannot be
   matched by a prefix rule.
4. **A bare tool name in `deny` removes the tool from the model's context entirely.**
5. **Paths** use gitignore syntax with four anchors: `//absolute`, `~/home`,
   `/relative-to-the-settings-source`, `path` or `./path` relative to the current
   directory. For deny and ask, a bare filename matches at any depth, so `Read(.env)` and
   `Read(**/.env)` are the same rule. A `!` pattern carves out of the `path` rules listed
   **before** it, within one settings file.
6. **One mode defeats everything**: a permission mode that bypasses permissions.
   Sandboxing does not: "Content-scoped ask rules like `Bash(git push *)` still force a
   prompt."

## The answer

**The syntax is enough for every rule the harness states**, with one wildcard trick and
two extra spellings, and the residue is small, known and recorded.

- Each floor entry names the rule it comes from, so a check walks from every rule with
  `enforced_by: guard` to its coverage and back. Five rules qualify today: the four in
  `safety` and `commits-only-when-shipping`.
- **A rule that says *ask* becomes an ask entry.** `deny` is used only where reading could
  never be part of a project's work — the credential stores outside the project. The floor
  never states something stronger than the rule it comes from, and never writes a bare tool
  name.
- Git's `-C` and `-c` forms are covered by a second entry with the wildcard before the
  subcommand (`Bash(git * push *)` beside `Bash(git push *)`), which is allowed for ask and
  deny; the host warns only about an **allow** rule shaped that way.
- `guard_only` in `plugin/control/floor.json` records what no pattern can reach, each with
  its reason: a program named by an absolute path the floor does not list, an environment
  runner, an exec wrapper, a search command that deletes through its own options, printing
  a value the process already holds, and — the one that is not about syntax at all —
  telling a deletion inside the task's declared paths from one outside them.

## Two claims in the plan were wrong

- **§6 called a project `allow` entry that covers a floor entry a conflict that stops the
  run; §9 said setup warns about it.** The host's rule order settles it: such an entry
  cannot undercut the floor, because deny and ask are resolved first and no allow carves an
  exception. It is reported as a notice — the person should know their rule is inert for
  those commands — and the run continues. §6 now says what §9 said.
- **§9 said the floor does "no parsing of compound commands".** That is true of `allow`
  rules only. Deny and ask rules see every subcommand, including inside a subshell or a
  command substitution. The floor is coarser than the guard for other reasons: wrappers,
  absolute paths, and the fact that it cannot know the task.

## What C4 inherits

`guard_only` is the list of what only the guard can cover, and the floor's entries are the
list it must reproduce when it regenerates them from its own pattern lists. The comparison
is entry by entry, and `tests/test_floor.py` already fails when an entry goes missing.
