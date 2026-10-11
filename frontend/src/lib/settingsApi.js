// The localisation settings endpoint (ADR-0027). The server validates every
// save and says why it refused one; this module only carries the settings
// across - mirrors categoriesApi.js.

const BASE = "/api/settings";

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

export function fetchSettings({ signal } = {}) {
  return request(BASE, { signal });
}

// `updates` is any subset of the settings; the answer is all of them.
export function saveSettings(updates) {
  return request(BASE, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
}
