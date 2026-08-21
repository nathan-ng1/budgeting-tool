# Migrate the Transaction Log and Recurring Transactions Config to a local SQLite database

The Dashboard (a locally-run web app, see [ADR-0008](./0008-dashboard-is-a-local-web-app-not-a-hosted-artifact.md)) needs frequent, fast reads (chart re-renders, month switching) and a live-editable Recurring Transactions Config — both a poor fit for the Google Sheets API's latency and the per-row `ONE_OF_RANGE` validation quirks already documented in `docs/agents/google-sheets-mcp.md`, and for hand-editing an `.xlsx` file from a web UI. We migrated both to a local SQLite database, retiring Google Sheets as the live store and `config\recurring-transactions.xlsx` as the recurring-rules source. Existing history was migrated in place, remapped from the old six-Category model to the new Income/Expense/Transfer model (see [ADR-0006](./0006-simplify-to-three-types-with-a-flat-category-list.md)) — verified mechanical against the live sheet's actual historical data, with no ambiguous cases.

## Consequences

- The Sheets MCP connection (`docs/agents/google-sheets-mcp.md`) and its documented dropdown-validation footguns no longer apply to the live write path; that doc becomes historical/reference only unless Google Sheets is kept around as a one-off export target.
- `src/transaction_log/sheets_client.py` and `src/recurring/config.py`'s `openpyxl` parsing are replaced by a database-backed equivalent.
- Sanitising's role is unchanged — it still strips PII before anything reaches `.data\`, independent of where the Transaction Log itself lives.
