## MODIFIED Requirements

### Requirement: A fresh clone updates unaided

The command SHALL complete in a project freshly cloned from one that was set up, reading
only what is committed, asking nothing and refusing nothing on account of the clone being
fresh. The `.env` entry in the clone's own exclude list counts as harness-written for
this purpose: the exclude list is per clone and never committed, and the harness wrote
the entry there in the first place.

#### Scenario: Cloned, then updated

- **WHEN** a harnessed project is cloned on another machine and the command is run before
  anything else touches it
- **THEN** every committed harness-owned path is recognised from the committed record, the
  runtime state location is restored and, for a `jev` project, so is the `.env` entry in
  the clone's own exclude list, and the command asks nothing
