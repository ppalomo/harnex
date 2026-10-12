# rails

A Ruby on Rails application: Rails, Active Record, Active Record migrations, and Minitest
or RSpec as the project declares.

## Check command

The project's own `AGENTS.md` names the single command that lints, formats, type-checks
and runs the test suite. This profile does not guess one — a builder that finds none
declared asks rather than inventing a target that may not exist. Where the project keeps
a target that exercises the real database, `AGENTS.md` names that too; a test run full of
skips or pending examples is treated as no evidence at all, not as a passing check.

## Conventions

- A schema change is a migration, not a hand-edited table — Active Record migrations own
  the history, and the migration is committed with the `db/schema.rb` or
  `db/structure.sql` it produces; which of the two the project keeps is declared in
  `AGENTS.md`, not assumed.
- Where logic lives is the project's call, not the stack's: fat models and thin
  controllers, service objects, or something else, as `AGENTS.md` declares. A change that
  puts a rule somewhere the project did not declare is worth naming in a builder's
  report, not silently allowed.
- Strong parameters sit at the boundary: a controller permits what an action takes and
  nothing more, and a `permit` list is read as part of the contract it guards.
- An N+1 query is named in a builder's report, with the association that causes it, not
  silently allowed — whether to preload it is a decision the report makes visible.

## Tools expected

Rails, Active Record, Bundler, and whatever the project's own `Gemfile.lock` already
names. The test framework and the linter are the project's — this profile does not choose
one.

## Team

This profile is a directory, and each file beside this one is what this stack adds to one
specialist: `security-reviewer.md`, `migration-reviewer.md` and `api-designer.md`. A
project that chooses `rails` gets those three agents, each rendered from the role of the
same name with the fragment appended, and nothing a fragment says alters the role.
