@echo off
REM Start the Dashboard's DEV environment - the backend (uv run python -m
REM dashboard, against your real local database) plus the frontend's Vite dev
REM server (hot reload, proxying /api to that backend) - and open it in Chrome.
REM One double-click, no terminal needed. Unlike open_dashboard.bat, this
REM doesn't need `npm run build` first: edits under frontend/src show up in the
REM browser immediately.
REM
REM Opens two windows, one per server. Closing either stops that server; use
REM close_dashboard_dev.bat to stop both at once from elsewhere.

setlocal

cd /d "%~dp0"

REM Re-entry: the browser is opened by a second copy of this script, once the
REM frontend dev server is actually accepting connections (same trick
REM open_dashboard.bat uses).
if "%~1"=="--open-when-ready" goto open_when_ready

REM --- Backend port: DASHBOARD_PORT in .env wins, else 8765 - same lookup
REM     open_dashboard.bat uses. The frontend dev server's proxy
REM     (frontend/vite.config.js) always targets 127.0.0.1:8765, so warn rather
REM     than silently break the proxy if .env asks for a different port.
set "BACKEND_PORT=8765"
if exist ".env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
        if /i "%%A"=="DASHBOARD_PORT" set "BACKEND_PORT=%%B"
    )
)
if not "%BACKEND_PORT%"=="8765" (
    echo Warning: DASHBOARD_PORT is set to %BACKEND_PORT% in .env, but the
    echo frontend dev server's proxy always targets 127.0.0.1:8765
    echo ^(frontend\vite.config.js^). The dev environment won't talk to itself
    echo correctly until one of those is changed to match the other.
    echo.
)

REM --- Vite's default dev port - see README. If it's busy, Vite picks the
REM     next free port on its own; this script won't know that, so the
REM     readiness wait below just times out and says to check the frontend
REM     window.
set "FRONTEND_PORT=5173"

REM --- The frontend's dependencies aren't installed - npm run dev can't work.
if not exist "frontend\node_modules" (
    echo The frontend's dependencies have not been installed yet.
    echo.
    echo     cd frontend
    echo     npm install
    echo.
    echo Then run this again. Node.js 20+ is needed - see the README.
    echo.
    pause
    exit /b 1
)

REM --- Frontend dev server already up? Then just open it.
call :is_listening %FRONTEND_PORT%
if not errorlevel 1 (
    echo The frontend dev server is already running on port %FRONTEND_PORT% - opening it.
    call :open_browser %FRONTEND_PORT%
    exit /b 0
)

REM --- Backend already up? Leave it running rather than starting a second one.
call :is_listening %BACKEND_PORT%
if not errorlevel 1 (
    echo A server is already listening on port %BACKEND_PORT% - assuming it's the
    echo Dashboard backend and leaving it running.
) else (
    echo Starting the Dashboard backend on port %BACKEND_PORT%...
    start "Budgeting Tool - backend (dev)" cmd /k "cd /d "%~dp0" && uv run python -m dashboard"
)

echo Starting the frontend dev server on port %FRONTEND_PORT%...
start "Budgeting Tool - frontend (dev)" cmd /k "cd /d "%~dp0frontend" && npm run dev"

start "" /b cmd /c ""%~f0" --open-when-ready %FRONTEND_PORT%"

echo.
echo Two windows just opened: backend and frontend dev server. Close either to
echo stop that one, or run close_dashboard_dev.bat to stop both at once.
echo.
exit /b 0


REM ---------------------------------------------------------------------------
:open_when_ready
REM Wait for the frontend dev server's port to accept a connection, then open
REM the browser. Polling the socket rather than sleeping a fixed time: the
REM first `npm run dev` of a session can take a while.
set "PORT=%~2"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$deadline = (Get-Date).AddSeconds(60);" ^
    "while ((Get-Date) -lt $deadline) {" ^
    "  try { $c = New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1', %PORT%); $c.Close(); exit 0 } catch {}" ^
    "  try { $c = New-Object Net.Sockets.TcpClient([Net.Sockets.AddressFamily]::InterNetworkV6); $c.Connect([Net.IPAddress]::IPv6Loopback, %PORT%); $c.Close(); exit 0 } catch {}" ^
    "  Start-Sleep -Milliseconds 250" ^
    "}; exit 1"
if errorlevel 1 (
    echo The frontend dev server did not come up on port %PORT% within 60
    echo seconds - check its window; if port %PORT% was busy, Vite may have
    echo picked a different port to serve on instead.
    exit /b 1
)
call :open_browser %PORT%
exit /b 0


REM ---------------------------------------------------------------------------
:is_listening
REM %1 = port. Sets errorlevel 0 if something is listening on that port, on
REM either loopback address (127.0.0.1 or ::1). Vite's default dev server
REM binds to whichever address "localhost" resolves to first on this machine,
REM which varies by machine - trying both is what makes this reliable. A
REM TcpClient built with the plain constructor is IPv4-only and simply cannot
REM connect to ::1 regardless of what string it's given, so the IPv6 attempt
REM needs its own TcpClient built with AddressFamily.InterNetworkV6.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "try { $c = New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1', %~1); $c.Close(); exit 0 } catch {}" ^
    "try { $c = New-Object Net.Sockets.TcpClient([Net.Sockets.AddressFamily]::InterNetworkV6); $c.Connect([Net.IPAddress]::IPv6Loopback, %~1); $c.Close(); exit 0 } catch {}" ^
    "exit 1"
exit /b %errorlevel%


REM ---------------------------------------------------------------------------
:open_browser
REM %1 = port. "localhost" (not 127.0.0.1): a browser resolves and tries
REM whichever loopback address the dev server is actually bound to; a raw
REM TcpClient connect to a single hardcoded address (as :is_listening above
REM must use) can't.
set "URL=http://localhost:%~1"
set "CHROME="
for %%P in (
    "%ProgramFiles%\Google\Chrome\Application\chrome.exe"
    "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
    "%LocalAppData%\Google\Chrome\Application\chrome.exe"
) do if not defined CHROME if exist %%P set "CHROME=%%~P"

if defined CHROME (
    start "" "%CHROME%" "%URL%"
) else (
    echo Chrome was not found - opening in your default browser instead.
    start "" "%URL%"
)
exit /b 0
