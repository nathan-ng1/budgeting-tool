# Changelog

## v0.4.1 — 2026-10-11

- Updating no longer stops on leftover files, such as a `budget.db` in the project folder, or on the tool's own `uv.lock` file having changed. `update.bat` and `update.command` still refuse to update if you've edited anything else.
