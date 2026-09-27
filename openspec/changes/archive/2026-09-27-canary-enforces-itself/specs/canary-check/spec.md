## Purpose

How the harness detects, at the end of each answer in the main session, that the project's
canary word is missing — the cheapest observable sign that the rules may have dropped out
of the context — and tells the person, without ever blocking the work.

## ADDED Requirements

### Requirement: The check runs at the end of every main-session answer

The harness SHALL check the canary at the end of every answer the main session gives, and
SHALL read the answer from what the host passes to the check at that moment, not from the
session's transcript. It SHALL NOT check the answers of subagents.

#### Scenario: An answer in the main session ends

- **WHEN** the main session finishes an answer in a project that chose the `canary` set
- **THEN** the check runs once for that answer and reads the answer the host passed to it

#### Scenario: A subagent finishes

- **WHEN** a subagent started by the main session finishes its answer
- **THEN** the canary check does not run for it, and nothing is reported

### Requirement: The check acts only where the project chose it

The check SHALL be inert in a project without a `.harnex.yml` at its root, and in a project
whose `.harnex.yml` does not list `canary` among its sets. Inert means it reads nothing
beyond looking for that file and the sets it lists, reports nothing and changes nothing.

#### Scenario: A project that never ran setup

- **WHEN** an answer ends in a project with no `.harnex.yml` at its root
- **THEN** the check reports nothing, whatever the answer says

#### Scenario: A project that did not choose the set

- **WHEN** an answer ends in a project whose `.harnex.yml` does not list `canary` among its
  sets
- **THEN** the check reports nothing, whatever the answer says

### Requirement: The word comes only from the project

The check SHALL take the canary word only from the `canary` key of the project's
`.harnex.yml`. It SHALL hold no word of its own and SHALL NOT fall back to the word setup
proposes.

#### Scenario: A project with its own word

- **WHEN** a project records a word other than the one setup proposes, and an answer ends
  with the proposed word but not with the project's
- **THEN** the check reports the word missing

#### Scenario: The set chosen without a word

- **WHEN** a project's `.harnex.yml` lists the `canary` set and records no word
- **THEN** the check reports that the set is chosen but no word is recorded, and does not
  check the answer against any word

### Requirement: What counts as ending with the word

An answer SHALL count as ending with the word when, after removing trailing whitespace and
any trailing emphasis or code markers the answer's formatting wraps the word in, it ends
with the word exactly as recorded, case included. An answer that holds the word anywhere
else SHALL NOT count.

#### Scenario: The word on its own last line

- **WHEN** an answer's last non-blank line is the recorded word
- **THEN** the check reports nothing

#### Scenario: The word wrapped in formatting

- **WHEN** an answer ends with the recorded word set in bold, italics or inline code,
  followed by trailing whitespace
- **THEN** the check reports nothing

#### Scenario: The word earlier in the answer

- **WHEN** an answer mentions the recorded word in its middle and ends with other text
- **THEN** the check reports the word missing

#### Scenario: The word in another case

- **WHEN** an answer ends with the recorded word in a different letter case
- **THEN** the check reports the word missing

### Requirement: A missing word is reported as a signal to the person

When the word is missing, the check SHALL report it to the person in one warning that names
the word, says that this instruction was not followed in the answer, says that the rules
may no longer be in effect, and names compacting or starting a new session as the usual
remedy. The warning SHALL NOT claim that the context is lost, and SHALL NOT be sent to the
model as an instruction.

#### Scenario: The word is missing

- **WHEN** an answer in a project that chose the `canary` set does not end with the word
- **THEN** the person sees one warning naming the word, and the session carries on

### Requirement: The check never blocks the work

The check SHALL NOT stop an answer from ending, SHALL NOT make the model continue, and
SHALL NOT change any file. Whatever it finds or fails to find, the turn SHALL end as it
would have without the check.

#### Scenario: The word is missing and the turn ends

- **WHEN** the check finds the word missing
- **THEN** the answer still ends, and the model is not asked to continue

#### Scenario: The check itself fails

- **WHEN** the check cannot complete — it crashes, runs out of time, or the host passes it
  something it cannot read
- **THEN** the answer still ends; the person is told the canary was not checked — by the
  check itself when it can still say so, otherwise by the host's own notice of a failed
  hook — and the check never reports a missing word it did not verify

### Requirement: What the check cannot judge it does not judge

When the host passes no answer text, or an empty one, the check SHALL report nothing. When
the project's `.harnex.yml` exists but cannot be read, the check SHALL report that it could
not read the file and that the canary was not checked, naming the reason, rather than stay
silent or guess.

#### Scenario: No answer text

- **WHEN** the host's end-of-turn input carries no answer text, or an empty one
- **THEN** the check reports nothing

#### Scenario: An unreadable choices file

- **WHEN** the project's `.harnex.yml` exists but is not in the form setup writes
- **THEN** the check reports that the canary was not checked because the file could not be
  read, with the reason, and reports nothing about the word

### Requirement: The check is tested against what the host really sends

The harness SHALL keep, as test fixtures, end-of-turn inputs recorded from a real host
session, with the host version they were recorded on, and SHALL test the check against
them. Paths and identifiers in the fixtures SHALL be replaced so that nothing private is
committed.

#### Scenario: The host changes the field the check reads

- **WHEN** a recorded fixture no longer carries the answer text in the field the check
  reads
- **THEN** a test fails, naming the field and the host version the fixture was recorded
  on
