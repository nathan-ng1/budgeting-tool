## Agent skills

### Issue tracker

Issues live on GitHub (`nathan-ng1/budgeting-tool`), via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Google Sheets

Read/write access to the Transaction Log goes through an MCP connection (service account, not
OAuth). See `docs/agents/google-sheets-mcp.md` for config, reproduction steps, and the verified
column layout.
