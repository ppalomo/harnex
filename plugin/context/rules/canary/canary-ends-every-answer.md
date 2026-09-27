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
canary word is a signal that this one instruction was not followed in that answer — not a
diagnosis that the rules are gone, but the cheapest sign that they may no longer be in
effect. Compacting or starting a new session is the usual remedy.

**Enforced by:** the canary check, `feedback/canary/canary.py` (pillar 5), run by the
plugin's Stop hook on the main session's answers only.
