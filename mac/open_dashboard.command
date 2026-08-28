#!/bin/bash
# Start the Dashboard and open it in Chrome - one double-click, no terminal
# needed. macOS counterpart to windows/open_dashboard.bat (issue #117).
# Serves on DASHBOARD_PORT from .env (8765 if unset), the same local server
# described in ADR-0008; nothing leaves this machine.
#
# Leave this window open while you use the Dashboard - closing it, or
# pressing Ctrl+C, stops the server.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR/.."
cd "$REPO_ROOT"

is_listening() {
    # $1 = port. True if something is already listening on 127.0.0.1:$1.
    (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null
    local result=$?
    exec 3>&- 2>/dev/null
    return $result
}

open_browser() {
    local url="http://127.0.0.1:$1"
    if [[ -d "/Applications/Google Chrome.app" ]]; then
        open -a "Google Chrome" "$url"
    else
        echo "Chrome was not found - opening in your default browser instead."
        open "$url"
    fi
}

check_update() {
    # Throttled (~24h), silent, best-effort - degrades to doing nothing at
    # all if gh isn't installed/authenticated or the state file was touched
    # recently, never an error (ADR-0019, mirroring issue #116 stories 19-22).
    command -v gh >/dev/null 2>&1 || exit 0
    gh auth status >/dev/null 2>&1 || exit 0

    local state_dir="$REPO_ROOT/.setup"
    local state_file="$state_dir/last_update_check.txt"
    mkdir -p "$state_dir" 2>/dev/null

    if [[ -f "$state_file" ]]; then
        local last_check_epoch now_epoch age_hours
        last_check_epoch="$(stat -f %m "$state_file" 2>/dev/null || echo 0)"
        now_epoch="$(date +%s)"
        age_hours=$(( (now_epoch - last_check_epoch) / 3600 ))
        if (( age_hours < 24 )); then
            exit 0
        fi
    fi

    # Touch the state file before the network call, not after - so a slow or
    # failed check still counts as "checked" and doesn't retry every launch.
    touch "$state_file" 2>/dev/null

    local latest_tag
    latest_tag="$(gh api "repos/nathan-ng1/budgeting-tool/releases/latest" --jq .tag_name 2>/dev/null)"
    [[ -z "$latest_tag" ]] && exit 0

    local local_version
    local_version="$(uv run python -m setup local-version 2>/dev/null)"
    [[ -z "$local_version" ]] && exit 0

    local new_version
    new_version="$(uv run python -m setup check-update --local "$local_version" --latest-tag "$latest_tag" 2>/dev/null)"
    [[ -z "$new_version" ]] && exit 0

    echo
    echo "Update available ($new_version) - run update.command to install it."
    exit 0
}

open_when_ready() {
    # $1 = port. Poll until it accepts a connection, then open the browser.
    # Polling rather than sleeping a fixed time: the first `uv run` of a
    # session can take a while.
    local deadline=$(( $(date +%s) + 60 ))
    while (( $(date +%s) < deadline )); do
        if is_listening "$1"; then
            open_browser "$1"
            exit 0
        fi
        sleep 0.25
    done
    echo "The Dashboard did not start within 60 seconds - not opening the browser."
    exit 1
}

# Re-entry: the browser is opened by a second, backgrounded invocation of
# this script, so the server can hold the foreground of this window.
if [[ "${1:-}" == "--open-when-ready" ]]; then
    open_when_ready "$2"
    exit $?
fi

# Re-entry: the update-availability check (ADR-0019) also runs as a second,
# detached invocation, so a slow/offline network call can never delay the
# server actually starting.
if [[ "${1:-}" == "--check-update" ]]; then
    check_update
    exit $?
fi

# Which port? DASHBOARD_PORT in .env wins, else the server's own default.
PORT=8765
if [[ -f ".env" ]]; then
    while IFS='=' read -r key value; do
        [[ "$key" == \#* || -z "$key" ]] && continue
        [[ "$key" == "DASHBOARD_PORT" ]] && PORT="$value"
    done < ".env"
fi

# The frontend is a build artefact and is gitignored, so a fresh clone has no
# page to serve. Say so here rather than letting the browser show the
# server's own build instructions.
if [[ ! -f "src/dashboard/static/index.html" ]]; then
    echo "The Dashboard frontend has not been built yet."
    echo
    echo "    cd frontend"
    echo "    npm install"
    echo "    npm run build"
    echo
    echo "Then run this again. Node.js 20+ is needed - see the README."
    echo
    read -n 1 -s -r -p "Press any key to close this window..."
    echo
    exit 1
fi

# Best-effort update-availability check (ADR-0019) - fired detached so it can
# never delay this launch; throttled and silent inside itself.
("$0" --check-update &) >/dev/null 2>&1

# Already serving? Then just open it rather than failing to bind.
if is_listening "$PORT"; then
    echo "The Dashboard is already running on port $PORT - opening it."
    open_browser "$PORT"
    exit 0
fi

# Open the browser once the server is actually accepting connections.
("$0" --open-when-ready "$PORT" &) >/dev/null 2>&1

echo "Starting the Dashboard on port $PORT..."
echo "Close this window or press Ctrl+C to stop it."
echo

uv run python -m dashboard
if [[ $? -ne 0 ]]; then
    echo
    echo "The Dashboard exited with an error - see above."
    read -n 1 -s -r -p "Press any key to close this window..."
    echo
    exit 1
fi
