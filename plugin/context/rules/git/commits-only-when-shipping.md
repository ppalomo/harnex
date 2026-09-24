---
id: commits-only-when-shipping
set: git
applies_to: always
enforced_by: guard
---

# Commit only in the shipping phase, after the person has said yes

Work in progress is worth nothing to the history and everything to the working tree: a
commit made mid-task freezes a state nobody chose to keep, and a commit made without
being asked takes a decision that belongs to the person. Build, check, report — then ask.

**Enforced by:** the shell guard of pillar 4, which asks the person before any command
that writes to the history.
