#!/bin/bash
# Explicit, manually-run update step (ADR-0019) - the macOS counterpart to
# windows/update.bat (issue #117). Fetches tags, shows what's changed since
# your installed version, confirms, then pulls and re-syncs dependencies.
# Never reconfigures .env or switches AI path - that stays setup.command's
# job (re-run it instead).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

press_any_key() {
    read -n 1 -s -r -p "Press any key to close this window..."
    echo
}

if [[ ! -d ".git" ]]; then
    echo "This isn't a clone of the repo - run update.command from inside it,"
    echo "or use setup.command if you haven't installed yet."
    press_any_key
    exit 1
fi

echo "Fetching the latest tags..."
git fetch --tags --quiet
if [[ $? -ne 0 ]]; then
    echo "Couldn't reach the repo - check your internet connection and that"
    echo "'gh auth status' is still logged in, then try again."
    press_any_key
    exit 1
fi

LATEST_TAG="$(git tag --sort=-v:refname | head -n 1)"
if [[ -z "$LATEST_TAG" ]]; then
    echo "No Release tags found yet - nothing to update to."
    press_any_key
    exit 0
fi

LOCAL_VERSION="$(uv run python -m setup local-version)"
NEW_VERSION="$(uv run python -m setup check-update --local "$LOCAL_VERSION" --latest-tag "$LATEST_TAG")"

if [[ -z "$NEW_VERSION" ]]; then
    echo "You're already on the latest version ($LOCAL_VERSION)."
    press_any_key
    exit 0
fi

echo
echo "Installed version: $LOCAL_VERSION"
echo "Latest version:    $NEW_VERSION"
echo
echo "What's new:"
git log --oneline "HEAD..$LATEST_TAG"
echo

read -r -p "Update now? [Y/n] " confirm
if [[ "${confirm,,}" == "n" ]]; then
    echo "No changes made."
    exit 0
fi

# Don't clobber local work - same git-safety norm as everywhere else in this
# repo: surface a conflict rather than silently discarding it.
if [[ -n "$(git status --porcelain)" ]]; then
    echo
    echo "You have uncommitted local changes:"
    git status --short
    echo
    echo "Commit or stash them first, then re-run update.command."
    press_any_key
    exit 1
fi

echo
echo "Pulling latest changes..."
git pull --ff-only
if [[ $? -ne 0 ]]; then
    echo
    echo "git pull couldn't fast-forward - your local branch has diverged from"
    echo "origin. Resolve that by hand (see the README's git-safety norms),"
    echo "then re-run update.command."
    press_any_key
    exit 1
fi

echo
echo "Re-syncing Python dependencies..."
uv sync
if [[ $? -ne 0 ]]; then
    echo "uv sync failed - see above."
    press_any_key
    exit 1
fi

if [[ -f "src/dashboard/static/index.html" ]]; then
    echo
    echo "Re-syncing the Dashboard frontend..."
    (
        cd frontend
        npm install && npm run build
    )
    if [[ $? -ne 0 ]]; then
        echo "Rebuilding the frontend failed - see above."
        press_any_key
        exit 1
    fi
fi

echo
echo "Updated to $NEW_VERSION."
press_any_key
exit 0
