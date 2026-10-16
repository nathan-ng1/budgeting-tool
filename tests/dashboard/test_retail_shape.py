"""The Dashboard must run without the Collaborator-only packages (Retail
Edition spec #236, decision S1): shared code never imports them, so the Retail
build can leave them out.

The check imports the Dashboard in a fresh interpreter in which those packages
are unimportable - the same shape as the compiled Retail build.
"""

import os
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"

COLLABORATOR_ONLY_PACKAGES = (
    "statement_export",
    "categorisation",
    "sanitising",
    "advisor",
    "budget_suggestions",
    "beem",
)

SCRIPT = f"""
import sys

BLOCKED = {COLLABORATOR_ONLY_PACKAGES!r}


class Blocker:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in BLOCKED:
            raise ImportError(f"Collaborator-only package imported: {{name}}")
        return None


sys.meta_path.insert(0, Blocker())

import dashboard.__main__
import dashboard.server
import database.store
import migration.runner
"""


def test_dashboard_imports_without_the_collaborator_only_packages():
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT],
        env={**os.environ, "PYTHONPATH": str(SRC)},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
