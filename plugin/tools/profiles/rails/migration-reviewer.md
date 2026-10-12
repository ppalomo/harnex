### Where to look

Migrations live under `db/migrate/`, one class per file, named by a timestamp that is
also its version; the diff that adds one also changes `db/schema.rb` or
`db/structure.sql`, whichever the project commits. A migration with no schema change
beside it has not been run; a schema change with no migration was hand-edited; and two
migrations with the same version will not both load. Pair every migration with the model
change it serves — a column added that no model reads, or a model reading a column no
migration adds, is a finding of order rather than of style. Where `AGENTS.md` names the
`strong_migrations` gem, read each `safety_assured` block as a place the author chose to
silence it, and ask what was silenced.

### What `change` can and cannot undo

A `change` method is reversible only if every call in it is: `remove_column` without the
column's type cannot be re-added on the way down, `change_column` keeps no record of the
old type, `execute` has no inverse, and `change_column_default` without `from:` and
`to:` has none either. Any of those inside `change` is a migration that raises on
rollback, not one that reverses; the honest form is `up` and `down`, or `reversible`
with both branches, and a `down` that raises `IrreversibleMigration` is a statement, not
a reverse step — say what it leaves behind. A data step inside a schema migration, or a
model class referenced from one, binds the migration to the code of the day it was
written: `Model.update_all` in a migration runs with whatever the model is now.

### Operations that lock or lose

On PostgreSQL, `add_index` without `algorithm: :concurrently` holds a lock for the whole
build, and the concurrent form only runs with `disable_ddl_transaction!` on the class; a
type change through `change_column` rewrites the table; `add_foreign_key` validates every
existing row under a lock unless `validate: false` is given and a `validate_foreign_key`
follows; and on versions before 11 a column added with a default rewrites every row.
`change_column_null` to `false` scans a large table with it locked and fails on any null
that remains; `add_column` with `null: false` and no default fails on any existing row.
A `remove_column` loses the column's data whether or not the migration reverses, and a
`rename_column` breaks every running process that still reads the old name until the
deploy completes.
