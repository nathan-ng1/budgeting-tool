"""Checks on a finished Retail build that don't need to run it (Issue #252).

The smoke test shows the app *behaves* like a Retail build; this shows what is
*in* it. Nuitka's compilation report lists every module compiled in, so a
Collaborator-only package that got bundled shows up there even if nothing
imports it at run time.
"""

import xml.etree.ElementTree as ElementTree
from pathlib import Path

from retail_build.plan import BUILD_INFO_FILE, COLLABORATOR_ONLY_PACKAGES, STATIC_DIR


def bundled_modules(report: Path) -> set[str]:
    """Every module name in a Nuitka compilation report."""
    root = ElementTree.parse(report).getroot()
    return {module.get("name", "") for module in root.iter("module")}


def problems(report: Path, dist: Path) -> list[str]:
    """What is wrong with the build in `dist`, as plain sentences; empty if nothing."""
    modules = bundled_modules(report)
    if not modules:
        # An unreadable report would otherwise pass every check below.
        return [f"{report} lists no modules"]

    found: list[str] = []
    for package in COLLABORATOR_ONLY_PACKAGES:
        leaked = sorted(name for name in modules if name == package or name.startswith(f"{package}."))
        if leaked:
            found.append(f"Collaborator-only package {package} is compiled in ({', '.join(leaked[:3])})")
        if (dist / package).exists():
            found.append(f"Collaborator-only package {package} is in the build folder")

    for required in (STATIC_DIR / "index.html", BUILD_INFO_FILE):
        if not (dist / required).is_file():
            found.append(f"{required.as_posix()} is missing from the build folder")
    return found
