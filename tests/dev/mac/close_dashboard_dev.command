#!/bin/bash
# Stop whatever Dashboard DEV environment is currently running - the backend
# and the frontend's Vite dev server started by open_dashboard_dev.command.
# One double-click, no terminal needed. Finds whatever is listening on the
# backend port (DASHBOARD_PORT from .env, 8765 if unset) and Vite's default
# dev port (5173) and ends both, so a restart after a code change actually
# picks up the new code. macOS counterpart to
# tests/dev/windows/close_dashboard_dev.bat (issue #117).
#
# This is a hard stop (kill -9), not a graceful shutdown - fine for local dev
# use, since every write already commits immediately (see database.store).
# Doesn't touch open_dashboard.command's built-dashboard server - that's
# close_dashboard.command's job.
#
# If Vite had to pick a different port than 5173 (because something else was
# already using it), this won't find that process - close its Terminal
# window by hand.
#
# Lives under tests/dev/mac/, alongside open_dashboard_dev.command - see that
# file's header for why.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../../.."

stop_port() {
    # $1 = port, $2 = label for messages. Returns 2 if nothing was listening
    # there, 0 otherwise (mirrors close_dashboard.command's convention).
    echo "Looking for the $2 on port $1..."
    local pids
    pids="$(lsof -ti ":$1" -sTCP:LISTEN 2>/dev/null)"
    if [[ -z "$pids" ]]; then
        return 2
    fi
    for pid in $pids; do
        echo "Stopping process $pid..."
        kill -9 "$pid" 2>/dev/null
    done
    echo "$2 on port $1 stopped."
    return 0
}

BACKEND_PORT=8765
if [[ -f ".env" ]]; then
    while IFS='=' read -r key value; do
        [[ "$key" == \#* || -z "$key" ]] && continue
        [[ "$key" == "DASHBOARD_PORT" ]] && BACKEND_PORT="$value"
    done < ".env"
fi
FRONTEND_PORT=5173

stop_port "$BACKEND_PORT" "backend"
stopped_backend=$?

stop_port "$FRONTEND_PORT" "frontend dev server"
stopped_frontend=$?

if [[ $stopped_backend -eq 2 && $stopped_frontend -eq 2 ]]; then
    echo "Nothing is listening on port $BACKEND_PORT or $FRONTEND_PORT - the dev"
    echo "environment is not running."
fi

read -n 1 -s -r -p "Press any key to close this window..."
echo
