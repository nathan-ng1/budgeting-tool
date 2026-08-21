// The Month Overview endpoint (Issue #27). Everything the Overview tab renders
// comes from this one call - the frontend does no aggregation of its own.

export async function fetchMonthOverview({ year, month }, { signal } = {}) {
  const response = await fetch(`/api/overview?year=${year}&month=${month}`, { signal });

  if (!response.ok) {
    throw new Error(`The Dashboard backend returned ${response.status} for ${year}-${String(month).padStart(2, "0")}.`);
  }

  return response.json();
}

// Dates the Transaction Log itself for the header's "As at" line. Separate from
// the Overview because it spans the whole log, not the selected month - and it
// is shown on every tab, including ones that fetch no Overview at all.
export async function fetchLatestTransactionDate({ signal } = {}) {
  const response = await fetch("/api/latest-transaction-date", { signal });

  if (!response.ok) {
    throw new Error(`The Dashboard backend returned ${response.status} for the latest Transaction date.`);
  }

  // Normalise a missing or empty date to null: an empty Transaction Log has no
  // date, and an undated header is the one thing the caller has to handle.
  const { date } = await response.json();
  return date || null;
}
