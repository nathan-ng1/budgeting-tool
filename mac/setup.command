#!/bin/bash
# Installation Pack bootstrapper (ADR-0017/0018) - macOS counterpart to
# windows/setup.bat (issue #117). Installs prerequisites via Homebrew, clones
# the repo, configures .env, and builds the Dashboard frontend.
#
# Standalone by design: this file is meant to be downloaded on its own from a
# GitHub Release and double-clicked before Git, Homebrew, or a clone exist -
# so it can't assume anything about the folder it's run from. It's also safe
# to re-run from inside an existing clone: that's both the "fix a partial
# install" path and the "Dashboard-only user adding the AI path later" path
# (ADR-0017's idempotency requirement, mirroring issue #116 stories 4 and 13).
#
# First run needs a Gatekeeper step Windows has no equivalent of: right-click
# this file in Finder and choose Open (or `xattr -d com.apple.quarantine
# setup.command`) before double-clicking will work - see
# docs/setup-guide-mac.html for the guided walkthrough this script backs.

set -uo pipefail

# Finder runs a double-clicked .command file with the shell's cwd set to
# $HOME, not this file's own folder - unlike Windows' %~dp0, so every step
# below that needs "where this script lives" resolves it explicitly.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

REPO_OWNER="nathan-ng1"
REPO_NAME="budgeting-tool"

press_any_key() {
    read -n 1 -s -r -p "Press any key to close this window..."
    echo
}

echo "==============================================="
echo " Budgeting Tool - Installation Pack setup (macOS)"
echo "==============================================="
echo

refresh_path() {
    # A freshly-installed Homebrew (or anything it just installed) isn't on
    # this already-running shell's PATH yet - brew's shellenv is only sourced
    # by new shells via .zprofile. Without this, a tool installed moments ago
    # would still look "not found" for the rest of this run (mirrors
    # windows/setup.bat's :refresh_path, same underlying problem).
    if [[ -x /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -x /usr/local/bin/brew ]]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
}
refresh_path

ensure_homebrew() {
    if command -v brew >/dev/null 2>&1; then
        echo "[ok] Homebrew is already installed."
        return 0
    fi

    echo
    echo "Homebrew was not found. It's needed to install this tool's other"
    echo "prerequisites (Git, uv, Node.js, GitHub CLI)."
    read -r -p "Install Homebrew now? [Y/n] " confirm
    if [[ "$confirm" == [Nn] ]]; then
        echo "Skipping Homebrew. Setup can't continue without it - install it"
        echo "yourself (https://brew.sh) and re-run this script when you're ready."
        press_any_key
        exit 1
    fi

    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    if [[ $? -ne 0 ]]; then
        echo "Installing Homebrew failed. Try manually: https://brew.sh"
        press_any_key
        exit 1
    fi

    refresh_path
    if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew installed, but this shell still can't see it on PATH."
        echo "Close this window, open a new one, and re-run this script."
        press_any_key
        exit 1
    fi
    echo "Homebrew installed."
}

# ensure_prereq "<display name>" <command-to-check> <brew-formula> <manual-url>
ensure_prereq() {
    local display_name="$1" check_cmd="$2" formula="$3" manual_url="$4"

    if command -v "$check_cmd" >/dev/null 2>&1; then
        echo "[ok] $display_name is already installed."
        return 0
    fi

    echo
    echo "$display_name was not found."
    read -r -p "Install $display_name now via Homebrew? [Y/n] " confirm
    if [[ "$confirm" == [Nn] ]]; then
        echo "Skipping $display_name. Setup can't continue without it - install it"
        echo "yourself ($manual_url) and re-run this script when you're ready."
        press_any_key
        exit 1
    fi

    echo "Installing $display_name..."
    brew install "$formula"
    if [[ $? -ne 0 ]]; then
        echo "Installing $display_name via Homebrew failed. Try manually: $manual_url"
        press_any_key
        exit 1
    fi

    refresh_path
    if ! command -v "$check_cmd" >/dev/null 2>&1; then
        echo "$display_name installed, but this shell still can't see it on PATH."
        echo "Close this window, open a new one, and re-run this script."
        press_any_key
        exit 1
    fi
    echo "$display_name installed."
}

ensure_python() {
    # Deliberately not `brew install python@3.12` - Homebrew's Python formula
    # has a long-standing history of PATH/shimming friction. uv provisions a
    # matching interpreter itself (its default managed-Python behaviour) the
    # first time `uv sync` runs below, so there's nothing to confirm here
    # beyond making sure uv itself is present (already handled above).
    echo "[ok] Python 3.12+ will be provisioned automatically by uv if needed."
}

ensure_node() {
    # Node needs a version check, not just a presence check - a stale Node
    # <20 already on PATH shouldn't count as satisfying "20+" (mirrors
    # windows/setup.bat's :ensure_node; the frontend build needs 20+).
    if command -v node >/dev/null 2>&1; then
        if node -e "process.exit(parseInt(process.versions.node.split('.')[0], 10) >= 20 ? 0 : 1)" >/dev/null 2>&1; then
            echo "[ok] Node.js 20+ is already installed."
            return 0
        fi
    fi

    echo
    echo "Node.js 20+ was not found."
    read -r -p "Install Node.js now via Homebrew? [Y/n] " confirm
    if [[ "$confirm" == [Nn] ]]; then
        echo "Skipping Node.js. Setup can't continue without it - install it"
        echo "yourself (https://nodejs.org/) and re-run this script when you're ready."
        press_any_key
        exit 1
    fi

    echo "Installing Node.js..."
    brew install node
    if [[ $? -ne 0 ]]; then
        echo "Installing Node.js via Homebrew failed. Try manually: https://nodejs.org/"
        press_any_key
        exit 1
    fi

    refresh_path
    if ! node -e "process.exit(parseInt(process.versions.node.split('.')[0], 10) >= 20 ? 0 : 1)" >/dev/null 2>&1; then
        echo "Node.js installed, but this shell still can't see 20+ on PATH."
        echo "Close this window, open a new one, and re-run this script."
        press_any_key
        exit 1
    fi
    echo "Node.js installed."
}

ensure_gh_auth() {
    # gh moved from optional to required (ADR-0017) - both the initial clone
    # of this private repo and every update check depend on it being
    # authenticated.
    if gh auth status >/dev/null 2>&1; then
        echo "[ok] GitHub CLI is already logged in."
        return 0
    fi

    echo
    echo "GitHub CLI isn't logged in yet. This repo is private, so an"
    echo "authenticated account that's been added as a collaborator is"
    echo "required to continue."
    gh auth login
    if [[ $? -ne 0 ]]; then
        echo "GitHub CLI login did not complete. Re-run this script once you're logged in."
        exit 1
    fi

    if ! gh auth status >/dev/null 2>&1; then
        echo "Still not logged in - re-run this script once 'gh auth login' succeeds."
        exit 1
    fi
}

ensure_clone() {
    # Four cases: already inside a clone (re-run, or a pre-existing checkout -
    # mirrors issue #116 story 30); inside an existing checkout's mac/ folder
    # itself (re-running mac/setup.command from inside a clone, rather than a
    # standalone download - .git now lives one level up from this script, not
    # next to it, since the windows/mac split moved this script out of the
    # repo root; missing this case used to silently clone a redundant nested
    # copy and write .env/build the frontend there instead of the real repo
    # root); a partial clone sitting next to this script; or a clean
    # bootstrap that needs to clone from scratch.
    if [[ -d ".git" ]]; then
        echo "[ok] Already inside a clone of this repo."
        return 0
    fi

    if [[ -d "../.git" ]]; then
        echo "[ok] Already inside a clone of this repo (running from mac/)."
        cd ..
        return 0
    fi

    if [[ -d "$REPO_NAME" ]]; then
        if [[ -d "$REPO_NAME/.git" ]]; then
            echo "[ok] Found an existing clone in ./$REPO_NAME - continuing there."
            cd "$REPO_NAME"
            return 0
        fi
        echo "A folder named \"$REPO_NAME\" already exists here but isn't a git clone."
        echo "Rename or remove it, then re-run this script."
        press_any_key
        exit 1
    fi

    echo
    echo "Cloning $REPO_OWNER/$REPO_NAME..."
    gh repo clone "$REPO_OWNER/$REPO_NAME"
    if [[ $? -ne 0 ]]; then
        echo "Clone failed - check you've been added as a collaborator on this"
        echo "private repo, then re-run this script."
        press_any_key
        exit 1
    fi
    cd "$REPO_NAME"
}

AI_BACKEND=""

# ensure_npm_global "<display name>" <command-to-check> <npm-package>
ensure_npm_global() {
    local display_name="$1" check_cmd="$2" npm_package="$3"

    if command -v "$check_cmd" >/dev/null 2>&1; then
        echo "[ok] $display_name is already installed."
        return 0
    fi

    echo
    echo "$display_name was not found."
    read -r -p "Install $display_name now via npm? [Y/n] " confirm
    if [[ "$confirm" == [Nn] ]]; then
        echo "Skipping $display_name - install it yourself, then re-run this script."
        press_any_key
        exit 1
    fi

    npm install -g "$npm_package"
    if [[ $? -ne 0 ]]; then
        echo "Installing $display_name via npm failed - see above. If this is a"
        echo "permissions error, see npm's docs on configuring a user-writable"
        echo "global prefix rather than running this with sudo."
        press_any_key
        exit 1
    fi

    refresh_path
    if ! command -v "$check_cmd" >/dev/null 2>&1; then
        echo "$display_name installed, but this shell still can't see it on PATH."
        echo "Close this window, open a new one, and re-run this script."
        press_any_key
        exit 1
    fi
    echo "$display_name installed."
}

verify_claude_login() {
    # No non-interactive "am I logged in" flag ships with Claude Code, so this
    # probes with a trivial non-interactive prompt: a login-required failure
    # looks different from a successful (even empty) response.
    echo "Checking Claude Code login..."
    if claude -p "reply with the single word: ok" >/dev/null 2>&1; then
        echo "[ok] Claude Code is logged in."
        return 0
    fi

    while true; do
        echo
        echo "Claude Code doesn't look logged in yet. Run 'claude' in another window"
        echo "and complete the login flow, then come back here."
        press_any_key
        if claude -p "reply with the single word: ok" >/dev/null 2>&1; then
            echo "[ok] Claude Code is logged in."
            return 0
        fi
        echo "Still not logged in."
    done
}

verify_codex_login() {
    echo "Checking Codex CLI login..."
    if codex login status >/dev/null 2>&1; then
        echo "[ok] Codex CLI is logged in."
        return 0
    fi

    while true; do
        echo
        echo "Codex CLI doesn't look logged in yet. Run 'codex login' in another"
        echo "window and complete the login flow, then come back here."
        press_any_key
        if codex login status >/dev/null 2>&1; then
            echo "[ok] Codex CLI is logged in."
            return 0
        fi
        echo "Still not logged in."
    done
}

configure_ai_path() {
    # Sets AI_BACKEND to claude/codex, or leaves it empty for Dashboard-only
    # (ADR-0018) - configure_env below reads it to decide what goes in .env.
    echo
    read -r -p "Do you have a Claude Code or Codex CLI subscription? [y/N] " has_ai
    if [[ "$has_ai" != [Yy] ]]; then
        echo "Continuing on the Dashboard-only path. You can add AI categorisation"
        echo "later by re-running this script."
        return 0
    fi

    local which_ai
    while true; do
        read -r -p "Which one - (1) Claude Code or (2) Codex CLI? [1/2] " which_ai
        case "$which_ai" in
            1) AI_BACKEND="claude"; break ;;
            2) AI_BACKEND="codex"; break ;;
            *) echo "Please enter 1 or 2." ;;
        esac
    done

    if [[ "$AI_BACKEND" == "claude" ]]; then
        ensure_npm_global "Claude Code" claude "@anthropic-ai/claude-code"
        verify_claude_login
    else
        ensure_npm_global "Codex CLI" codex "@openai/codex"
        verify_codex_login
    fi
}

configure_env() {
    # Prompts for the per-person values, preserving whatever's already in
    # .env (or .env.example, on a first run) for anything the user doesn't
    # change - this is what makes a Dashboard-only user's later AI-path
    # re-run non-destructive (mirrors issue #116 story 13). The actual
    # merge/write is the tested seam (src/setup/env_file.py), invoked below
    # via write-env.
    echo
    echo "--- Configuring .env"

    local existing_inbox="" existing_db=""
    if [[ -f ".env" ]]; then
        while IFS='=' read -r key value; do
            [[ "$key" == \#* || -z "$key" ]] && continue
            case "$key" in
                TRANSACTIONS_INBOX) existing_inbox="$value" ;;
                DATABASE_PATH) existing_db="$value" ;;
            esac
        done < ".env"
    fi

    local transactions_inbox="" database_path=""
    if [[ -n "$existing_inbox" && -n "$existing_db" ]]; then
        echo "Already configured:"
        echo "  TRANSACTIONS_INBOX=$existing_inbox"
        echo "  DATABASE_PATH=$existing_db"
        read -r -p "Change these? [y/N] " reconfigure
        if [[ "$reconfigure" != [Yy] ]]; then
            transactions_inbox="$existing_inbox"
            database_path="$existing_db"
        fi
    fi

    if [[ -z "$transactions_inbox" ]]; then
        local suggested_inbox="${existing_inbox:-$HOME/Documents/Transactions}"
        read -r -p "Transactions Inbox folder [$suggested_inbox]: " transactions_inbox
        transactions_inbox="${transactions_inbox:-$suggested_inbox}"

        local suggested_db="${existing_db:-$PWD/budget.db}"
        read -r -p "Database file path [$suggested_db]: " database_path
        database_path="${database_path:-$suggested_db}"
    fi

    local values=("TRANSACTIONS_INBOX=$transactions_inbox" "DATABASE_PATH=$database_path")
    local required=("TRANSACTIONS_INBOX" "DATABASE_PATH")
    if [[ -n "$AI_BACKEND" ]]; then
        # ADVISOR_BACKEND (budget_suggestions) is a separate setting from
        # CATEGORISER_BACKEND (statement_export) per ADR-0014, but there's no
        # reason to make someone who just answered "yes, I have Claude Code/
        # Codex" go edit .env by hand a second time to get Budget Suggestion
        # working - mirror the same choice into both.
        values+=("CATEGORISER_BACKEND=$AI_BACKEND" "ADVISOR_BACKEND=$AI_BACKEND")
        required+=("CATEGORISER_BACKEND" "ADVISOR_BACKEND")
    fi

    uv run python -m setup write-env --values "${values[@]}" --required "${required[@]}"
    if [[ $? -ne 0 ]]; then
        echo
        echo ".env is still missing some required values (see above). Fix them by"
        echo "hand in .env, or re-run this script."
        press_any_key
        exit 1
    fi
    echo ".env written."
}

build_frontend() {
    # The Dashboard is the headline feature, so it's always built (mirrors
    # issue #116 story 12) - unlike the manual README walkthrough, where it's
    # optional.
    echo
    if [[ -f "src/dashboard/static/index.html" ]]; then
        read -r -p "Dashboard frontend is already built - rebuild it? [y/N] " rebuild
        if [[ "$rebuild" != [Yy] ]]; then
            return 0
        fi
    fi

    echo "--- Building the Dashboard frontend..."
    (
        cd frontend
        npm install && npm run build
    )
    if [[ $? -ne 0 ]]; then
        echo "Building the frontend failed - see above."
        press_any_key
        exit 1
    fi
    echo "Frontend built."
}

ensure_homebrew

ensure_prereq "Git" git git "https://git-scm.com/downloads"
ensure_prereq "uv" uv uv "https://docs.astral.sh/uv/getting-started/installation/"
ensure_python
ensure_node
ensure_prereq "GitHub CLI" gh gh "https://cli.github.com/"
ensure_gh_auth
ensure_clone

echo
echo "--- Installing Python dependencies (uv sync)..."
uv sync
if [[ $? -ne 0 ]]; then
    echo "uv sync failed - see above."
    press_any_key
    exit 1
fi

configure_ai_path
configure_env
build_frontend

echo
echo "==============================================="
echo " Setup complete."
echo "==============================================="
echo
echo "Double-click mac/open_dashboard.command to view the Dashboard."
if [[ -n "$AI_BACKEND" ]]; then
    echo "Run mac/process_statement_export.command whenever you have a new Statement Export to categorise."
    echo "Run mac/generate_budget_suggestion.command any time for a fresh Budget Suggestion write-up."
else
    echo "You're on the Dashboard-only path - add transactions by hand via the Dashboard's"
    echo "Transactions tab. Re-run setup.command any time to add the AI-categorisation path."
fi
press_any_key
exit 0
