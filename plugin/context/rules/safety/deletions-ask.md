---
id: deletions-ask
set: safety
applies_to: always
enforced_by: guard
---

# Ask the person before deleting anything you were not asked to delete

Deleting a file, a branch, a directory or a remote is the one action whose cost is
unbounded and whose benefit is usually tidiness. Inside the paths a task declares,
deletion is part of the work; outside them it is a surprise, and a surprise the person
may only notice much later.

**Enforced by:** the shell guard of pillar 4, which asks before any command that removes
something.
