# The Transactions tab is per-Financial-Year, with client-side filtering, search, and sort

Every existing Dashboard endpoint (`/api/overview`) aggregates server-side and hands the frontend a
finished view-model to render, with no computation of its own — established for the Month Overview
endpoint (Issue #27) and restated in `dashboard/queries.py`'s own docstring. The new Transactions tab
(view/filter/search/sort/add/edit/delete over the raw Transaction Log, scoped during a `/grill-with-docs`
session) breaks from that pattern on two points:

1. **Scope: one Financial Year at a time**, not the Transaction Log's full history. `GET
   /api/transactions` returns only the current Financial Year's rows, defaulting the same way Overview's
   month selector defaults — the Financial Year containing today's date. No Financial Year switcher
   exists yet, matching Overview's current lack of one (**resolved by
   [ADR-0021](./0021-financial-year-switcher-and-calendar-year-toggle.md)**, which also extends this tab
   to Calendar Year framing). Showing multiple Financial Years at once was considered and explicitly
   deferred, not ruled out, and remains out of scope.
2. **Client-side filtering, search, and sort.** The endpoint returns that Financial Year's transactions
   as one flat, newest-first list; Category/Month/Type filtering, Notes search, and Date/Amount sorting
   all happen in the browser instead of as query parameters. A transaction list is raw rows, not an
   aggregation, and one Financial Year of a personal card's transactions is small enough (at most a few
   hundred to low thousands of rows) that fetching it whole and filtering in React is simpler than
   backend filter/sort plumbing, with no real cost at this scale.

## Consequences

- If the Transactions tab later grows to span multiple Financial Years, "fetch it all, filter
  client-side" should be revisited — it holds only because a single Financial Year's data is small.
- A future reader comparing `/api/transactions` to `/api/overview` will find the "backend aggregates,
  frontend renders" rule broken; this ADR is that context.
