---
id: check-before-done
set: code
applies_to: always
enforced_by: check
---

# Run the project's check command before saying a task is done

"Done" is a claim about the state of the repository, and the only evidence for it is the
check passing on the tree as it stands. A task reported done on a tree that was never
checked moves the failure to whoever picks the work up next, with the context gone.
Report the command you ran and what it said.

**Enforced by:** the check command of pillar 5, run by the build loop before a task is
accepted.
