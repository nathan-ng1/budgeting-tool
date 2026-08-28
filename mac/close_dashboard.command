#!/bin/bash
# Stop whatever Dashboard server is currently running - one double-click, no
# terminal needed. macOS counterpart to windows/close_dashboard.bat
# (issue #117). Finds the process listening on DASHBOARD_PORT (from .env,
# 8765 if unset) and ends it, so a restart after a code change actually
# picks up the new code instead of silently still serving the old one.
#
# This is a hard stop (kill -9), not a graceful shutdown - fine for local
# use, since every write already commits immediately (see database.store).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

PORT=8765
if [[ -f ".env" ]]; then
    while IFS='=' read -r key value; do
        [[ "$key" == \#* || -z "$key" ]] && continue
        [[ "$key" == "DASHBOARD_PORT" ]] && PORT="$value"
    done < ".env"
fi

echo "Looking for a Dashboard server on port $PORT..."

PIDS="$(lsof -ti ":$PORT" -sTCP:LISTEN 2>/dev/null)"
if [[ -z "$PIDS" ]]; then
    echo "Nothing is listening on port $PORT - the Dashboard is not running."
    read -n 1 -s -r -p "Press any key to close this window..."
    echo
    exit 0
fi

for pid in $PIDS; do
    echo "Stopping process $pid..."
    kill -9 "$pid" 2>/dev/null
done

echo "Dashboard on port $PORT stopped."
read -n 1 -s -r -p "Press any key to close this window..."
echo
