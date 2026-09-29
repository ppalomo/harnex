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

**Enforced by:** the permission floor of pillar 4, which asks before the common
spellings of a removal even when nothing of the harness is running; the shell guard of
the same pillar (`control/guard/guard.py`), which asks before an ordinary deletion and
denies the builder role specifically a deletion inside `openspec/` or `.harnex/`,
regardless of any task; and, for whether a deletion sits inside the paths a task itself
declares, pillar 5's own check after the fact, since that is task-specific state the
guard is never handed before a command runs.
