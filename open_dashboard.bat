@echo off
REM Start the Dashboard and open it in Chrome - one double-click, no terminal
REM needed. Serves on DASHBOARD_PORT from .env (8765 if unset), the same local
REM server described in ADR-0008; nothing leaves this machine.
REM
REM Leave this window open while you use the Dashboard - closing it, or
REM pressing Ctrl+C, stops the server.

setlocal

cd /d "%~dp0"

REM Re-entry: the browser is opened by a second copy of this script, so the
REM server can hold the foreground of this window (see the start /b below).
if "%~1"=="--open-when-ready" goto open_when_ready

REM --- Which port? DASHBOARD_PORT in .env wins, else the server's own default.
set "PORT=8765"
if exist ".env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
        if /i "%%A"=="DASHBOARD_PORT" set "PORT=%%B"
    )
)

REM --- The frontend is a build artefact and is gitignored, so a fresh clone
REM     has no page to serve. Say so here rather than letting the browser show
REM     the server's own build instructions.
if not exist "src\dashboard\static\index.html" (
    echo The Dashboard frontend has not been built yet.
    echo.
    echo     cd frontend
    echo     npm install
    echo     npm run build
    echo.
    echo Then run this again. Node.js 20+ is needed - see the README.
    echo.
    pause
    exit /b 1
)

REM --- Already serving? Then just open it rather than failing to bind.
call :is_listening %PORT%
if not errorlevel 1 (
    echo The Dashboard is already running on port %PORT% - opening it.
    call :open_browser %PORT%
    exit /b 0
)

REM --- Open the browser once the server is actually accepting connections.
start "" /b cmd /c ""%~f0" --open-when-ready %PORT%"

echo Starting the Dashboard on port %PORT%...
echo Close this window or press Ctrl+C to stop it.
echo.

uv run python -m dashboard
if errorlevel 1 (
    echo.
    echo The Dashboard exited with an error - see above.
    pause
    exit /b 1
)

exit /b 0


REM ---------------------------------------------------------------------------
:open_when_ready
REM Wait for the port to accept a connection, then open the browser. Polling the
REM socket rather than sleeping a fixed time: the first `uv run` of a session
REM can take a while, and a fixed wait would either race it or dawdle.
set "PORT=%~2"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$deadline = (Get-Date).AddSeconds(60);" ^
    "while ((Get-Date) -lt $deadline) {" ^
    "  try { $c = New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1', %PORT%); $c.Close(); exit 0 }" ^
    "  catch { Start-Sleep -Milliseconds 250 }" ^
    "}; exit 1"
if errorlevel 1 (
    echo The Dashboard did not start within 60 seconds - not opening the browser.
    exit /b 1
)
call :open_browser %PORT%
exit /b 0


REM ---------------------------------------------------------------------------
:is_listening
REM Sets errorlevel 0 if something is already listening on the given port.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "try { $c = New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1', %~1); $c.Close(); exit 0 }" ^
    "catch { exit 1 }"
exit /b %errorlevel%


REM ---------------------------------------------------------------------------
:open_browser
set "URL=http://127.0.0.1:%~1"
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
