"""Where the Database lives - the one resolver every entry point uses (Issue #238,
ADR-0032; partly supersedes ADR-0030).

Order, first match wins:

1. an override: the `DATABASE_PATH` environment variable, or `DATABASE_PATH` in
   the repo-root `.env` (the Collaborator Edition's setting; nothing else is
   consulted when it is set);
2. the pointer file in the per-user data folder, which "Change location..."
   writes when there is no override;
3. the Database file in the default per-user data folder.

An unreadable or invalid pointer is ignored, so a damaged or stale pointer
degrades to the default folder rather than stopping the app.
"""

import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = REPO_ROOT / ".env"

APP_FOLDER_NAME = "Budgeting Tool"
DEFAULT_DATABASE_NAME = "budget.db"
POINTER_FILE_NAME = "database-location.txt"

SOURCE_OVERRIDE = "override"
SOURCE_POINTER = "pointer"
SOURCE_DEFAULT = "default"


@dataclass(frozen=True)
class DatabaseLocation:
    path: Path
    source: str  # SOURCE_OVERRIDE, SOURCE_POINTER or SOURCE_DEFAULT


def default_data_folder(
    *, platform: str = sys.platform, environ: Mapping[str, str] = os.environ, home: Path | None = None
) -> Path:
    """The per-user folder for the app's data: Windows local app data, macOS
    Application Support (and the XDG data folder elsewhere)."""
    home = Path.home() if home is None else home
    if platform == "win32":
        base = Path(environ.get("LOCALAPPDATA") or home / "AppData" / "Local")
    elif platform == "darwin":
        base = home / "Library" / "Application Support"
    else:
        base = Path(environ.get("XDG_DATA_HOME") or home / ".local" / "share")
    return base / APP_FOLDER_NAME


def resolve_location(
    *,
    env_path: Path | None = None,
    data_folder: Path | None = None,
    environ: Mapping[str, str] = os.environ,
) -> DatabaseLocation:
    override = _override(ENV_PATH if env_path is None else env_path, environ)
    if override is not None:
        return DatabaseLocation(Path(override), SOURCE_OVERRIDE)

    data_folder = default_data_folder() if data_folder is None else data_folder
    pointed = _read_pointer(data_folder)
    if pointed is not None:
        return DatabaseLocation(pointed, SOURCE_POINTER)

    return DatabaseLocation(data_folder / DEFAULT_DATABASE_NAME, SOURCE_DEFAULT)


def resolve_database_path(
    database_path: Path | None = None,
    *,
    env_path: Path | None = None,
    data_folder: Path | None = None,
    environ: Mapping[str, str] = os.environ,
) -> Path:
    """`database_path` if given, else wherever `resolve_location` says."""
    if database_path is not None:
        return database_path
    return resolve_location(env_path=env_path, data_folder=data_folder, environ=environ).path


def write_pointer(data_folder: Path, database_file: Path) -> None:
    """Record `database_file` as the Database's location. Replaced via a
    temporary file so a failure partway leaves the old pointer as it was."""
    data_folder.mkdir(parents=True, exist_ok=True)
    pointer = data_folder / POINTER_FILE_NAME
    temporary = pointer.with_name(pointer.name + ".tmp")
    try:
        temporary.write_text(f"{database_file}\n", encoding="utf-8")
        os.replace(temporary, pointer)
    finally:
        temporary.unlink(missing_ok=True)


def _override(env_path: Path, environ: Mapping[str, str]) -> str | None:
    value = environ.get("DATABASE_PATH")
    if value is None or not value.strip():
        value = dotenv_values(env_path).get("DATABASE_PATH")
    return value.strip() if value and value.strip() else None


def _read_pointer(data_folder: Path) -> Path | None:
    """The Database file the pointer names, or None if there is no usable one:
    unreadable, blank, not absolute, a folder, or in a folder that isn't there."""
    try:
        text = (data_folder / POINTER_FILE_NAME).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return None
    if not text:
        return None
    pointed = Path(text)
    if not pointed.is_absolute() or pointed.is_dir() or not pointed.parent.is_dir():
        return None
    return pointed
