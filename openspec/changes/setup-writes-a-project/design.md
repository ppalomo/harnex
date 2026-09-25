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

### A command asks, a skill holds the procedure, a script does the work

`/harnex:setup` is a thin command under `plugin/commands/`; the procedure it follows —
the questions, in what order, what to show, what counts as a yes — is a skill,
`plugin/skills/harnex-setup/`; every filesystem step is `plugin/scripts/setup.py`. All three
are pillar 2.

The split is what makes the specs testable: the script has two verbs, `plan` and `write`,
and both take one answers document (`--answers <file|->`) and return a machine-readable
result plus the human lines the session prints. `write` re-runs the survey itself and refuses
if any conflict stands, so an approval given against a stale plan cannot write anything.

Alternatives: everything in the command prompt — nothing testable, and the plan's own
sequence would be advice; one script that prompts on a terminal — Claude Code gives it none,
and the questions belong to the session that can explain them. The skill exists rather than
folding the procedure into the command because `C6`'s `update` repeats most of it, and a
procedure stated twice is the thing this repository refuses.

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

An `allow` entry undercuts the floor when its tool matches and its pattern covers a floor
entry's — equal, or a prefix generalisation of it (`Bash(git:*)` covers `Bash(git push:*)`;
`Bash` and `Bash(*)` cover everything). Only that shape is compared; anything else broad
enough to matter is reported as broad rather than judged. The comparison is deliberately
coarse and the report says so, because a wrong "no conflict" is worse than a conflict the
person looks at.

### Survey classifies by content, so nothing needs remembering

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

## Risks / Trade-offs

- **The first merge reformats a project's permission file** → the plan names it before the
  yes, the content is preserved entry for entry, and every later run writes nothing.
- **The host's permission syntax may not express a pattern closely enough** → `guard_only`
  records it with its reason, the checks accept it, and `C4` inherits a list of exactly what
  only the guard can cover.
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
