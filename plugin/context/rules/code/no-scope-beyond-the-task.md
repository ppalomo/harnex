---
id: no-scope-beyond-the-task
set: code
applies_to: always
enforced_by: check
---

# Change only what the task asks for, and say what you saw but did not touch

A task is also a promise about what will not move. An improvement made in passing is
unreviewed, untested against its own intent, and hides inside a diff the reviewer is
reading for something else. When you find something worth fixing, name it in the report
and leave it; it becomes the next task or the next change.

**Enforced by:** `plugin/feedback/task_scope_check.py` (pillar 5), run by `apply`'s loop
after every builder writes — `check_declared` against a task's own declared paths, or, for
a task that declares none, the `task.scope` question put to the decision model with the
task's text and the changed paths. `check_protected` runs unconditionally alongside
either one: no task's own scope, declared or judged, can widen past it.
