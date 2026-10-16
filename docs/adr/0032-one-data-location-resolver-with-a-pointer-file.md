# One data-location resolver, with a pointer file in the per-user folder

The Retail Edition has no `.env` and no repo to hold one, so ADR-0030's rule "the Database's
location is `DATABASE_PATH` in the repo-root `.env`" can't be the only source. We decided every entry
point, in both editions, resolves the Database location the same way, in `database.location`:

1. an **override**: the `DATABASE_PATH` environment variable or the `.env` value. When set, nothing
   else is consulted;
2. the **pointer file** (`database-location.txt`) in the per-user data folder, holding the absolute
   path of the Database file;
3. the **default**: `budget.db` in the per-user data folder (`%LOCALAPPDATA%\Budgeting Tool` on
   Windows, `~/Library/Application Support/Budgeting Tool` on macOS).

The Statement Export pipeline, `python -m migration` (so the update scripts), the Budget Suggestion
flow and the Dashboard all reach it through `database.store.connect`/`open_connection`, so none has a
lookup of its own. Collaborator installs keep their `.env` untouched and never reach steps 2 or 3.

"Change location…" ships in both editions and records the new location where the resolver will look
for it: it rewrites `.env` when an override exists (the override would win over anything else), and
otherwise writes the pointer file. As before, it records the location only after the new connection
opened, so a failed switch leaves `.env`, the pointer file and the live Database as they were. Both
writes go through a temporary file and a rename.

An unreadable pointer, or one that is blank, relative, names a folder, or names a file in a folder
that isn't there (an unplugged drive, an unsynced cloud folder), is ignored and the default folder is
used, so a stale pointer degrades to a working app rather than a stopped one.

This partly supersedes [ADR-0030](./0030-database-location-is-chosen-in-settings-stored-in-env-and-switched-live.md):
its live switch, move and migrate behaviour stand, and "stored in `.env`" now holds only while an
override exists. ADR-0030's "pointer file in a fixed per-user folder" option, rejected there for the
Collaborator Edition because every script would need a second lookup, is adopted here because the
lookup is now one shared function.

## Consequences

- A Database path that disappears (deleted pointer target, unplugged drive) silently falls back to a
  fresh Database in the default folder rather than failing. Accepted: the original file is untouched,
  and Settings shows the path in use.
- The environment variable beats `.env`, as `load_dotenv` already did.
- Tests must never touch the real per-user folder or the developer's `.env`; `tests/conftest.py`
  redirects both for every test.
