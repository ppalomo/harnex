---
id: canary-ends-every-answer
set: canary
applies_to: always
enforced_by: hook
---

# End every answer with the canary word the project declares

The canary is a cheap, continuous test that the instructions are still in the context. A
model that has lost them keeps answering fluently and stops following them, and there is
no other signal that distinguishes that from a model that simply disagreed. A missing
canary word means the instructions are gone: compact, or start again.

**Enforced by:** the canary check of pillar 5, which reads the last answer at the end of
each turn and warns when the word is absent.
