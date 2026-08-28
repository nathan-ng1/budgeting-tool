#!/bin/bash
# Start the Dashboard's DEV environment - the backend (uv run python -m
# dashboard, against your real local database) plus the frontend's Vite dev
# server (hot reload, proxying /api to that backend) - and open it in Chrome.
# One double-click, no terminal needed. Unlike open_dashboard.command, this
# doesn't need `npm run build` first: edits under frontend/src show up in the
# browser immediately. macOS counterpart to
# tests/dev/windows/open_dashboard_dev.bat (issue #117).
#
# Opens two Terminal windows, one per server, via osascript. Closing either
# stops that server; use close_dashboard_dev.command to stop both at once.
#
# Lives under tests/dev/mac/, not the repo root - this is a manual
# frontend-dev convenience script, not part of the guided end-user path (see
# docs/dashboard-guide.html for that). REPO_ROOT below resolves three levels
# up from this file's own location so it still works from wherever it's
# double-clicked.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$REPO_ROOT"

is_listening() {
    (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null
    local result=$?
    exec 3>&- 2>/dev/null
    return $result
}

open_browser() {
    local url="http://localhost:$1"
    if [[ -d "/Applications/Google Chrome.app" ]]; then
        open -a "Google Chrome" "$url"
    else
        echo "Chrome was not found - opening in your default browser instead."
        open "$url"
    fi
}

# Re-entry: the browser is opened by a second copy of this script, once the
# frontend dev server is actually accepting connections.
if [[ "${1:-}" == "--open-when-ready" ]]; then
    deadline=$(( $(date +%s) + 60 ))
    while (( $(date +%s) < deadline )); do
        if is_listening "$2"; then
            open_browser "$2"
            exit 0
        fi
        sleep 0.25
    done
    echo "The frontend dev server did not come up on port $2 within 60"
    echo "seconds - check its Terminal window; if port $2 was busy, Vite may"
    echo "have picked a different port to serve on instead."
    exit 1
fi

# Backend port: DASHBOARD_PORT in .env wins, else 8765 - same lookup
# open_dashboard.command uses. The frontend dev server's proxy
# (frontend/vite.config.js) always targets 127.0.0.1:8765, so warn rather
# than silently break the proxy if .env asks for a different port.
BACKEND_PORT=8765
if [[ -f ".env" ]]; then
    while IFS='=' read -r key value; do
        [[ "$key" == \#* || -z "$key" ]] && continue
        [[ "$key" == "DASHBOARD_PORT" ]] && BACKEND_PORT="$value"
    done < ".env"
fi
if [[ "$BACKEND_PORT" != "8765" ]]; then
    echo "Warning: DASHBOARD_PORT is set to $BACKEND_PORT in .env, but the"
    echo "frontend dev server's proxy always targets 127.0.0.1:8765"
    echo "(frontend/vite.config.js). The dev environment won't talk to itself"
    echo "correctly until one of those is changed to match the other."
    echo
fi

FRONTEND_PORT=5173

if [[ ! -d "frontend/node_modules" ]]; then
    echo "The frontend's dependencies have not been installed yet."
    echo
    echo "    cd frontend"
    echo "    npm install"
    echo
    echo "Then run this again. Node.js 20+ is needed - see the README."
    echo
    read -n 1 -s -r -p "Press any key to close this window..."
    echo
    exit 1
fi

if is_listening "$FRONTEND_PORT"; then
    echo "The frontend dev server is already running on port $FRONTEND_PORT - opening it."
    open_browser "$FRONTEND_PORT"
    exit 0
fi

if is_listening "$BACKEND_PORT"; then
    echo "A server is already listening on port $BACKEND_PORT - assuming it's the"
    echo "Dashboard backend and leaving it running."
else
    echo "Starting the Dashboard backend on port $BACKEND_PORT..."
    osascript -e "tell application \"Terminal\" to do script \"cd '$REPO_ROOT' && uv run python -m dashboard\""
fi

echo "Starting the frontend dev server on port $FRONTEND_PORT..."
osascript -e "tell application \"Terminal\" to do script \"cd '$REPO_ROOT/frontend' && npm run dev\""

("$0" --open-when-ready "$FRONTEND_PORT" &) >/dev/null 2>&1

echo
echo "Two Terminal windows just opened: backend and frontend dev server. Close"
echo "either to stop that one, or run close_dashboard_dev.command to stop"
echo "both at once."
echo
