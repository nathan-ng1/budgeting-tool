"""The Dashboard process makes no network call (ADR-0008, Issue #251): the
launcher checks for updates and hands the answer in. A module that reaches for
an HTTP client or a raw socket does not belong in `dashboard`.
"""

import ast
from pathlib import Path

DASHBOARD = Path(__file__).resolve().parents[2] / "src" / "dashboard"

# `http.server` (serving) is fine; these are the ways of calling out.
NETWORK_MODULES = {
    "urllib.request",
    "http.client",
    "socket",
    "ssl",
    "ftplib",
    "smtplib",
    "poplib",
    "imaplib",
    "telnetlib",
    "xmlrpc.client",
    "requests",
    "httpx",
    "aiohttp",
    "websockets",
}


def imported_modules(path: Path) -> set[str]:
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return found


def test_no_dashboard_module_imports_a_way_of_calling_out():
    offenders = {
        str(path.relative_to(DASHBOARD)): sorted(imported_modules(path) & NETWORK_MODULES)
        for path in DASHBOARD.rglob("*.py")
    }

    assert {name: modules for name, modules in offenders.items() if modules} == {}
