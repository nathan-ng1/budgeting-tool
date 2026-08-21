// The Transactions tab's read and CRUD endpoints (Issues #33 and #35). Every
// write is validated by the store, not here - this module only carries the
// transaction across and surfaces whatever the backend says when it refuses
// one - mirrors recurringApi.js.

const BASE = "/api/transactions";

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

function jsonRequest(method, transaction) {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(transaction),
  };
}

export function fetchTransactions({ year, month }, { signal } = {}) {
  return request(`${BASE}?year=${year}&month=${month}`, { signal });
}

export function fetchCategories({ signal } = {}) {
  return request("/api/categories", { signal });
}

export function createTransaction(transaction) {
  return request(BASE, jsonRequest("POST", transaction));
}

export function updateTransaction(id, transaction) {
  return request(`${BASE}/${id}`, jsonRequest("PUT", transaction));
}

export function deleteTransaction(id) {
  return request(`${BASE}/${id}`, { method: "DELETE" });
}
