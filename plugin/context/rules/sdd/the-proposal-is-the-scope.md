---
id: the-proposal-is-the-scope
set: sdd
applies_to: always
enforced_by: check
---

# Treat the proposal as the boundary of the change, and widen it by revising it, never in passing

The proposal is what the person approved. Work that falls outside it has not been
approved, however obviously good it is. When the boundary turns out to be wrong, stop and
revise the proposal — which costs a paragraph — rather than quietly delivering something
else.

**Enforced by:** the scope check, `feedback/scope_check.py` (pillar 5), run by `propose`
once every required artifact exists. It reports a path written outside the change's own
directory; it does not stop the write or undo it.
