// The Goals endpoint (Goals spec section 7). Every figure on a Goal - Status,
// saved, pace, the monthly amounts - is computed by the backend against one
// "today"; this module only carries Goals across and surfaces whatever the
// backend says when it refuses one.

const BASE = "/api/goals";

async function request(url, options = {}) {
  const response = await fetch(url, options);

  if (!response.ok) {
    throw new Error(await failureMessage(response));
  }

  return response.json();
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

function jsonRequest(method, goal) {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(goal),
  };
}

// { today, goals, past } - active Goals in `goals`, archived and deleted ones
// in `past`, every Goal carrying its derived figures.
export function fetchGoals({ signal } = {}) {
  return request(BASE, { signal });
}

export function createGoal(goal) {
  return request(BASE, jsonRequest("POST", goal));
}

export function updateGoal(id, goal) {
  return request(`${BASE}/${id}`, jsonRequest("PUT", goal));
}

// Archive or delete a Goal: both are soft - the Goal moves to Past goals and
// its Contributions are untouched. Reactivating is an updateGoal with
// `state: "active"`.
export function archiveGoal(id) {
  return request(`${BASE}/${id}/archive`, { method: "POST" });
}

export function deleteGoal(id) {
  return request(`${BASE}/${id}/delete`, { method: "POST" });
}

// Add a Contribution to a Goal: the backend writes a Goals-Category Savings
// Transaction linked to it. `notes` is optional - the backend defaults it to
// the Goal's title. The Goal's figures are re-read by the caller afterwards.
export function addContribution(goalId, { amount, date, notes }) {
  return request(`${BASE}/${goalId}/contributions`, jsonRequest("POST", { amount, date, notes }));
}
