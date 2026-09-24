---
id: pushes-ask
set: safety
applies_to: always
enforced_by: guard
---

# Ask the person before sending anything to a remote

Publishing is the point at which work stops being local and becomes something other
people, and other systems, act on. It can start a pipeline, notify a team or expose a
draft, and none of that can be taken back by deleting the branch afterwards.

**Enforced by:** the shell guard of pillar 4, which asks before any command that writes
to a remote.
