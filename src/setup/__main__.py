"""CLI seam `setup.bat`/`update.bat`/`open_dashboard.bat` shell out to.

Each subcommand is thin orchestration (real file I/O, argument parsing) around
the tested pure functions in `setup.env_file` and `setup.version_check` - see
issue #116. Nothing here is pytest-covered; keep it that way by not growing
decision logic in this file, only plumbing.
"""

import argparse
import sys
import tomllib
from pathlib import Path

from setup.env_file import REQUIRED_KEYS, merge_env
from setup.version_check import check_update_available

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = REPO_ROOT / ".env"
ENV_EXAMPLE_PATH = REPO_ROOT / ".env.example"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"


def local_version() -> str:
    with open(PYPROJECT_PATH, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def cmd_local_version(_args: argparse.Namespace) -> int:
    print(local_version())
    return 0


def cmd_check_update(args: argparse.Namespace) -> int:
    result = check_update_available(args.local, args.latest_tag)
    if result.update_available:
        print(result.latest_version)
    return 0


def cmd_write_env(args: argparse.Namespace) -> int:
    values: dict[str, str] = {}
    for pair in args.values:
        key, _, value = pair.partition("=")
        values[key] = value

    if ENV_PATH.exists():
        existing_content = ENV_PATH.read_text(encoding="utf-8")
    elif ENV_EXAMPLE_PATH.exists():
        existing_content = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    else:
        existing_content = ""

    required = tuple(args.required) if args.required else REQUIRED_KEYS
    result = merge_env(existing_content, values, required)

    ENV_PATH.write_text(result.content, encoding="utf-8")

    for key in result.missing_required:
        print(f"MISSING {key}")

    return 1 if result.missing_required else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m setup")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("local-version", help="Print the installed version from pyproject.toml").set_defaults(
        func=cmd_local_version
    )

    check_update = subparsers.add_parser(
        "check-update", help="Print the latest version if it's newer than --local, else print nothing"
    )
    check_update.add_argument("--local", required=True, help="Installed version, e.g. 0.3.0")
    check_update.add_argument("--latest-tag", default=None, help="Latest Release tag, e.g. v0.4.0 (omit if unknown)")
    check_update.set_defaults(func=cmd_check_update)

    write_env = subparsers.add_parser(
        "write-env", help="Merge values into .env (or .env.example if .env doesn't exist yet) and write .env"
    )
    write_env.add_argument("--values", nargs="*", default=[], metavar="KEY=VALUE", help="Values to set")
    write_env.add_argument(
        "--required", nargs="*", default=None, metavar="KEY", help="Keys to report as MISSING if left unset"
    )
    write_env.set_defaults(func=cmd_write_env)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
