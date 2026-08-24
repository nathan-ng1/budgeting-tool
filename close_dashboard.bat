@echo off
REM Stop whatever Dashboard server is currently running - one double-click, no
REM terminal needed. Finds the process listening on DASHBOARD_PORT (from .env,
REM 8765 if unset) and ends it, so a restart after a code change actually picks
REM up the new code instead of silently still serving the old one.
REM
REM This is a hard stop (Stop-Process -Force), not a graceful shutdown - fine
REM for local dev use, since every write already commits immediately (see
REM database.store).

setlocal
cd /d "%~dp0"

REM --- Which port? DASHBOARD_PORT in .env wins, else the server's own default -
REM     same lookup open_dashboard.bat uses, so this always targets the same
REM     port that script would have started the server on.
set "PORT=8765"
if exist ".env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
        if /i "%%A"=="DASHBOARD_PORT" set "PORT=%%B"
    )
)

echo Looking for a Dashboard server on port %PORT%...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ids = Get-NetTCPConnection -LocalPort %PORT% -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique;" ^
    "if (-not $ids) { exit 2 };" ^
    "foreach ($id in $ids) { Write-Output ('Stopping process ' + $id + '...'); Stop-Process -Id $id -Force -ErrorAction SilentlyContinue };" ^
    "exit 0"

if errorlevel 2 (
    echo Nothing is listening on port %PORT% - the Dashboard is not running.
    pause
    exit /b 0
)

echo Dashboard on port %PORT% stopped.
pause
