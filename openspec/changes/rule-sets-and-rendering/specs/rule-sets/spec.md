## Purpose

How the harness states a rule: the one file a rule lives in, the fields that file
declares, the sets that group rules into something a project can choose, and the
rendering that turns a chosen list of sets into the rules file a project's agents read.

## ADDED Requirements

### Requirement: A rule is one file, stated once

Every rule SHALL be a single file, and the harness SHALL hold no second statement of the
same rule. The file SHALL declare, in a form a check can read without executing it, the
rule's identity, the set it belongs to, what it applies to, and what enforces it. The
rule as an agent reads it SHALL be the file's body, beginning with the rule stated as one
sentence and followed by the reason it exists.

#### Scenario: Reading a rule

- **WHEN** an agent or a person opens a rule file
- **THEN** the first line of the body is the rule in one sentence, and what follows is
  why it exists, with no other rule stated in the same file

#### Scenario: A rule file missing a declared field

- **WHEN** the rule files are checked and one declares fewer or other fields than the
  format requires
- **THEN** the check fails, naming the file and the field

#### Scenario: A rule's identity matches where it lives

- **WHEN** the rule files are checked
- **THEN** each rule's identity is unique across every set, matches the name of its own
  file, and the set it declares is the set it is stored in; any mismatch fails the check
  and names the file

### Requirement: A rule that is enforced names its enforcer

A rule SHALL declare whether it is enforced and by what kind of enforcement. A rule that
declares any enforcement SHALL name, in its body, the component that does the enforcing,
so that a reader of the rule can find the code and a reader of the code can find the
rule. A rule that declares no enforcement SHALL name none.

#### Scenario: An enforced rule that names no enforcer

- **WHEN** the rule files are checked and a rule declares an enforcement but its body
  names no enforcer
- **THEN** the check fails, naming the rule

#### Scenario: An enforcement kind outside the declared vocabulary

- **WHEN** a rule declares an enforcement that is not one of the kinds the format allows
- **THEN** the check fails, naming the rule and listing the kinds allowed

### Requirement: Rules are grouped into sets a project chooses

Rules SHALL be grouped into named sets, and a set SHALL be the unit a project selects.
Every set SHALL contain at least one rule, and every rule SHALL belong to exactly one
set. The sets available SHALL be discoverable from the harness itself rather than from a
list kept beside it.

#### Scenario: Listing what a project can choose

- **WHEN** the available sets are asked for
- **THEN** they are derived from the rules the harness holds, so a set that has been
  added is offered and a set that has been removed is not

#### Scenario: An empty set

- **WHEN** the rule files are checked and a set holds no rule
- **THEN** the check fails, naming the set

### Requirement: A chosen list of sets renders one rules file

The harness SHALL render a list of chosen sets into a single rules file that states every
rule in those sets and nothing else. The rendered file SHALL be readable on its own,
saying what produced it and what a reader must do to change a rule.

#### Scenario: Rendering the chosen sets

- **WHEN** a list of sets is rendered
- **THEN** the result contains every rule of every chosen set, each with its statement
  and its reason, and no rule from any set that was not chosen

#### Scenario: Rendering to a destination or to the screen

- **WHEN** a rendering is asked for a file, and the same rendering is asked for the screen
- **THEN** both produce the same content, byte for byte

### Requirement: Rendering is deterministic and independent of the order asked for

The same chosen sets SHALL always render the same file, byte for byte, regardless of the
order in which the sets were given, of repetitions in that list, and of how many times
the rendering is run. The content rendered for one set SHALL NOT depend on which other
sets were rendered beside it.

#### Scenario: The same choice rendered twice

- **WHEN** the same list of sets is rendered twice
- **THEN** the two results are identical, byte for byte

#### Scenario: The same choice given in a different order

- **WHEN** two lists name the same sets in different orders, or one of them repeats a set
- **THEN** both render the same file, byte for byte

#### Scenario: One set's content is the same beside any other

- **WHEN** a set is rendered alone and rendered again together with other sets
- **THEN** the part of the result belonging to that set is identical in both

### Requirement: A rule that applies to a profile is rendered only for that profile

A rule SHALL declare whether it applies always or only to a named profile. A rule that
applies to a profile SHALL be rendered only when the project has declared that profile,
and SHALL be absent otherwise. A rule that declares a profile that the harness does not
hold SHALL fail the check.

#### Scenario: A project without the profile

- **WHEN** a set holding a profile rule is rendered for a project that does not declare
  that profile
- **THEN** the rule is absent from the result, and every rule of that set that applies
  always is present

#### Scenario: A project with the profile

- **WHEN** the same set is rendered for a project that declares that profile
- **THEN** the rule is present in the result

#### Scenario: A rule naming a profile that does not exist

- **WHEN** the rule files are checked and a rule applies to a profile the harness does
  not hold
- **THEN** the check fails, naming the rule and the profile

### Requirement: Rendering refuses what it cannot render

Rendering SHALL fail, without writing anything, when it is asked for a set the harness
does not hold or for no set at all, and SHALL say what went wrong and what it does hold.

#### Scenario: An unknown set

- **WHEN** a rendering names a set the harness does not hold
- **THEN** it fails, names the unknown set, lists the sets it does hold, and writes no
  file

#### Scenario: No set at all

- **WHEN** a rendering names no set
- **THEN** it fails and says so, and writes no file
