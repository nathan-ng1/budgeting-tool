// The Budget tab's per-month editor endpoint (Issue #62). Every write is
// validated by the store, not here - this module only carries the Amount
// across and surfaces whatever the backend says when it refuses one.

const BASE = "/api/budget-editor";

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

export function fetchBudgetEditor({ year, month }, { signal } = {}) {
  return request(`${BASE}?year=${year}&month=${month}`, { signal });
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
