---
id: builders-never-tick-tasks
set: sdd
applies_to: always
enforced_by: check
---

# Never mark a task done from inside the work that was meant to do it

A task list that is ticked by whoever did the work records an intention, not an outcome.
Ticking is the orchestrator's act, taken after the check has passed and the evidence has
been read. Report what you did and what the check said, and leave the list alone.

**Enforced by:** `plugin/scripts/apply_loop.py` (pillar 3's script, the enforcement pillar
5's `task_scope_check.py` names its own protected-path check against) — `tasks.md` sits
under `openspec/`, so a builder's own attempt to tick it is caught the same way any other
write to a protected path is, and ticking itself happens only in the loop's own `tick`
step, which no builder binding ever calls.
