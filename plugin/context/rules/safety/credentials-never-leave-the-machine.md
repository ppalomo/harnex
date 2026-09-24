---
id: credentials-never-leave-the-machine
set: safety
applies_to: always
enforced_by: guard
---

# Never print, commit or send a credential, and ask before reading one

Reading a credential from the environment to use it is ordinary work. Putting one into a
message, a file, a log line or a commit is not, and it cannot be undone: once a value has
been written down somewhere it did not belong, it has to be replaced rather than deleted.
When a task seems to need the value itself, that is the moment to ask.

**Enforced by:** the shell guard of pillar 4, which asks before any command that would
read a store of credentials or echo one.
