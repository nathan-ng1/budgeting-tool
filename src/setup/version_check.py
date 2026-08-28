from dataclasses import dataclass


@dataclass(frozen=True)
class VersionCheckResult:
    update_available: bool
    # Normalised (no leading "v") latest version, or None when `latest_tag`
    # was missing/malformed and no comparison could be made.
    latest_version: str | None


def check_update_available(local_version: str, latest_tag: str | None) -> VersionCheckResult:
    """Compare the installed version (`pyproject.toml`) against a Release tag.

    Pure function, no network/`gh` call - the caller is responsible for
    fetching `latest_tag` (e.g. via `gh api .../releases/latest`) and passing
    it in. A missing or malformed `latest_tag` (offline, `gh` unauthenticated,
    no Releases yet) degrades to "no update" rather than raising, matching
    ADR-0019's best-effort/silent behaviour.
    """
    latest_parsed = _parse_version(latest_tag) if latest_tag else None
    if latest_parsed is None:
        return VersionCheckResult(update_available=False, latest_version=None)

    normalised_latest = ".".join(str(part) for part in latest_parsed)
    local_parsed = _parse_version(local_version)
    if local_parsed is None:
        return VersionCheckResult(update_available=False, latest_version=normalised_latest)

    return VersionCheckResult(
        update_available=latest_parsed > local_parsed,
        latest_version=normalised_latest,
    )


def _parse_version(raw: str) -> tuple[int, ...] | None:
    text = raw.strip()
    if text.startswith(("v", "V")):
        text = text[1:]
    if not text:
        return None
    parts = text.split(".")
    if not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)
