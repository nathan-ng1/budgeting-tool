// The Overview tab is organised around the Financial Year - July 1 to June 30
// (see CONTEXT.md). A Financial Year is named by the calendar year it starts
// in, so "Financial Year 2026" runs July 2026 through June 2027.
//
// A thin, Financial-Year-only face on period.js's framing-agnostic logic
// (ADR-0021) - kept so callers that only ever mean Financial Year (Budget.jsx,
// Transactions.jsx) don't have to pass `"financial"` everywhere.

import { monthsOfPeriod, periodFor, periodLabel, startMonthFor } from "./period.js";

export const FINANCIAL_YEAR_START_MONTH = startMonthFor("financial");

export function financialYearFor(year, month) {
  return periodFor(year, month, "financial");
}

export function monthsOfFinancialYear(financialYear) {
  return monthsOfPeriod(financialYear, "financial");
}

export function financialYearLabel(financialYear) {
  return periodLabel(financialYear, "financial");
}
