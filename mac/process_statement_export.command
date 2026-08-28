#!/bin/bash
# Run the full Statement Export process: sanitise anything in the
# Transactions Inbox, then categorise and write it to the Transaction Log via
# whichever backend is configured (CATEGORISER_BACKEND in .env - claude,
# codex, or openai-compatible). Pass --dry-run to preview without writing.
# macOS counterpart to windows/process_statement_export.bat (issue #117).
# See docs/agents/statement-export-pipeline.md for the full walkthrough.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "Sanitising exports from the Transactions Inbox..."
uv run python -m sanitising
if [[ $? -ne 0 ]]; then
    echo "Sanitising failed - aborting."
    read -n 1 -s -r -p "Press any key to close this window..."
    echo
    exit 1
fi

echo
echo "Processing the sanitised export..."
uv run python -m statement_export "$@"
if [[ $? -ne 0 ]]; then
    echo "Processing failed for one or more files - see above."
    read -n 1 -s -r -p "Press any key to close this window..."
    echo
    exit 1
fi

read -n 1 -s -r -p "Press any key to close this window..."
echo
