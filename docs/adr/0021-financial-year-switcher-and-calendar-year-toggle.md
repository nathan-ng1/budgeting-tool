# A shared Financial Year switcher and Calendar Year toggle replace "always the FY containing today"

ADR-0011 and ADR-0010 each flagged viewing a non-current Financial Year as deferred, out of
scope until a switcher existed. This ADR builds that switcher — prev/next arrows plus a
Financial Year/Calendar Year toggle, in a new header row above the nav, replacing the static
"current FY" subtitle — as global state (`periodType`, `referenceYear`) shared across Overview,
Budget, and Transactions (including the Transactions tab's Export panel default date range), so
the three tabs can never disagree about which year or framing they're showing. Each tab keeps
its own independent month/Full-year pill selection and existing default-on-load behaviour
(Overview defaults to Full year, Budget to the current month) — only the year and FY/CY framing
are shared, not the selected month.

Calendar Year (Jan 1–Dec 31) is a new, real alternative to Financial Year, not just a relabelled
aggregation window: month pills reorder to Jan→Dec when it's active, mirroring Financial Year's
Jul→Jun order. Selectable years are bounded by the Transaction Log's actual date range (oldest
Transaction to today), not a hardcoded lookback. The `periodType` choice persists across reloads;
`referenceYear` and each tab's month/Full-year selection still reset to the current period on
every load, per ADR-0011's existing no-persistence rule.

## Consequences

- The backend's Financial-Year-shaped logic (`_elapsed_months`, the annual overview's month
  ordering, the Budget tab's Full year grid) needs generalising to a caller-supplied start month
  (7 for Financial Year, 1 for Calendar Year) instead of a hardcoded July.
- The Settings tab renders no switcher — it holds no Financial-Year- or Calendar-Year-scoped
  data.
- ADR-0011's "no Financial Year switcher" consequence and ADR-0010's "no switcher yet" note are
  resolved by this ADR.
