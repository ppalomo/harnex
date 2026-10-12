### Where to look

Migrations live under the `versions/` directory the project's Alembic configuration names;
each holds one `upgrade()` and one `downgrade()`, and each names its `down_revision`. Pair
every migration with the SQLAlchemy model change in the same diff — this stack's
convention is that a schema change ships with the model it comes from, so a migration with
no model change beside it, or a model change with none, is a finding of order rather than
of style. Two migrations in the diff claiming the same `down_revision` are two heads, and
`alembic upgrade head` will refuse until one is merged; name it as certain.

### What autogenerate does not see

A migration written by `alembic revision --autogenerate` is a draft, not a reading of the
model. It renders a column rename as a drop and an add, which loses the column's data; it
does not detect a changed server default, an enum's new or removed members, a check
constraint, or a constraint's name; and the names it emits for the constraints it does
detect come from the metadata's naming convention, which `downgrade()` must match exactly
to drop. Read the forward step against the model, not against what the generator wrote,
and read the reverse step as what the forward step would need undone.

### Operations that lock or lose

On PostgreSQL, `add_column` with `nullable=False` and no `server_default` fails on any
existing row; `create_index` without `postgresql_concurrently=True` holds a lock for the
whole build, and the concurrent form cannot run inside the transaction Alembic opens by
default, so the migration must opt out of it; a type change through `alter_column`
rewrites the table. On SQLite most `ALTER` forms do not exist, and `batch_alter_table`
recreates the table, copying every row. A data step inside a schema migration —
`op.execute()` or a bulk update between two schema operations — runs under the same lock,
cannot be retried on its own, and is not reversed by anything `downgrade()` does to the
schema. A `downgrade()` that is `pass` is not a reverse step; say what it leaves behind.
