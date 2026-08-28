@echo off
REM Explicit, manually-run update step (ADR-0019) - the counterpart to
REM open_dashboard.bat's silent "update available" notice. Fetches tags, shows
REM what's changed since your installed version, confirms, then pulls and
REM re-syncs dependencies. Never reconfigures .env or switches AI path - that
REM stays setup.bat's job (re-run it instead).

setlocal enabledelayedexpansion
cd /d "%~dp0"
title Budgeting Tool - Update

if not exist ".git" (
    echo This isn't a clone of the repo - run update.bat from inside it,
    echo or use setup.bat if you haven't installed yet.
    pause
    exit /b 1
)

echo Fetching the latest tags...
git fetch --tags --quiet
if errorlevel 1 (
    echo Couldn't reach the repo - check your internet connection and that
    echo 'gh auth status' is still logged in, then try again.
    pause
    exit /b 1
)

for /f "delims=" %%T in ('git tag --sort=-v:refname') do (
    if not defined LATEST_TAG set "LATEST_TAG=%%T"
)
if not defined LATEST_TAG (
    echo No Release tags found yet - nothing to update to.
    pause
    exit /b 0
)

for /f "delims=" %%V in ('uv run python -m setup local-version') do set "LOCAL_VERSION=%%V"

set "NEW_VERSION="
for /f "delims=" %%N in ('uv run python -m setup check-update --local "%LOCAL_VERSION%" --latest-tag "%LATEST_TAG%"') do set "NEW_VERSION=%%N"

if not defined NEW_VERSION (
    echo You're already on the latest version ^(%LOCAL_VERSION%^).
    pause
    exit /b 0
)

echo.
echo Installed version: %LOCAL_VERSION%
echo Latest version:    %NEW_VERSION%
echo.
echo What's new:
git log --oneline HEAD.."%LATEST_TAG%"
echo.

set /p "CONFIRM=Update now? [Y/n] "
if /i "%CONFIRM%"=="n" (
    echo No changes made.
    exit /b 0
)

REM --- Don't clobber local work - same git-safety norm as everywhere else in
REM     this repo: surface a conflict rather than silently discarding it.
set "DIRTY="
for /f "delims=" %%S in ('git status --porcelain') do set "DIRTY=1"
if defined DIRTY (
    echo.
    echo You have uncommitted local changes:
    git status --short
    echo.
    echo Commit or stash them first, then re-run update.bat.
    pause
    exit /b 1
)

echo.
echo Pulling latest changes...
git pull --ff-only
if errorlevel 1 (
    echo.
    echo git pull couldn't fast-forward - your local branch has diverged from
    echo origin. Resolve that by hand ^(see the README's git-safety norms^),
    echo then re-run update.bat.
    pause
    exit /b 1
)

echo.
echo Re-syncing Python dependencies...
uv sync
if errorlevel 1 (
    echo uv sync failed - see above.
    pause
    exit /b 1
)

if exist "src\dashboard\static\index.html" (
    echo.
    echo Re-syncing the Dashboard frontend...
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
)

echo.
echo Updated to %NEW_VERSION%.
pause
exit /b 0
