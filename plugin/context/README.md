# Pillar 1 · Context & Memory

The eyes and the memory: everything the agent reads before it acts, and everything it is
expected to remember between tasks.

## What belongs here

- **Rule files**, one file per rule, grouped in sets under `rules/<set>/`. The body is the
  rule as an agent reads it, with its reason, in a few lines.
- **Instruction templates** rendered into a project by `setup`: the working instructions,
  the rules file, the project's answers.
- **Progress conventions**: how a change's state is written down so a fresh context can
  pick the work up.

## What does not

- **Enforcement.** A rule is *stated* here and, if it is also enforced, enforced in
  pillar 4 (before an action) or pillar 5 (after one). The rule file names its enforcer;
  the code that does the enforcing lives there, never here.
- **Technology names.** Only `../tools/profiles/` may name a language, framework or
  service. A rule that needs one is either a profile rule or is written without it.
- **Project facts.** No project name, domain vocabulary, private resource or credential.
  A component that needs a project fact reads it from the importing project's working
  instructions at task time, and says so.

## Filled by

`C1b` — the rule file format, the six sets (`git`, `code`, `sdd`, `safety`, `canary`,
`language`) and the renderer that turns a chosen list of sets into a project's rules file.
