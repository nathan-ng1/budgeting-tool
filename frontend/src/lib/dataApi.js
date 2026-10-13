// The "Your data" endpoint (Issue #196, ADR-0030): where the Database lives and
// how big it is. Later "Your data" actions (backup, move, switch, delete) add
// their calls here - mirrors categoriesApi.js.

const BASE = "/api/database";

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

/** The Database's `{ path, size_bytes }`. */
export function fetchDatabaseLocation({ signal } = {}) {
  return request(BASE, { signal });
}
