# The update process runs pending one-off migrations, tracked in the database

Schema and default-data changes reach an existing install through one-off scripts in
`src/migration/` (ADR-0022, ADR-0024), because `database.store._seed_default_categories` never
reseeds a non-empty `categories` table. Nothing ran those scripts, so each had to be run by hand and
was easy to miss: the live database still held a `Transfer`-typed Category long after
`rename_transfer_to_savings` shipped.

We decided `update.bat`/`update.command` run `python -m migration` after `uv sync`. It runs every
pending migration once, in order, and records each one in the database itself:

- **Tracking:** a `schema_migrations` table (`name`, `applied_at`), one row per applied migration,
  owned by `migration.runner`. We chose it over `PRAGMA user_version`, which holds one integer. That
  can't record which migrations have run, and it can't be inspected without knowing the numbering.
  Re-running every migration on each update was ruled out: today's three are idempotent, but a
  future one need not be.
- **Ordering:** an explicit registry list, `migration.registry.MIGRATIONS`, not filename discovery.
  The order is reviewable in one place, and a stray file in `src/migration/` never runs by accident.
  An entry's name is what gets recorded, so entries are only ever appended, never renamed or
  reordered.
- **New installs:** `database.store.open_connection` treats a database with no `transactions` table
  as brand new. It already builds the current schema there, so it records every registered migration
  as applied without running any.
- **Existing installs on first rollout:** nothing is pre-marked. All three current migrations are
  safe to re-run, and `rename_transfer_to_savings` is still needed on the live database.
- **Failure:** the runner stops at the first failing migration and doesn't record it, so the next
  run retries it. The update script stops with a message, matching its `errorlevel` handling for
  `uv sync`. Migrations commit their own work, so one can fail partway. For that reason the
  database file is backed up next to itself (`<name>.pre-migration-<timestamp>.db`) before anything
  runs. No backup is made when nothing is pending.

## Consequences

- Widens [ADR-0019](./0019-update-checks-are-automatic-updates-are-manual.md)'s "pull-latest-and-
  re-sync" scope for `update` to include migrating the database. Applying an update stays a manual,
  confirmed step, so ADR-0019's decision itself is unchanged. ADR-0022's and ADR-0024's one-off
  scripts are now run by the update process instead of by hand.
- Adding a migration means writing `src/migration/<name>.py` with `migrate(connection)` and
  appending it to `MIGRATIONS`. Nothing else is needed for the next update to apply it.
- Running a migration script directly would skip the record, so the scripts no longer have their
  own `__main__` entry points. `uv run python -m migration` is the one way to run them by hand.
- A migration is never run on a database created after it shipped. It only has to handle installs
  that existed before it.
- Each update with pending migrations leaves one backup file beside the database. Nothing deletes
  them automatically.
