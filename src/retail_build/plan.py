"""What goes into the Retail build, and the Nuitka command that compiles it.

The Retail Edition is an explicit allowlist (decision S11, ADR-0033): the
shared packages plus the Dashboard are named here, so a package added to `src/`
is left out of the build until someone adds it. The Collaborator-only packages
are also passed to Nuitka as "never follow", so an import that slipped into
shared code could not pull one in unnoticed.
"""

import re
import sys
from pathlib import Path

APP_NAME = "BudgetingTool"
MAIN_SCRIPT_NAME = "retail_app.py"

# Everything the Dashboard and the launcher need, and nothing else.
SHARED_PACKAGES = (
    "dashboard",
    "database",
    "goals",
    "launcher",
    "migration",
    "recurring",
    "setup",
    "transaction_log",
)

COLLABORATOR_ONLY_PACKAGES = (
    "statement_export",
    "categorisation",
    "sanitising",
    "advisor",
    "budget_suggestions",
    "beem",
)

# Top-level names under `src/` that are neither shipped nor Collaborator-only.
BUILD_TOOLING = ("retail_build",)

# The built frontend and the baked-in Version, relative to `src/`; both are
# produced before the compile (`npm run build`, `python -m dashboard.build_info`).
STATIC_DIR = Path("dashboard") / "static"
BUILD_INFO_FILE = Path("dashboard") / "build_info.json"


def dist_dir(output_dir: Path) -> Path:
    """The folder Nuitka's standalone mode writes the app to."""
    return output_dir / f"{Path(MAIN_SCRIPT_NAME).stem}.dist"


def executable_path(output_dir: Path, platform: str = sys.platform) -> Path:
    suffix = ".exe" if platform == "win32" else ""
    return dist_dir(output_dir) / f"{APP_NAME}{suffix}"


def windows_version(version: str) -> str:
    """`0.6.0` as the four-part number Windows file properties need (`0.6.0.0`)."""
    parts = re.match(r"^(\d+)\.(\d+)\.(\d+)", version)
    if parts is None:
        raise ValueError(f"Not a Version of the form X.Y.Z: {version!r}")
    return ".".join(parts.groups()) + ".0"


def nuitka_args(
    *,
    src: Path,
    output_dir: Path,
    version: str,
    platform: str = sys.platform,
    report: Path | None = None,
) -> list[str]:
    """The arguments to `python -m nuitka` for a standalone (never onefile) build."""
    args = [
        "--standalone",
        f"--output-dir={output_dir}",
        f"--output-filename={APP_NAME}",
        "--enable-plugin=tk-inter",
        "--assume-yes-for-downloads",
        "--lto=no",
        "--remove-output",
        f"--include-data-dir={src / STATIC_DIR}={STATIC_DIR.as_posix()}",
        f"--include-data-files={src / BUILD_INFO_FILE}={BUILD_INFO_FILE.as_posix()}",
    ]
    args += [f"--include-package={package}" for package in SHARED_PACKAGES]
    args += [f"--nofollow-import-to={package}" for package in COLLABORATOR_ONLY_PACKAGES]
    if platform == "win32":
        args += [
            "--windows-console-mode=disable",
            "--product-name=Budgeting Tool",
            "--file-description=Budgeting Tool",
            f"--product-version={windows_version(version)}",
            f"--file-version={windows_version(version)}",
        ]
    if report is not None:
        args.append(f"--report={report}")
    args.append(str(src / MAIN_SCRIPT_NAME))
    return args
