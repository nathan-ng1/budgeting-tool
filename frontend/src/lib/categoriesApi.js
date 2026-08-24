// The Category Management endpoint (Issue #91). Every write is validated by
// the store, not here - this module only carries the Category across and
// surfaces whatever the backend says when it refuses one - mirrors
// recurringApi.js/transactionsApi.js.

const BASE = "/api/categories";

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

function jsonRequest(method, body) {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export function fetchCategories({ signal } = {}) {
  return request(BASE, { signal });
}

export function createCategory({ type, name, emoji }) {
  return request(BASE, jsonRequest("POST", { type, name, emoji }));
}

export function updateCategory(id, { name, emoji }) {
  return request(`${BASE}/${id}`, jsonRequest("PUT", { name, emoji }));
}

export function deleteCategory(id) {
  return request(`${BASE}/${id}`, { method: "DELETE" });
}
