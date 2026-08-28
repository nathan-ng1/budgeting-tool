#!/bin/bash
# Regenerate the standing Budget Suggestion write-up - one double-click, no
# terminal needed. Pulls recent Expense/Debt Budgeted vs Actual history and
# analyses it via whichever backend is configured (ADVISOR_BACKEND in .env -
# claude, codex, or openai-compatible), replacing whatever write-up was
# stored before - one standing document, no history kept (ADR-0014: a
# scripted flow, not a live Dashboard call). macOS counterpart to
# windows/generate_budget_suggestion.bat (issue #117).
#
# Refresh the Dashboard's Budget tab afterwards to see the new write-up.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "Regenerating the Budget Suggestion..."
uv run python -m budget_suggestions
if [[ $? -ne 0 ]]; then
    echo "Budget Suggestion generation failed - see above."
    read -n 1 -s -r -p "Press any key to close this window..."
    echo
    exit 1
fi

read -n 1 -s -r -p "Press any key to close this window..."
echo
