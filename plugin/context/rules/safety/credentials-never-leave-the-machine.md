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

**Enforced by:** the permission floor of pillar 4, which refuses reads of the credential
stores outside the project and asks before a read of the project's own — prevention for
the first, a question for the second, both holding with nothing of the harness running;
and the shell guard of the same pillar, which is what can see a value being printed,
committed or sent, since no pattern can.
