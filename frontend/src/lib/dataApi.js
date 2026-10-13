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

export const BACKUP_URL = `${BASE}/backup`;

/**
 * Generate a Backup and have the browser save it (Issue #197). The server
 * records "Last backed up" when it generates the file. Shared with the delete
 * flow's "download a Backup first" (Issue #201).
 */
export async function downloadBackup() {
  const response = await fetch(BACKUP_URL);

  if (!response.ok) {
    throw new Error(await failureMessage(response));
  }

  const disposition = response.headers.get("Content-Disposition") ?? "";
  const filename = /filename="([^"]+)"/.exec(disposition)?.[1] ?? "budget-backup.db";
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

/** The Database's `{ path, size_bytes, last_backed_up }` (last_backed_up is an ISO timestamp or null). */
export function fetchDatabaseLocation({ signal } = {}) {
  return request(BASE, { signal });
}
