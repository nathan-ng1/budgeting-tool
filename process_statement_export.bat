@echo off
REM Run the full Statement Export process: sanitise anything in the Transactions
REM Inbox, then hand off to Claude to categorise and write it to the Transaction Log.
REM See docs/agents/statement-export-pipeline.md for the full walkthrough.

cd /d "%~dp0"

echo Sanitising exports from the Transactions Inbox...
uv run python -m sanitising
if errorlevel 1 (
    echo Sanitising failed - aborting.
    pause
    exit /b 1
)

echo.
echo Launching Claude to process the sanitised export...
claude "process the new statement export"
