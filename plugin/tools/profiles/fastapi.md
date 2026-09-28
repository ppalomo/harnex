# fastapi

A Python backend on FastAPI, SQLAlchemy, Alembic, and pytest.

## Check command

The project's own `AGENTS.md` names the single command that lints, formats, type-checks
and runs the test suite. This profile does not guess one — a builder that finds none
declared asks rather than inventing a target that may not exist. Where the project keeps
a target that exercises the real database, `AGENTS.md` names that too; a test run full of
skips is treated as no evidence at all, not as a passing check.

## Conventions

- Layering is declared by the project, not assumed: which layers exist, what each may
  import, and where the composition root lives. A change that crosses a layer boundary
  `AGENTS.md` did not declare is worth naming in a builder's report, not silently allowed.
- A schema change is a migration, not a hand-edited table — Alembic owns the history, and
  a migration is written for the same commit as the model change it comes from.
- A row is not a domain rule. Four files that move a value from a database row to a JSON
  response are ceremony unless `AGENTS.md` names the rule they protect; where it does not,
  a builder follows the layering as written rather than inventing a justification for it.

## Tools expected

FastAPI, SQLAlchemy, Alembic, pytest. Dependency and virtual-environment management is
whatever the project's own lockfile already names — this profile does not choose one.
