// The Recurring Transactions Config endpoint (Issue #29). Every write is
// validated by the store, not here - this module only carries the rule across
// and surfaces whatever the backend says when it refuses one.

const BASE = "/api/recurring-rules";

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

function jsonRequest(method, rule) {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(rule),
  };
}

export function fetchRecurringRules({ signal } = {}) {
  return request(BASE, { signal });
}

export function fetchCategories({ signal } = {}) {
  return request("/api/categories", { signal });
}

export function createRecurringRule(rule) {
  return request(BASE, jsonRequest("POST", rule));
}

export function updateRecurringRule(id, rule) {
  return request(`${BASE}/${id}`, jsonRequest("PUT", rule));
}

export function deleteRecurringRule(id) {
  return request(`${BASE}/${id}`, { method: "DELETE" });
}

export function runRecurringRules() {
  return request(`${BASE}/run`, { method: "POST" });
}
