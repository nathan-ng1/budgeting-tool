"""Every one-off migration the update process runs, oldest first (Issue #152,
ADR-0025).

To add one: write `migration/<name>.py` exposing `migrate(connection)`, then
append it to the end of MIGRATIONS - never reorder or rename an entry once it
has shipped, since the name is what `schema_migrations` records. A brand new
database marks every entry here as applied without running it (see
`database.store.open_connection`), so a migration only ever runs against an
install that existed before it shipped.
"""

from migration import add_bills_and_subscriptions, categories_table, rename_transfer_to_savings
from migration.runner import Migration

MIGRATIONS = [
    Migration(name="categories_table", migrate=categories_table.migrate),
    Migration(name="rename_transfer_to_savings", migrate=rename_transfer_to_savings.migrate),
    Migration(name="add_bills_and_subscriptions", migrate=add_bills_and_subscriptions.migrate),
]
