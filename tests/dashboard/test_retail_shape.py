"""The Dashboard must run without the Collaborator-only packages (Retail
Edition spec #236, decision S1): shared code never imports them, so the Retail
build can leave them out.

The check imports the Dashboard in a fresh interpreter in which those packages
are unimportable - the same shape as the compiled Retail build.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from retail_build.plan import COLLABORATOR_ONLY_PACKAGES

SRC = Path(__file__).resolve().parents[2] / "src"

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
import launcher.launch
import migration.runner
"""

# Serves the real Dashboard over a temporary Database in the same blocked
# interpreter and prints the status of each tab's API, plus the capabilities
# the frontend would read (Issue #248).
SERVE_SCRIPT = f"""
{SCRIPT}
import json
import threading
from urllib.error import HTTPError
from urllib.request import urlopen

from dashboard.server import build_server

PATHS = {{
    "Overview": "/api/overview?year=2026&month=8",
    "Annual overview": "/api/annual-overview?year=2026&period=financial",
    "Transactions": "/api/transactions?year=2026&month=8",
    "Budget editor": "/api/budget-editor?year=2026&month=8",
    "Budget grid": "/api/budget-grid?year=2026&period=financial",
    "Budget Suggestion": "/api/budget-suggestion",
    "Goals": "/api/goals",
    "Categories": "/api/categories",
    "Settings": "/api/settings",
    "Recurring rules": "/api/recurring-rules",
    "Recurring due": "/api/recurring-rules/due",
    "Version": "/api/version",
    "Capabilities": "/api/capabilities",
}}

server = build_server(database.store.connect(__import__("pathlib").Path(sys.argv[1])))
threading.Thread(target=server.serve_forever, daemon=True).start()

statuses, capabilities = {{}}, None
for tab, path in PATHS.items():
    try:
        with urlopen(f"http://127.0.0.1:{{server.server_port}}{{path}}") as response:
            statuses[tab] = response.status
            if tab == "Capabilities":
                capabilities = json.loads(response.read())
    except HTTPError as error:
        statuses[tab] = error.code

print(json.dumps({{"statuses": statuses, "capabilities": capabilities}}))
server.shutdown()
"""


def run_blocked(script: str, *args: str):
    return subprocess.run(
        [sys.executable, "-c", script, *args],
        env={**os.environ, "PYTHONPATH": str(SRC)},
        capture_output=True,
        text=True,
    )


def test_dashboard_imports_without_the_collaborator_only_packages():
    result = run_blocked(SCRIPT)

    assert result.returncode == 0, result.stderr


def test_every_tabs_api_still_responds_and_the_collaborator_only_features_report_absent(tmp_path):
    result = run_blocked(SERVE_SCRIPT, str(tmp_path / "budget.db"))

    assert result.returncode == 0, result.stderr
    served = json.loads(result.stdout)
    assert served["capabilities"] == {"budget_suggestion": False, "statement_export": False}
    # The Budget Suggestion endpoint is the one thing not served; every other
    # tab's API answers as it does in the Collaborator Edition.
    assert {tab: status for tab, status in served["statuses"].items() if status != 200} == {"Budget Suggestion": 404}
