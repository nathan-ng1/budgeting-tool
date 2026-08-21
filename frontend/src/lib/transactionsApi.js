// The Transactions tab's read endpoint (Issue #33) - list-only for now, since
// the tab has no add/edit/delete yet (see Issue #32's later tickets).

export async function fetchTransactions({ year, month }, { signal } = {}) {
  const response = await fetch(`/api/transactions?year=${year}&month=${month}`, { signal });

  if (!response.ok) {
    throw new Error(`The Dashboard backend returned ${response.status} for the Transactions list.`);
  }

  return response.json();
}
