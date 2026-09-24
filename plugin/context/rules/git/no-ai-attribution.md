---
id: no-ai-attribution
set: git
applies_to: always
enforced_by: none
---

# Never add an AI author or co-author line to a commit or a pull request

The history records who is accountable for a change, and that is the person who approved
it, whatever wrote the lines. A co-author line naming a model makes the record wrong in a
way no later commit can fix, and it is read by tools that count contributors. Leave the
authorship exactly as the person's own work would leave it.
