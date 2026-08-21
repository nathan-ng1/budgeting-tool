// The Month Overview endpoint (Issue #27). Everything the Overview tab renders
// comes from this one call - the frontend does no aggregation of its own.

export async function fetchMonthOverview({ year, month }, { signal } = {}) {
  const response = await fetch(`/api/overview?year=${year}&month=${month}`, { signal });

  if (!response.ok) {
    throw new Error(`The Dashboard backend returned ${response.status} for ${year}-${String(month).padStart(2, "0")}.`);
  }

  return response.json();
}
