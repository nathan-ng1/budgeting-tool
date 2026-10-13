"""The "Your data" section's view of the Database: where it lives and how big
it is on disk (Issue #196)."""

from pathlib import Path


def as_payload(path: Path) -> dict:
    return {"path": str(path), "size_bytes": path.stat().st_size}
