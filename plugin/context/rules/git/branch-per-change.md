---
id: branch-per-change
set: git
applies_to: always
enforced_by: none
---

# Do the work of one change on one branch of its own

A change is the unit that is proposed, built, verified and shipped, so it is also the
unit that is reviewed and, if it goes wrong, the unit that is abandoned. Work from two
changes on one branch cannot be shipped separately and cannot be abandoned separately.
Branch before the first edit, not after.
