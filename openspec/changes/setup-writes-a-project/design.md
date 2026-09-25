## Context

See `proposal.md` — Why. What shapes the approach here is what already exists and what the
plan has already settled:

- The renderer of `C1b` is importable and pure: `available_sets()` and `render()` take a set
  list and profiles and return bytes that depend on nothing else. Setup does not re-implement
  any of it.
- Harness scripts depend on the standard library only (decision 15), so nothing here parses
  YAML with a library. `C1b` learned that four flat fields are parsed by fifteen lines and
  that refusing what they do not match *is* the schema check; `.harnex.yml` is written and
  read the same way.
- A generated file must be a pure function of the project's choices (decision 16), or
  ownership by hash reports an edit on every release.
- A Claude Code command is a prompt, not a process: it cannot be unit-tested and it has no
  terminal. Everything that must be tested has to live outside it.
- The host reads a project's permissions from one file and a plugin cannot ship permission
  rules, so the floor has to be merged into a file the project also owns (§6, §9).

## Goals / Non-Goals

**Goals:**

- One deterministic program that can survey, plan and write, driven entirely by data, so
  every scenario in the specs is a test that needs no session and no credential.
- A record of what the harness generated that `C6`'s `update` can obey without being written
  yet, and that `C4`'s regenerated floor can be compared against entry by entry.
- Adoption as the same code path as a fresh setup, not a second one.

**Non-Goals:**

- Preserving the exact byte formatting of a project's permission file. The merge is by entry
  on parsed data; a file whose formatting differs from the harness's is reformatted the one
  time the floor lands in it, and the plan says so before it happens.
- A general YAML reader. `.harnex.yml` is a fixed, flat shape, and anything outside it is
  refused with the line named.
- Any interactive prompt inside the script. Approval is an input, not a question.

## Decisions

### A skill asks, a script does the work

`/harnex:setup` is one skill, `plugin/skills/setup/`: the questions, in what order, what to
show, what counts as a yes. Every filesystem step is `plugin/scripts/setup.py`. Both are
pillar 2.

The plan said a thin command in front of the skill. Installing it showed why not: the host
lists commands and skills in one inventory, so a command plus a skill is **two components
for one capability** — `Skills (2) setup, harnex-setup`, two always-on descriptions — and
the skill, named `setup`, is already invoked as `/harnex:setup`. The command bought the
name it already had, so it is gone: one component, ~81 always-on tokens, and the host's own
advice for a new plugin.

The split between the two is what makes the specs testable: the script has three verbs,
`choices`, `plan` and `write`, and the last two take one answers document (`--answers <file|->`) and return a machine-readable
result plus the human lines the session prints. `write` re-runs the survey itself and refuses
if any conflict stands, so an approval given against a stale plan cannot write anything.

Alternatives: everything in the skill's prompt — nothing testable, and the plan's own
sequence would be advice; one script that prompts on a terminal — Claude Code gives it none,
and the questions belong to the session that can explain them. `choices` exists because the
skill must offer only what the harness holds, and a prompt cannot discover that on its own
without reading the tree.

### What setup writes, and who owns each path

| Path | Owner | Written when | Recorded |
|---|---|---|---|
| `AGENTS.md` | project | absent → created from template; present → pointer line inserted only on an explicit yes | no |
| `CLAUDE.md` | project | same, with the two `@` imports | no |
| `.harnex.yml` | project | absent → created from the answers; present → read, never written | no |
| `openspec/config.yaml` | project | absent → created from template; present → left alone | no |
| `.harnex/rules.md` | harness | rendered from the chosen sets | path + hash |
| `.harnex/state/.gitignore` | harness | created, containing the pattern that ignores its own directory | path + hash |
| `.harnex/manifest.json` | harness | last, after every other write | itself, by being the record |
| `.claude/settings.json` | shared, by entry | the floor's entries merged into `permissions.deny` and `permissions.ask` | the entries written, verbatim |

Nothing else is touched. The project's `.gitignore` is never read or written: the state
directory ignores itself.

### The record is data about paths and entries, with no stamp of its own

`.harnex/manifest.json` holds `{"format": 1, "paths": {<path>: <sha256 of the bytes
written>}, "entries": {"<file>": {"deny": [...], "ask": [...]}}}`, keys sorted, one trailing
newline. No timestamp, no harness version, no project name: a stamp of any kind would make
the record differ between two runs of the same choice and turn every release into a diff —
which is exactly what decision 16 forbids for generated files, and the record is the file
that ownership rests on. `format` is the shape's own number and changes only when the shape
does.

Entries are recorded verbatim rather than hashed, because a merge has to find them again in a
file the project also edits.

### `.harnex.yml` is a fixed flat shape, and the reader is the schema

Written and read by the same twenty lines: `key: value` for scalars, `key:` followed by
`  - item` lines for the three lists (`profiles`, `sets`, `features`), `#` comments and blank
lines ignored, quoted scalars accepted, everything else refused with the file and line named.
The keys are the seven the plan fixes. Taking a YAML library to read seven keys would put a
dependency resolution in front of every hook and command that reads the file later —
`C1d`'s hook has three seconds to live.

### The floor is a list of entries, each naming the rule it comes from

`plugin/control/floor.json` (pillar 4): `{"format": 1, "entries": [{"rule": "<rule id>",
"list": "deny"|"ask", "pattern": "<host syntax>"}], "guard_only": [{"rule": "<rule id>",
"why": "..."}]}`.

Naming the rule in each entry is what lets a check walk from every rule with
`enforced_by: guard` to its coverage and back, the same walk `C1d` adds for hooks, and what
lets `C4` regenerate the entries from the guard's pattern lists and compare them one by one.
`guard_only` is where this change answers the plan's open question: a pattern the host's
syntax cannot express is recorded with its reason rather than quietly missing, and the check
accepts a rule covered either way. The exact patterns are verified against the host's
documented permission syntax during implementation and the version recorded in
`docs/smoke.md` and in `docs/decisions/`.

### The permission merge compares parsed data and writes only on a difference

Parse the existing file; add the floor's entries to `permissions.deny` and `permissions.ask`
if absent; if the result equals what was parsed, write nothing at all. That is what makes a
second run byte-identical whatever the project's formatting, and it costs one comparison.
A file that cannot be parsed as JSON is a conflict named as such, not a file to rewrite.

### What the host's documentation settled, and what it changed here

The plan says two different things about a project `allow` entry that covers what the floor
asks about: §6 calls it a conflict that stops the run, §9 says setup warns about it. The
host's own documentation settles it (`code.claude.com/docs/en/permissions`, read against
Claude Code 2.1.269):

- **Rules resolve deny → ask → allow, first match wins, and specificity does not change the
  order.** "An allow rule can't carve an exception out of a deny rule. The same precedence
  applies between ask and allow: a matching ask rule prompts even when a more specific allow
  rule also matches the same call." So a project `allow` **cannot** undercut a floor entry.
  The overlap is worth reporting — the person should know their rule is inert for those
  commands — but stopping the run over it would refuse to write a floor that would have
  worked. §6's "conflict" is therefore implemented as §9's "warns", and both sentences of the
  plan are corrected to say the same thing.
- **Deny and ask rules already see compound commands.** They "apply when any subcommand
  matches them, including a command nested inside a subshell, a command substitution, or a
  control-flow body", and they match past a leading environment assignment. The plan's claim
  that the floor does no parsing of compound commands is true only of `allow` rules; corrected
  in §9.
- **What genuinely escapes a prefix rule** is a program named by an absolute path
  (`/bin/rm`), a shell wrapper (`bash -c '…'`), an environment runner (`devbox run`,
  `docker exec`), `find -exec` and `-delete`, exec wrappers such as `watch` and `setsid`, and
  git's own `-C` and `-c` forms — the documentation's example is that `Bash(git push *)` does
  not match `git -C . push origin main`. Where a second pattern closes the gap cheaply the
  floor carries it (`Bash(git * push *)` beside `Bash(git push *)`, the absolute-path spellings
  of `rm`, and an ask on `bash -c`); the rest is what `guard_only` records, and it is the
  answer to the plan's open question.
- **A bare tool name in `deny` removes the tool from the model's context entirely.** The floor
  therefore never writes one: every entry is scoped.
- **One mode does defeat the floor**: a permission mode that bypasses permissions. Setup warns
  and writes the floor anyway. Sandboxing does not defeat it, because content-scoped ask rules
  still prompt there.

So the overlap check stays, and what it produces is a notice, not a stop. It compares tool and
pattern: an entry equal to a floor entry's, or a prefix generalisation of it (`Bash(git *)`
meets `Bash(git push *)`; a bare `Bash` or `Bash(*)` meets everything). Anything else broad
enough to matter is reported as broad rather than judged, because a wrong "nothing to see" is
worse than a notice the person reads.

### Survey classifies by content, so nothing needs remembering

A fresh clone is the one case where "already harnessed" and "nothing to write" come
apart: the runtime state location is deliberately not committed, so a clone is recognised
from the record, asks nothing, and restores that one path. Everything committed is
reported unchanged.

Four classes, from the record and the bytes on disk: absent; **generated** (hash matches the
record); **current** (no record, or a stale one, but byte-identical to what would be
written — the state an interruption leaves); **project-owned**; **unaccounted for** (harness
path, present, matching neither). Recovery therefore needs no journal: re-running after an
interruption sees each written path as *current* and finishes. The declined pointer line
needs no memory either — its absence is the notice's trigger, so the notice repeats by
construction.

### Writes are atomic, the record is last, the order is fixed

Each path is written to a temporary sibling and `os.replace`d; the manifest last so that a
record never claims a path that is not there. The order is fixed — project files, rules,
state, settings, manifest — so a test can interrupt after each step and assert what the next
run does.

## Guarantees, by kind

Per the repository's rule that every guarantee names its kind and its failure mode:

| Guarantee | Kind | When the component fails |
|---|---|---|
| No project-owned byte changes without a yes | **prevention** in the script — it writes a project-owned path only for a flagged pointer-line insertion and cannot write one any other way — over **instruction** in the skill, which must not set the flag without a yes | If the session sets the flag wrongly, one known line is inserted into one known file: recoverable from version control, and the plan printed it first |
| Nothing is written while a conflict stands | **prevention**: `write` re-surveys and exits before its first write | If the script cannot run, nothing is written at all: setup's failure mode is doing nothing |
| A harness file edited by hand is never overwritten | **detection** before the write, by hash | If the record is absent, the refusal is total: it points at adoption rather than guessing |
| Generated content is identical for identical choices | **prevention** by construction, no stamps; **detection** by the committed snapshots | A stray stamp shows up as a snapshot diff in this repository's own checks before release |
| The floor covers every rule enforced by the guard | **detection** in the checks, rule by rule | A rule with neither an entry nor a recorded reason fails the check |
| A command the harness would refuse is still refused with nothing of ours running | **prevention** by the host, from the floor's entries | The floor is coarser than the guard, so some commands are asked about rather than refused; a host mode that bypasses permissions leaves nothing in force, which setup warns about and no harness can defend against |
| The project's own permission entries are preserved | **prevention**: the merge is by entry on parsed data | An unparsable file is a conflict and the run stops; formatting is not preserved the first time the floor lands, and the plan says so |
| A project entry that meets the floor is seen by the person | **detection**, reported in the plan | The host's rule order means the floor applies regardless, so a missed notice costs information, not protection |

## Risks / Trade-offs

- **The first merge reformats a project's permission file** → the plan names it before the
  yes, the content is preserved entry for entry, and every later run writes nothing.
- **The host's permission syntax may not express a pattern closely enough** → `guard_only`
  records it with its reason, the checks accept it, and `C4` inherits a list of exactly what
  only the guard can cover. The gaps are known and named above rather than assumed away.
- **The host's permission and settings formats change monthly** → every pattern lives in one
  file, with the verified version recorded; a format change is one file to edit.
- **A project may write real YAML in `.harnex.yml`** → the reader refuses with the line
  named and prints the shape it accepts, rather than half-understanding the file.
- **The floor lands before the guard exists**, so for one phase the only enforcement of the
  `safety` rules is coarse → the four rules are reworded to name both layers and say what
  each gives, so nothing claims prevention it does not have.
- **Adoption replaces a file the harness did not write** → only after showing the difference
  and an explicit yes, and the file is the harness's own rendering, never the project's.

## Migration Plan

Nothing to migrate: the capability is new and no project depends on it yet. Undoing a setup
in a scratch project is `git checkout` of the listed paths plus removing `.harnex/`; the
command is additive and never deletes. Migrating a real project is `C6`.
