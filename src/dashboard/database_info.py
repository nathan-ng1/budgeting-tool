"""The "Your data" section's view of the Database: where it lives, how big it
is on disk (Issue #196) and when a Backup was last made (Issue #197)."""

import tempfile
from datetime import datetime
from pathlib import Path


def as_payload(path: Path, last_backed_up: str | None = None) -> dict:
    return {"path": str(path), "size_bytes": path.stat().st_size, "last_backed_up": last_backed_up}


def backup_file_name(database_path: Path, now: datetime) -> str:
    """A timestamped default name for the downloaded Backup, e.g.
    `budget-backup-20261013-142530.db`."""
    return f"{database_path.stem}-backup-{now.strftime('%Y%m%d-%H%M%S')}{database_path.suffix}"


def make_backup(store, now: datetime) -> tuple[bytes, str]:
    """Generate a Backup of the live Database: its bytes and default file name.

    "Last backed up" is recorded here, when the Backup is generated - the
    server can't know whether the browser's save completed (Issue #197)."""
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / "backup.db"
        store.backup_to(target)
        body = target.read_bytes()
    store.record_backup(now.isoformat(timespec="seconds"))
    return body, backup_file_name(store.path, now)
