"""Reads the Version History out of CHANGELOG.md (ADR-0029).

The file is hand-curated: newest first, each Version a level-2 heading
`## v<version> — <ISO date>` followed by a flat list of `- ` bullets. Anything
that doesn't fit that shape reads as no history at all rather than a partial
one, so the Dashboard shows its "isn't available" message instead of a
half-right list.
"""

import re
from datetime import date
from pathlib import Path

HEADING = re.compile(r"^## v(?P<version>\d+\.\d+\.\d+) — (?P<date>\d{4}-\d{2}-\d{2})\s*$")


def read_history(path: Path) -> list[dict] | None:
    """The parsed Versions, newest first, or None if the file is missing or malformed."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    history: list[dict] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            heading = HEADING.match(stripped)
            if heading is None or not _is_iso_date(heading["date"]):
                return None
            history.append({"version": heading["version"], "date": heading["date"], "entries": []})
        elif stripped.startswith("- "):
            if not history:
                return None
            history[-1]["entries"].append(stripped[2:].strip())

    if not history or any(not version["entries"] for version in history):
        return None
    return history


def _is_iso_date(text: str) -> bool:
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return True
