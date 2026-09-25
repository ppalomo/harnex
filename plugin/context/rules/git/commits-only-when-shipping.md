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

**Enforced by:** the permission floor of pillar 4, which asks the person before a
command that writes to the history, even when nothing of the harness is running; and the
shell guard of the same pillar, which is what can tell the shipping phase from any
other.
