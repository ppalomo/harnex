---
id: destructive-commands-ask
set: safety
applies_to: always
enforced_by: guard
---

# Ask the person before running a command whose effect cannot be undone

Reversibility is the whole difference between a mistake and an incident. A command that
rewrites history, resets a tree, overwrites a store or drops state leaves nothing to fall
back on, so the person decides, not the agent — and they decide with the exact command in
front of them, not a description of it.

**Enforced by:** the shell guard of pillar 4, which classifies every command before it
runs and asks whenever it is not certain the command is safe.
