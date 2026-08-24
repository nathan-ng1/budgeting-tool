@echo off
REM Regenerate the standing Budget Suggestion write-up - one double-click, no
REM terminal needed. Pulls recent Expense/Debt Budgeted vs Actual history and
REM analyses it via whichever backend is configured (ADVISOR_BACKEND in .env -
REM claude, codex, or openai-compatible), replacing whatever write-up was
REM stored before - one standing document, no history kept (ADR-0014: a
REM scripted flow, not a live Dashboard call).
REM
REM Refresh the Dashboard's Budget tab afterwards to see the new write-up.

cd /d "%~dp0"

echo Regenerating the Budget Suggestion...
uv run python -m budget_suggestions
if errorlevel 1 (
    echo Budget Suggestion generation failed - see above.
    pause
    exit /b 1
)

pause
