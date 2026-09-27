## MODIFIED Requirements

### Requirement: A rule that is enforced names its enforcer

A rule SHALL declare whether it is enforced and by what kind of enforcement. A rule that
declares any enforcement SHALL name, in its body, the component that does the enforcing,
so that a reader of the rule can find the code and a reader of the code can find the
rule. A rule that declares no enforcement SHALL name none.

For enforcement by a hook the walk SHALL be checked in both directions: a rule that
declares enforcement by a hook SHALL name, by its path within the plugin, a script that
exists and that a hook the plugin declares runs; and every hook the plugin declares SHALL
run a script that some rule names as its enforcer.

#### Scenario: An enforced rule that names no enforcer

- **WHEN** the rule files are checked and a rule declares an enforcement but its body
  names no enforcer
- **THEN** the check fails, naming the rule

#### Scenario: An enforcement kind outside the declared vocabulary

- **WHEN** a rule declares an enforcement that is not one of the kinds the format allows
- **THEN** the check fails, naming the rule and listing the kinds allowed

#### Scenario: A rule claims a hook the plugin does not declare

- **WHEN** a rule declares enforcement by a hook, and the script it names does not exist
  or no hook the plugin declares runs it
- **THEN** the check fails, naming the rule and the script

#### Scenario: A hook no rule claims

- **WHEN** the plugin declares a hook whose script no rule names as its enforcer
- **THEN** the check fails, naming the hook's event and script, because a check with no
  rule behind it enforces something no agent was told
