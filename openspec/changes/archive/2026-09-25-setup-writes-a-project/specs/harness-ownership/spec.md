## Purpose

Which paths and entries in a harnessed project belong to the harness rather than to the
project, the committed record of what the harness generated, and the contract every later
regeneration obeys so that refreshing the harness never overwrites a person's work.

## ADDED Requirements

### Requirement: What the harness generated is recorded, and the record is committed

The harness SHALL keep, in the project, a record of everything it generated: every path it
owns with a fingerprint of the content it wrote, and, for the one file it shares with the
project, exactly the entries it wrote. That record SHALL be part of what the project
commits, so that ownership is known in a fresh clone without inspecting anything else.

#### Scenario: Reading what the harness owns

- **WHEN** any harness operation needs to know whether a path is its own
- **THEN** it reads the record, which names every harness-owned path with the fingerprint of
  the content written, and the entries it owns inside the shared file

#### Scenario: A fresh clone

- **WHEN** a harnessed project is cloned on another machine
- **THEN** the record is present and ownership is established without asking the person and
  without re-deriving it from the files

### Requirement: Ownership is by file, with one shared file owned by entry

Every path in a harnessed project SHALL be owned either by the harness or by the project.
The single exception SHALL be the file the host reads the project's permissions from, which
SHALL be shared and owned entry by entry: the harness owns the entries recorded as its own
and nothing else in that file.

#### Scenario: A project-owned path

- **WHEN** a harness operation runs over a project-owned path
- **THEN** it reads it, may report on it, and does not write it

#### Scenario: The shared file

- **WHEN** the harness writes its entries into the shared file
- **THEN** only the entries recorded as the harness's own are its to change, and every other
  entry, and the rest of the file's content, is preserved

### Requirement: A harness-owned file is overwritten only when it matches the record

A harness-owned file SHALL be overwritten only when its current content matches the
fingerprint in the record, or matches the content about to be written. In every other case
the operation SHALL stop, name the file, and write nothing.

#### Scenario: The file is as the harness left it

- **WHEN** a harness-owned file matches its recorded fingerprint and its rendering has
  changed
- **THEN** it is rewritten and the record updated

#### Scenario: The file was edited by hand

- **WHEN** a harness-owned file matches neither its recorded fingerprint nor the content to
  be written
- **THEN** the operation stops before writing anything, names the file, and says that it was
  edited after the harness wrote it

#### Scenario: The file is already what would be written

- **WHEN** a harness-owned file does not match the record but is byte-identical to the
  content about to be written
- **THEN** it is accepted as already current, nothing is rewritten, and the record is brought
  up to date

### Requirement: Generated content is a pure function of the project's choices

Every file the harness generates SHALL depend only on the project's recorded choices and on
the harness's own content. It SHALL contain no timestamp, no version stamp and nothing else
that changes between two runs of the same choice, and SHALL NOT depend on the order in which
a choice was given.

#### Scenario: The same choice, twice, anywhere

- **WHEN** the same choices are rendered on another machine, at another time, or with a
  choice list in a different order
- **THEN** the generated content is identical, byte for byte

#### Scenario: Nothing to refresh

- **WHEN** neither the project's choices nor the harness's content has changed since the
  record was written
- **THEN** every harness-owned file already matches its fingerprint and there is nothing to
  write

### Requirement: Writes are atomic and the record is written last

Every write to a harness-owned path SHALL be atomic: the content is written elsewhere and put
in place in one step, so an interrupted operation never leaves a partially written file. The
record SHALL be written after the paths it describes.

#### Scenario: Interrupted mid-write

- **WHEN** an operation is interrupted while writing a harness-owned file
- **THEN** the path is either absent or holds complete content, never a fragment

#### Scenario: Interrupted before the record

- **WHEN** an operation is interrupted after writing some paths and before writing the record
- **THEN** running it again recognises each written path as already current by its content,
  completes the remaining paths, and writes the record

### Requirement: Harness files with no record are never guessed at

An operation finding paths the harness owns but no record accounting for them SHALL refuse
to proceed and SHALL point to the operation that surveys and asks. Adoption of such a path
SHALL replace it only after showing the person the difference and receiving an explicit yes.

#### Scenario: The record is missing

- **WHEN** harness-owned paths are present and the record is absent — deleted, or the project
  was harnessed by hand
- **THEN** the operation refuses, says it will not guess what it owns, and names the operation
  that can adopt the project

#### Scenario: Adopting a file the harness did not write

- **WHEN** the person asks the harness to adopt an unaccounted-for harness-owned file
- **THEN** the difference between its content and what the harness would write is shown, and
  the file is replaced only after an explicit yes

### Requirement: What the harness reads and what it writes are bounded

Any operation that refreshes a harnessed project SHALL read the project's recorded choices
and the record as its input, MAY read project-owned files only to report on them, and SHALL
write nothing but harness-owned paths and harness-owned entries.

#### Scenario: A refresh in a project whose entry files lack the pointer line

- **WHEN** a refresh runs and a project-owned entry file does not point at the rules
- **THEN** the refresh reports it and does not write that file
