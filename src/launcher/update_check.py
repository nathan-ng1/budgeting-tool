"""The launcher's daily update check (Issue #251, spec #236, decision S7).

Once a day at most, the launcher reads the update manifest (`latest.json`) and
remembers the newest Version it names, so the Dashboard can say an update exists
without making a network call itself (ADR-0008). The check is silent: offline,
a slow host or a malformed manifest all read as "nothing to report". Applying an
update stays manual (ADR-0019).

What is remembered is the last attempt's time and the newest Version seen, in
the data folder. The answer is worked out against the installed Version on every
launch, so a Buyer who has just updated is never told about the Version they
already have.
"""

import json
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen

from dashboard.build_info import BUILD_INFO_PATH, package_version, read_build_info
from setup.version_check import check_update_available

STATE_FILE_NAME = "update-check.json"
CHECK_INTERVAL = timedelta(days=1)
# Short: the launcher waits on this before the Dashboard opens.
FETCH_TIMEOUT_SECONDS = 3
# The manifest carries the Version History, so it is more than a line or two.
MAX_MANIFEST_BYTES = 1_000_000


def fetch_manifest(url: str) -> object:
    """The manifest at `url`, parsed. Raises on any failure; the caller decides it does not matter."""
    with urlopen(url, timeout=FETCH_TIMEOUT_SECONDS) as response:
        return json.loads(response.read(MAX_MANIFEST_BYTES))


def installed_version() -> str | None:
    """This build's Version: the baked-in one when compiled, else the installed package's."""
    info = read_build_info(BUILD_INFO_PATH)
    return info["version"] if info is not None else package_version()


def check_for_update(
    data_folder: Path,
    *,
    installed_version: str | None,
    manifest_url: str | None,
    fetch: Callable[[str], object],
    now: Callable[[], datetime],
) -> str | None:
    """The Version a Buyer should be told is available, or None.

    Fetches the manifest only if the last attempt was a day or more ago; a failed
    attempt counts, so being offline does not mean a wait at every launch.
    Never raises.
    """
    if installed_version is None or manifest_url is None:
        return None

    checked_at, latest = _read_state(data_folder)
    current = now()
    if checked_at is None or not timedelta(0) <= current - checked_at < CHECK_INTERVAL:
        latest = _newest_from(manifest_url, fetch) or latest
        _write_state(data_folder, current, latest)

    if latest is None:
        return None
    result = check_update_available(installed_version, latest)
    return result.latest_version if result.update_available else None


def _newest_from(manifest_url: str, fetch: Callable[[str], object]) -> str | None:
    """The normalised Version the manifest names, or None if it can't be had."""
    try:
        manifest = fetch(manifest_url)
        version = manifest["version"]
    except Exception:
        # Offline, a slow or broken host, not JSON, not an object: all the same here.
        return None
    if not isinstance(version, str):
        return None
    return check_update_available("", version).latest_version


def _read_state(data_folder: Path) -> tuple[datetime | None, str | None]:
    try:
        state = json.loads((data_folder / STATE_FILE_NAME).read_text(encoding="utf-8"))
        checked_at = datetime.fromisoformat(state["checked_at"])
    except (OSError, ValueError, KeyError, TypeError):
        return None, None
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=timezone.utc)
    latest = state.get("latest_version")
    return checked_at, latest if isinstance(latest, str) else None


def _write_state(data_folder: Path, checked_at: datetime, latest: str | None) -> None:
    try:
        data_folder.mkdir(parents=True, exist_ok=True)
        (data_folder / STATE_FILE_NAME).write_text(
            json.dumps({"checked_at": checked_at.isoformat(), "latest_version": latest}), encoding="utf-8"
        )
    except OSError:
        # Cannot remember: the next launch just checks again.
        pass
