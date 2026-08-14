@echo off
REM Run the full Statement Export process: sanitise anything in the Transactions
REM Inbox, then categorise and write it to the Transaction Log via whichever
REM backend is configured (CATEGORISER_BACKEND in .env - claude, codex, or
REM openai-compatible). Pass --dry-run to preview without writing.
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
echo Processing the sanitised export...
uv run python -m statement_export %*
if errorlevel 1 (
    echo Processing failed for one or more files - see above.
    pause
    exit /b 1
)

pause
