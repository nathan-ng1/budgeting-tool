// Pure filter/search/sort logic for the Transactions tab (Issue #34) - mirrors
// financialYear.js/charts.js in staying a plain-array module with no fetching
// or component state of its own. Everything here operates on the array the
// tab's fetch (Issue #33) already loaded; no result here ever triggers a
// refetch.

import { monthsOfFinancialYear } from "./financialYear.js";

export const ALL_CATEGORIES = "All categories";
export const ALL_MONTHS = "All months";
export const ALL_TYPES = "All types";

// Fixed per ADR-0006/ADR-0012, not derived from loaded data - Type is a closed
// set regardless of which Types happen to appear in the current Financial Year.
export const TYPES = ["Income", "Expense", "Debt", "Transfer"];

export function categoryOptions(transactions) {
  return [...new Set(transactions.map((transaction) => transaction.category))].sort();
}

export function monthOptions(financialYear) {
  return monthsOfFinancialYear(financialYear).map(({ year, month, label }) => ({
    value: monthValue(year, month),
    label,
  }));
}

function monthValue(year, month) {
  return `${year}-${String(month).padStart(2, "0")}`;
}

function matches(transaction, { category, month, type, search }) {
  if (category !== ALL_CATEGORIES && transaction.category !== category) {
    return false;
  }
  if (month !== ALL_MONTHS && transaction.date.slice(0, 7) !== month) {
    return false;
  }
  if (type !== ALL_TYPES && transaction.type !== type) {
    return false;
  }
  if (search !== "" && !transaction.notes.toLowerCase().includes(search.toLowerCase())) {
    return false;
  }
  return true;
}

function compare(a, b, sortKey) {
  return sortKey === "amount" ? a.amount - b.amount : a.date.localeCompare(b.date);
}

export function visibleTransactions(transactions, filters, { sortKey, sortDirection }) {
  const sign = sortDirection === "asc" ? 1 : -1;
  return transactions
    .filter((transaction) => matches(transaction, filters))
    .sort((a, b) => sign * compare(a, b, sortKey));
}

// Clicking a header flips direction only when it's already the active sort
// key; switching to a different column keeps whatever direction was already
// showing (see Issue #32's Implementation Decisions).
export function nextSort({ sortKey, sortDirection }, clickedKey) {
  if (clickedKey === sortKey) {
    return { sortKey, sortDirection: sortDirection === "asc" ? "desc" : "asc" };
  }
  return { sortKey: clickedKey, sortDirection };
}
