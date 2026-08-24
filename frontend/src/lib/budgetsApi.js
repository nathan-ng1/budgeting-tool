// The Budget tab's per-month editor endpoint (Issue #62) and Full year
// read-only grid endpoint (Issue #64). Every write is validated by the
// store, not here - this module only carries the Amount across and surfaces
// whatever the backend says when it refuses one.

const BASE = "/api/budget-editor";
const GRID_BASE = "/api/budget-grid";
const SUGGESTION_BASE = "/api/budget-suggestion";

async function request(url, options = {}) {
  const response = await fetch(url, options);

  if (!response.ok) {
    throw new Error(await failureMessage(response));
  }

  // DELETE answers 204 with no body, so there is nothing to parse.
  return response.status === 204 ? null : response.json();
}

async function failureMessage(response) {
  try {
    const body = await response.json();
    if (body && body.error) {
      return body.error;
    }
  } catch {
    // A failure with no JSON body at all - fall through to the status.
  }
  return `The Dashboard backend returned ${response.status}.`;
}

// `window` is the trailing window (3/6/12 - Issue #63) the historical
// columns are computed over; omitted, the backend falls back to its own
// default rather than this module restating it.
export function fetchBudgetEditor({ year, month }, { signal, window } = {}) {
  const query = window === undefined ? `year=${year}&month=${month}` : `year=${year}&month=${month}&window=${window}`;
  return request(`${BASE}?${query}`, { signal });
}

export function saveCategoryBudget({ year, month }, category, amount) {
  return request(`${BASE}/${encodeURIComponent(category)}?year=${year}&month=${month}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ amount }),
  });
}

export function deleteCategoryBudget({ year, month }, category) {
  return request(`${BASE}/${encodeURIComponent(category)}?year=${year}&month=${month}`, { method: "DELETE" });
}

// The Full year read-only grid (Issue #64) - every Category Budget across
// the Financial Year starting `year`-07, grouped by Type.
export function fetchBudgetGrid(year, { signal } = {}) {
  return request(`${GRID_BASE}?year=${year}`, { signal });
}

// The standing Budget Suggestion write-up (Issue #66) - not scoped to any
// (year, month), so unlike every other fetch here this takes no arguments
// beyond an optional abort signal.
export function fetchBudgetSuggestion({ signal } = {}) {
  return request(SUGGESTION_BASE, { signal });
}
