"""Reads the Version History out of CHANGELOG.md (ADR-0029).

The file is hand-curated: newest first, each Version a level-2 heading
`## v<version> — <ISO date>` followed by `- ` bullets, optionally gathered under
`### <title>` sub-headings such as "New features" and "Bug fixes". The
sub-heading `### Collaborator Edition only` marks bullets a Retail Buyer
shouldn't see: the parser carries that group with `collaborator_only` set, the
Collaborator Edition shows it, and the build step drops it (see build_info.py).
Anything that doesn't fit that shape reads as no history at all rather than a
partial one, so the Dashboard shows its "isn't available" message instead of a
half-right list.
"""

import re
from datetime import date
from pathlib import Path

COLLABORATOR_ONLY_TITLE = "Collaborator Edition only"

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
            history.append({"version": heading["version"], "date": heading["date"], "entries": [], "groups": []})
        elif stripped.startswith("### "):
            if not history:
                return None
            title = stripped[4:].strip()
            history[-1]["groups"].append(
                {"title": title, "collaborator_only": title == COLLABORATOR_ONLY_TITLE, "entries": []}
            )
        elif stripped.startswith("- "):
            if not history:
                return None
            # A bullet belongs to the latest sub-heading, or is ungrouped before the first.
            current = history[-1]["groups"][-1] if history[-1]["groups"] else history[-1]
            current["entries"].append(stripped[2:].strip())

    if not history or any(not _has_entries(version) for version in history):
        return None
    return history


def without_collaborator_only(history: list[dict]) -> list[dict]:
    """`history` minus the Collaborator-only groups, and minus any Version left with nothing to show."""
    shared = []
    for version in history:
        groups = [group for group in version["groups"] if not group["collaborator_only"]]
        remaining = {**version, "groups": groups}
        if _has_entries(remaining):
            shared.append(remaining)
    return shared


def _has_entries(version: dict) -> bool:
    return bool(version["entries"]) or any(group["entries"] for group in version["groups"])


def _is_iso_date(text: str) -> bool:
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return True
