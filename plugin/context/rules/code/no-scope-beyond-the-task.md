---
id: no-scope-beyond-the-task
set: code
applies_to: always
enforced_by: decision
---

# Change only what the task asks for, and say what you saw but did not touch

A task is also a promise about what will not move. An improvement made in passing is
unreviewed, untested against its own intent, and hides inside a diff the reviewer is
reading for something else. When you find something worth fixing, name it in the report
and leave it; it becomes the next task or the next change.

**Enforced by:** the scope question of pillar 3, asked of the decision model with the
task's text and the paths that changed.
