@echo off
REM Installation Pack bootstrapper (ADR-0017/0018) - installs prerequisites,
REM clones the repo, configures .env, and builds the Dashboard frontend.
REM
REM Standalone by design: this file is meant to be downloaded on its own from
REM a GitHub Release and double-clicked before Git, or a clone, exist - so it
REM can't assume anything about the folder it's run from. It's also safe to
REM re-run from inside an existing clone: that's both the "fix a partial
REM install" path and the "Dashboard-only user adding the AI path later" path
REM (ADR-0017's idempotency requirement, issue #116 user stories 4 and 13).
REM
REM See docs/setup-guide.html for the guided walkthrough this script backs.
REM
REM Lives under windows/ in this repo for source-tree organisation, but is
REM downloaded standalone from a Release, so it never assumes anything about
REM its own folder - see mac/setup.command for the macOS equivalent
REM (issue #117).

setlocal enabledelayedexpansion
cd /d "%~dp0"
title Budgeting Tool - Setup

set "REPO_OWNER=nathan-ng1"
set "REPO_NAME=budgeting-tool"

echo ===============================================
echo  Budgeting Tool - Installation Pack setup
echo ===============================================
echo.

call :ensure_winget

call :ensure_prereq "Git" git "Git.Git" "https://git-scm.com/downloads"
if errorlevel 1 exit /b 1

call :ensure_prereq "uv" uv "astral-sh.uv" "https://docs.astral.sh/uv/getting-started/installation/"
if errorlevel 1 exit /b 1

call :ensure_python
if errorlevel 1 exit /b 1

call :ensure_node
if errorlevel 1 exit /b 1

call :ensure_prereq "GitHub CLI" gh "GitHub.cli" "https://cli.github.com/"
if errorlevel 1 exit /b 1

call :ensure_gh_auth
if errorlevel 1 exit /b 1

call :ensure_clone
if errorlevel 1 exit /b 1

echo.
echo --- Installing Python dependencies (uv sync)...
uv sync
if errorlevel 1 (
    echo uv sync failed - see above.
    pause
    exit /b 1
)

call :configure_ai_path
if errorlevel 1 exit /b 1

call :configure_env
if errorlevel 1 exit /b 1

call :build_frontend

echo.
echo ===============================================
echo  Setup complete.
echo ===============================================
echo.
echo Double-click windows\open_dashboard.bat to view the Dashboard.
if defined AI_BACKEND (
    echo Run windows\process_statement_export.bat whenever you have a new Statement Export to categorise.
    echo Run windows\generate_budget_suggestion.bat any time for a fresh Budget Suggestion write-up.
) else (
    echo You're on the Dashboard-only path - add transactions by hand via the Dashboard's
    echo Transactions tab. Re-run setup.bat any time to add the AI-categorisation path.
)
pause
exit /b 0


REM =============================================================================
:ensure_winget
REM Sets WINGET_OK=1 if winget is available; otherwise every :ensure_prereq call
REM below falls back to printing a manual download link (issue #116 story 7).
where winget >nul 2>&1
if errorlevel 1 (
    set "WINGET_OK="
    echo NOTE: winget was not found on this machine. Prerequisites below will need
    echo to be installed manually - a download link is printed for each.
) else (
    set "WINGET_OK=1"
)
exit /b 0


REM =============================================================================
:refresh_path
REM winget/npm installs update the Machine/User Path in the registry, not this
REM already-running process's own environment block - without this, a tool
REM installed moments ago would still look "not found" for the rest of this
REM run even though it inspires a re-check right after (issue #116 story 4:
REM re-running setup.bat needs to actually pick up what was just installed).
set "SYS_PATH="
set "USR_PATH="
for /f "tokens=2,*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYS_PATH=%%B"
for /f "tokens=2,*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USR_PATH=%%B"
if defined SYS_PATH if defined USR_PATH set "PATH=%SYS_PATH%;%USR_PATH%"
exit /b 0


REM =============================================================================
REM :ensure_prereq "<display name>" <command-to-check> <winget-id> <manual-url>
:ensure_prereq
set "DISPLAY_NAME=%~1"
set "CHECK_CMD=%~2"
set "WINGET_ID=%~3"
set "MANUAL_URL=%~4"

where %CHECK_CMD% >nul 2>&1
if not errorlevel 1 (
    echo [ok] %DISPLAY_NAME% is already installed.
    exit /b 0
)

echo.
echo %DISPLAY_NAME% was not found.
if not defined WINGET_OK (
    echo Install it manually from: %MANUAL_URL%
    echo Then re-run this script.
    pause
    exit /b 1
)

set /p "CONFIRM=Install %DISPLAY_NAME% now via winget? [Y/n] "
if /i "%CONFIRM%"=="n" (
    echo Skipping %DISPLAY_NAME%. Setup can't continue without it - install it
    echo yourself ^(%MANUAL_URL%^) and re-run this script when you're ready.
    pause
    exit /b 1
)

echo Installing %DISPLAY_NAME%...
winget install --id %WINGET_ID% -e --accept-source-agreements --accept-package-agreements
if errorlevel 1 (
    echo Installing %DISPLAY_NAME% via winget failed. Try manually: %MANUAL_URL%
    pause
    exit /b 1
)

call :refresh_path
where %CHECK_CMD% >nul 2>&1
if errorlevel 1 (
    echo %DISPLAY_NAME% installed, but this window still can't see it on PATH.
    echo Close this window, open a new one, and re-run this script.
    pause
    exit /b 1
)
echo %DISPLAY_NAME% installed.
exit /b 0


REM =============================================================================
:ensure_python
REM Python needs a version check, not just a presence check - a stray old
REM Python 2/early-3 install shouldn't count as satisfying "3.12+".
where python >nul 2>&1
if not errorlevel 1 (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1
    if not errorlevel 1 (
        echo [ok] Python 3.12+ is already installed.
        exit /b 0
    )
)

echo.
echo Python 3.12+ was not found.
if not defined WINGET_OK (
    echo Install it manually from: https://www.python.org/downloads/
    echo Then re-run this script.
    pause
    exit /b 1
)

set /p "CONFIRM=Install Python 3.12 now via winget? [Y/n] "
if /i "%CONFIRM%"=="n" (
    echo Skipping Python. Setup can't continue without it - install it yourself
    echo and re-run this script when you're ready.
    pause
    exit /b 1
)

winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
if errorlevel 1 (
    echo Installing Python via winget failed. Try manually: https://www.python.org/downloads/
    pause
    exit /b 1
)

call :refresh_path
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1
if errorlevel 1 (
    echo Python installed, but this window still can't see 3.12+ on PATH.
    echo Close this window, open a new one, and re-run this script.
    pause
    exit /b 1
)
echo Python installed.
exit /b 0


REM =============================================================================
:ensure_node
REM Node.js 20+ - the frontend is always built (issue #116 story 12), so unlike
REM the README's "optional" framing for manual setup, this script requires it.
where node >nul 2>&1
if not errorlevel 1 (
    node -e "process.exit(parseInt(process.versions.node.split('.')[0], 10) >= 20 ? 0 : 1)" >nul 2>&1
    if not errorlevel 1 (
        echo [ok] Node.js 20+ is already installed.
        exit /b 0
    )
)

echo.
echo Node.js 20+ was not found.
if not defined WINGET_OK (
    echo Install it manually from: https://nodejs.org/
    echo Then re-run this script.
    pause
    exit /b 1
)

set /p "CONFIRM=Install Node.js LTS now via winget? [Y/n] "
if /i "%CONFIRM%"=="n" (
    echo Skipping Node.js. Setup can't continue without it - install it yourself
    echo and re-run this script when you're ready.
    pause
    exit /b 1
)

winget install --id OpenJS.NodeJS.LTS -e --accept-source-agreements --accept-package-agreements
if errorlevel 1 (
    echo Installing Node.js via winget failed. Try manually: https://nodejs.org/
    pause
    exit /b 1
)

call :refresh_path
node -e "process.exit(parseInt(process.versions.node.split('.')[0], 10) >= 20 ? 0 : 1)" >nul 2>&1
if errorlevel 1 (
    echo Node.js installed, but this window still can't see 20+ on PATH.
    echo Close this window, open a new one, and re-run this script.
    pause
    exit /b 1
)
echo Node.js installed.
exit /b 0


REM =============================================================================
:ensure_gh_auth
REM gh moved from optional to required (ADR-0017) - both the initial clone of
REM this private repo and every update check depend on it being authenticated.
gh auth status >nul 2>&1
if not errorlevel 1 (
    echo [ok] GitHub CLI is already logged in.
    exit /b 0
)

echo.
echo GitHub CLI isn't logged in yet. This repo is private, so an authenticated
echo account that's been added as a collaborator is required to continue.
gh auth login
if errorlevel 1 (
    echo GitHub CLI login did not complete. Re-run this script once you're logged in.
    exit /b 1
)

gh auth status >nul 2>&1
if errorlevel 1 (
    echo Still not logged in - re-run this script once 'gh auth login' succeeds.
    exit /b 1
)
exit /b 0


REM =============================================================================
:ensure_clone
REM Four cases: already inside a clone (re-run, or the maintainer's pre-existing
REM checkout - story 30); inside an existing checkout's windows\ folder itself
REM (re-running windows\setup.bat from inside a clone, rather than a
REM standalone download - .git now lives one level up from this script, not
REM next to it, since the windows/mac split moved this script out of the repo
REM root; missing this case used to silently clone a redundant nested copy
REM and write .env/build the frontend there instead of the real repo root);
REM a partial clone sitting next to this script; or a clean bootstrap that
REM needs to clone from scratch.
if exist ".git" (
    echo [ok] Already inside a clone of this repo.
    exit /b 0
)

if exist "..\.git" (
    echo [ok] Already inside a clone of this repo ^(running from windows\^).
    cd /d ".."
    exit /b 0
)

if exist "%REPO_NAME%" (
    if exist "%REPO_NAME%\.git" (
        echo [ok] Found an existing clone in .\%REPO_NAME% - continuing there.
        cd /d "%REPO_NAME%"
        exit /b 0
    )
    echo A folder named "%REPO_NAME%" already exists here but isn't a git clone.
    echo Rename or remove it, then re-run this script.
    pause
    exit /b 1
)

echo.
echo Cloning %REPO_OWNER%/%REPO_NAME%...
gh repo clone %REPO_OWNER%/%REPO_NAME%
if errorlevel 1 (
    echo Clone failed - check you've been added as a collaborator on this
    echo private repo, then re-run this script.
    pause
    exit /b 1
)
cd /d "%REPO_NAME%"
exit /b 0


REM =============================================================================
:configure_ai_path
REM Sets AI_BACKEND to claude/codex, or leaves it undefined for Dashboard-only
REM (ADR-0018) - configure_env below reads it to decide what goes in .env.
set "AI_BACKEND="

echo.
set /p "HAS_AI=Do you have a Claude Code or Codex CLI subscription? [y/N] "
if /i not "%HAS_AI%"=="y" (
    echo Continuing on the Dashboard-only path. You can add AI categorisation
    echo later by re-running this script.
    exit /b 0
)

:ask_which_ai
set /p "WHICH_AI=Which one - (1) Claude Code or (2) Codex CLI? [1/2] "
if "%WHICH_AI%"=="1" (
    set "AI_BACKEND=claude"
) else if "%WHICH_AI%"=="2" (
    set "AI_BACKEND=codex"
) else (
    echo Please enter 1 or 2.
    goto ask_which_ai
)

if "%AI_BACKEND%"=="claude" (
    call :ensure_npm_global "Claude Code" claude "@anthropic-ai/claude-code"
    if errorlevel 1 exit /b 1
    call :verify_claude_login
) else (
    call :ensure_npm_global "Codex CLI" codex "@openai/codex"
    if errorlevel 1 exit /b 1
    call :verify_codex_login
)
exit /b 0


REM =============================================================================
REM :ensure_npm_global "<display name>" <command-to-check> <npm-package>
:ensure_npm_global
set "DISPLAY_NAME=%~1"
set "CHECK_CMD=%~2"
set "NPM_PACKAGE=%~3"

where %CHECK_CMD% >nul 2>&1
if not errorlevel 1 (
    echo [ok] %DISPLAY_NAME% is already installed.
    exit /b 0
)

echo.
echo %DISPLAY_NAME% was not found.
set /p "CONFIRM=Install %DISPLAY_NAME% now via npm? [Y/n] "
if /i "%CONFIRM%"=="n" (
    echo Skipping %DISPLAY_NAME% - install it yourself, then re-run this script.
    pause
    exit /b 1
)

call npm install -g %NPM_PACKAGE%
if errorlevel 1 (
    echo Installing %DISPLAY_NAME% via npm failed - see above.
    pause
    exit /b 1
)

call :refresh_path
where %CHECK_CMD% >nul 2>&1
if errorlevel 1 (
    echo %DISPLAY_NAME% installed, but this window still can't see it on PATH.
    echo Close this window, open a new one, and re-run this script.
    pause
    exit /b 1
)
echo %DISPLAY_NAME% installed.
exit /b 0


REM =============================================================================
:verify_claude_login
REM No non-interactive "am I logged in" flag ships with Claude Code, so this
REM probes with a trivial non-interactive prompt: a login-required failure
REM looks different from a successful (even empty) response.
echo Checking Claude Code login...
claude -p "reply with the single word: ok" >nul 2>nul
if not errorlevel 1 (
    echo [ok] Claude Code is logged in.
    exit /b 0
)

:claude_login_wait
echo.
echo Claude Code doesn't look logged in yet. Run 'claude' in another window and
echo complete the login flow, then come back here.
pause
claude -p "reply with the single word: ok" >nul 2>nul
if errorlevel 1 (
    echo Still not logged in.
    goto claude_login_wait
)
echo [ok] Claude Code is logged in.
exit /b 0


REM =============================================================================
:verify_codex_login
echo Checking Codex CLI login...
codex login status >nul 2>nul
if not errorlevel 1 (
    echo [ok] Codex CLI is logged in.
    exit /b 0
)

:codex_login_wait
echo.
echo Codex CLI doesn't look logged in yet. Run 'codex login' in another window
echo and complete the login flow, then come back here.
pause
codex login status >nul 2>nul
if errorlevel 1 (
    echo Still not logged in.
    goto codex_login_wait
)
echo [ok] Codex CLI is logged in.
exit /b 0


REM =============================================================================
:configure_env
REM Prompts for the per-person values, preserving whatever's already in .env
REM (or .env.example, on a first run) for anything the user doesn't change -
REM this is what makes a Dashboard-only user's later AI-path re-run non-
REM destructive (story 13). The actual merge/write is the tested seam
REM (src/setup/env_file.py), invoked below via write-env.
echo.
echo --- Configuring .env

REM Read whatever's already there so a re-run can offer to keep it, rather
REM than always suggesting a generic default that would clobber real values
REM on Enter (story 13 - this is what makes the Dashboard-only-then-AI-later
REM re-run non-destructive).
set "EXISTING_INBOX="
set "EXISTING_DB="
if exist ".env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
        if /i "%%A"=="TRANSACTIONS_INBOX" set "EXISTING_INBOX=%%B"
        if /i "%%A"=="DATABASE_PATH" set "EXISTING_DB=%%B"
    )
)

if defined EXISTING_INBOX if defined EXISTING_DB (
    echo Already configured:
    echo   TRANSACTIONS_INBOX=%EXISTING_INBOX%
    echo   DATABASE_PATH=%EXISTING_DB%
    set /p "RECONFIGURE=Change these? [y/N] "
    if /i not "!RECONFIGURE!"=="y" (
        set "TRANSACTIONS_INBOX=%EXISTING_INBOX%"
        set "DATABASE_PATH=%EXISTING_DB%"
        goto env_values_set
    )
)

set "SUGGESTED_INBOX=%USERPROFILE%\Documents\Transactions"
if defined EXISTING_INBOX set "SUGGESTED_INBOX=%EXISTING_INBOX%"
set /p "TRANSACTIONS_INBOX=Transactions Inbox folder [%SUGGESTED_INBOX%]: "
if "%TRANSACTIONS_INBOX%"=="" set "TRANSACTIONS_INBOX=%SUGGESTED_INBOX%"
REM A trailing backslash right before the closing quote we add above would be
REM read as an escaped quote by the called process's argv parser - strip it.
if "%TRANSACTIONS_INBOX:~-1%"=="\" set "TRANSACTIONS_INBOX=%TRANSACTIONS_INBOX:~0,-1%"

set "SUGGESTED_DB=%CD%\budget.db"
if defined EXISTING_DB set "SUGGESTED_DB=%EXISTING_DB%"
set /p "DATABASE_PATH=Database file path [%SUGGESTED_DB%]: "
if "%DATABASE_PATH%"=="" set "DATABASE_PATH=%SUGGESTED_DB%"

:env_values_set
REM Each KEY=VALUE is quoted on its own - Windows paths routinely contain
REM spaces (e.g. a username folder), and an unquoted %VALUES% would let cmd's
REM own tokenising split one path into several argv entries.
set "VALUES="TRANSACTIONS_INBOX=%TRANSACTIONS_INBOX%" "DATABASE_PATH=%DATABASE_PATH%""
set "REQUIRED=TRANSACTIONS_INBOX DATABASE_PATH"
if defined AI_BACKEND (
    REM ADVISOR_BACKEND (budget_suggestions) is a separate setting from
    REM CATEGORISER_BACKEND (statement_export) per ADR-0014, but there's no
    REM reason to make someone who just answered "yes, I have Claude Code/
    REM Codex" go edit .env by hand a second time to get Budget Suggestion
    REM working - mirror the same choice into both.
    set "VALUES=%VALUES% "CATEGORISER_BACKEND=%AI_BACKEND%" "ADVISOR_BACKEND=%AI_BACKEND%""
    set "REQUIRED=%REQUIRED% CATEGORISER_BACKEND ADVISOR_BACKEND"
)

uv run python -m setup write-env --values %VALUES% --required %REQUIRED%
if errorlevel 1 (
    echo.
    echo .env is still missing some required values ^(see above^). Fix them by
    echo hand in .env, or re-run this script.
    pause
    exit /b 1
)
echo .env written.
exit /b 0


REM =============================================================================
:build_frontend
REM The Dashboard is the headline feature, so it's always built (story 12) -
REM unlike the manual README walkthrough, where it's optional.
echo.
if exist "src\dashboard\static\index.html" (
    set /p "REBUILD=Dashboard frontend is already built - rebuild it? [y/N] "
    if /i not "!REBUILD!"=="y" exit /b 0
)

echo --- Building the Dashboard frontend...
pushd frontend
call npm install
if errorlevel 1 (
    echo npm install failed - see above.
    popd
    pause
    exit /b 1
)
call npm run build
if errorlevel 1 (
    echo npm run build failed - see above.
    popd
    pause
    exit /b 1
)
popd
echo Frontend built.
exit /b 0
