---
id: conventional-commits
set: git
applies_to: always
enforced_by: none
---

# Write commit messages in the conventional form, in English, saying what changed and why

`type(scope): summary`, a blank line, then the reason. The type and the scope let a
reader scan a history they did not write; the reason is the part no diff can recover. The
summary says what the change does, not what you did to make it.
