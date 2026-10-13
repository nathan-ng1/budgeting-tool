// Changing the Database's location (Issue #198, ADR-0030): a two-step flow so
// the user confirms between them. The first step's answer carries the
// `outcome` (move, current, existing, migrate); the second step is one call.

const BASE = "/api/database";

async function post(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });

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

/**
 * Open the native folder picker and report what the chosen folder holds:
 * `{ cancelled: true }`, or `{ cancelled: false, folder, outcome, target }`
 * where `outcome` is "move" (no Database there), "current", "existing" or "migrate".
 */
export function chooseDatabaseFolder() {
  return post(`${BASE}/choose-folder`);
}

/** Carry out the confirmed choice; resolves with the Database's new `{ path, size_bytes }`. */
export function applyDatabaseFolder(folder) {
  return post(`${BASE}/location`, { folder });
}
