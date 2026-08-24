@echo off
REM Stop whatever Dashboard DEV environment is currently running - the backend
REM and the frontend's Vite dev server started by open_dashboard_dev.bat. One
REM double-click, no terminal needed. Finds whatever is listening on the
REM backend port (DASHBOARD_PORT from .env, 8765 if unset) and Vite's default
REM dev port (5173) and ends both, so a restart after a code change actually
REM picks up the new code.
REM
REM This is a hard stop (Stop-Process -Force), not a graceful shutdown - fine
REM for local dev use, since every write already commits immediately (see
REM database.store). Doesn't touch open_dashboard.bat's built-dashboard server -
REM that's close_dashboard.bat's job.
REM
REM If Vite had to pick a different port than 5173 (because something else was
REM already using it), this won't find that process - close its window by hand.

setlocal
cd /d "%~dp0"

set "BACKEND_PORT=8765"
if exist ".env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
        if /i "%%A"=="DASHBOARD_PORT" set "BACKEND_PORT=%%B"
    )
)
set "FRONTEND_PORT=5173"

call :stop_port %BACKEND_PORT% "backend"
set "STOPPED_BACKEND=%errorlevel%"

call :stop_port %FRONTEND_PORT% "frontend dev server"
set "STOPPED_FRONTEND=%errorlevel%"

if "%STOPPED_BACKEND%"=="2" if "%STOPPED_FRONTEND%"=="2" (
    echo Nothing is listening on port %BACKEND_PORT% or %FRONTEND_PORT% - the dev
    echo environment is not running.
)

pause
exit /b 0


REM ---------------------------------------------------------------------------
:stop_port
REM %1 = port, %2 = label for messages. Sets errorlevel 2 if nothing was
REM listening there, 0 otherwise (mirrors close_dashboard.bat's convention).
echo Looking for the %~2 on port %~1...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ids = Get-NetTCPConnection -LocalPort %~1 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique;" ^
    "if (-not $ids) { exit 2 };" ^
    "foreach ($id in $ids) { Write-Output ('Stopping process ' + $id + '...'); Stop-Process -Id $id -Force -ErrorAction SilentlyContinue };" ^
    "exit 0"
if errorlevel 2 (
    exit /b 2
)
echo %~2 on port %~1 stopped.
exit /b 0
