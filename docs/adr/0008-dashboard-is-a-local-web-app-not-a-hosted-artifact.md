# The Dashboard is a local web app, not a hosted Artifact

Claude Design (used to produce the Dashboard's visual mockup) publishes as an Artifact — a page hosted on claude.ai, private by default but still off-machine. This tool's data is personal financial data (real amounts, merchants, income), and Sanitising already exists specifically to keep such data from leaving the user's control. We decided Claude Design produces the visual reference only; the production Dashboard is a locally-run web app (a small backend plus browser frontend) that reads the local database directly and never sends transaction data anywhere.

## Consequences

- The Dashboard needs its own local server process (framework choice deferred to implementation time) rather than reusing Artifact hosting/capabilities.
- Needs Review resolution stays in the terminal flow, not the Dashboard, for this round — the Dashboard's initial scope is the Overview tab (stat tiles, spending-by-category donut, expenses-over-time chart) plus Recurring Transactions Config editing. Transactions/Month vs Month/Budget/Insights tabs are a later phase.
