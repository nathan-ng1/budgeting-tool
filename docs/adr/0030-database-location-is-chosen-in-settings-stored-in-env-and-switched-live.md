# The Database's location is chosen in Settings, stored in `.env`, and switched live

> **Partly superseded by [ADR-0032](./0032-one-data-location-resolver-with-a-pointer-file.md) and
> [ADR-0033](./0033-the-editions-differ-by-what-ships.md).** The location is stored in `.env` only
> while a `DATABASE_PATH` override exists; otherwise it is stored in a pointer file in the per-user
> data folder, and "Change location…" is available in the Retail Edition too. ADR-0033 records why
> there is one resolver for both editions.

The Settings tab now shows where the Database lives and offers a "Change location…" control. The
location has to be stored outside the Database, because a pointer can't live inside the file it
points to. We decided the Dashboard rewrites `DATABASE_PATH` in the repo-root `.env`, the same key
`setup.bat`/`setup.command` already write. The Statement Export pipeline, `python -m migration`,
the update scripts and the Budget Suggestion flow all read that key, so they follow a new location
without any change of their own. A switch replaces the Dashboard server's open connection while
the server keeps running, under the lock that already serialises every request. `.env` is rewritten
only after the new connection opens successfully, so a failed switch leaves both the Dashboard and
`.env` on the old Database.

"Claude never reads or edits `.env`" ([ADR-0001](./0001-sanitising-happens-outside-claudes-read-access.md))
is a boundary on Claude's own access, not on the Dashboard's code. The Dashboard process editing its
own configuration doesn't conflict with it.

## Considered Options

- **A pointer file in a fixed per-user folder** (e.g. `%LOCALAPPDATA%`), with `.env` as the fallback.
  Rejected for the Collaborator Edition. Every script would need to learn a second lookup, and two
  sources of truth for one path can disagree. This is likely the Retail Edition's answer, since it
  has no `.env` (see `docs/retail-edition-design-notes.md`, Q13).
- **Write `.env` and ask the user to restart the Dashboard.** Rejected. The request lock already
  makes a live swap safe, and asking a user to close and reopen the Dashboard is an easy step to get
  wrong mid-move.
- **A typed path instead of a native folder picker.** Rejected in favour of the native dialog. It
  runs in a short-lived child process, because macOS only allows Tk dialogs on a process's main
  thread and the server handles each request on its own thread.
- **An in-Dashboard Restore (upload a Backup and swap it in).** Rejected for now. A Backup is a
  complete Database, so pointing "Change location…" at the folder holding it is the restore. That
  avoids a second destructive control alongside "Delete data and reset dashboard".

## Consequences

- Choosing a folder that already holds a Database switches to it as-is, without copying over it.
  Before switching, the Dashboard checks the file against `schema_migrations`
  ([ADR-0025](./0025-update-runs-pending-migrations-tracked-in-the-database.md)):
  - a file that isn't one of ours is refused;
  - a file missing migrations is copied to a `pre-migration` file and then migrated;
  - a file recording a migration this code doesn't know (made by a newer Version) is refused.

  Migrations therefore run from the Dashboard as well as from the update scripts, using the same
  runner and registry.
- Choosing a folder with no Database moves the current one there, together with its
  `*.pre-migration-*.db` files. The old files are deleted only once the copy is verified and the
  switch succeeds.
- ~~This feature is Collaborator Edition only.~~ It now ships in both editions; ADR-0032 adds the
  pointer file the Retail Edition stores its location in.
