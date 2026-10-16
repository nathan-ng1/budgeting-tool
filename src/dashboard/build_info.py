"""`build_info.json`: the Version and Version History baked in at build time.

A compiled build has no clone to read `CHANGELOG.md` from and no package
metadata to read the Version from, so the build step (`python -m
dashboard.build_info`) writes both into one file beside the Dashboard. When
that file is present the backend serves from it instead (server.py). Bullets
under the changelog's `### Collaborator Edition only` sub-heading are left out,
so a Buyer never sees them.

A file that is present but unreadable or the wrong shape reads as None, and
the Dashboard then shows its "isn't available" message rather than breaking.
"""

import argparse
import json
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as installed_version
from pathlib import Path

from dashboard.changelog import read_history, without_collaborator_only

REPO_ROOT = Path(__file__).resolve().parents[2]
CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"
BUILD_INFO_PATH = Path(__file__).resolve().parent / "build_info.json"


def package_version() -> str | None:
    """The installed package's version (the `pyproject.toml` one), or None if it isn't installed."""
    try:
        return installed_version("budgeting-tool")
    except PackageNotFoundError:
        return None


def write_build_info(changelog_path: Path, output_path: Path, version: str) -> None:
    """Write `version` and the changelog's history, minus Collaborator-only items, to `output_path`.

    Raises ValueError, writing nothing, if the changelog is missing or malformed:
    a build must not ship with a silently empty Version History.
    """
    history = read_history(changelog_path)
    if history is None:
        raise ValueError(f"{changelog_path} is missing or malformed")
    info = {"version": version, "history": without_collaborator_only(history)}
    output_path.write_text(json.dumps(info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_build_info(path: Path) -> dict | None:
    """`{"version", "history"}` from `path`, or None if it is unreadable or the wrong shape."""
    try:
        info = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    if not _is_build_info(info):
        return None
    return {"version": info["version"], "history": info["history"]}


def _is_build_info(info) -> bool:
    return (
        isinstance(info, dict)
        and isinstance(info.get("version"), str)
        and isinstance(info.get("history"), list)
        and all(_is_version(entry) for entry in info["history"])
    )


def _is_version(entry) -> bool:
    return (
        isinstance(entry, dict)
        and isinstance(entry.get("version"), str)
        and isinstance(entry.get("date"), str)
        and _is_text_list(entry.get("entries"))
        and isinstance(entry.get("groups"), list)
        and all(
            isinstance(group, dict) and isinstance(group.get("title"), str) and _is_text_list(group.get("entries"))
            for group in entry["groups"]
        )
    )


def _is_text_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Write build_info.json for a compiled build.")
    parser.add_argument("--changelog", type=Path, default=CHANGELOG_PATH)
    parser.add_argument("--output", type=Path, default=BUILD_INFO_PATH)
    parser.add_argument("--version", default=None, help="defaults to the installed package's version")
    args = parser.parse_args()

    version = args.version or package_version()
    if version is None:
        raise SystemExit("budgeting-tool isn't installed, so its version is unknown; pass --version.")
    try:
        write_build_info(args.changelog, args.output, version)
    except ValueError as error:
        raise SystemExit(str(error))
    print(f"Wrote {args.output} (v{version})")


if __name__ == "__main__":
    main()
