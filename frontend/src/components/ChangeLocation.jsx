import { useState } from "react";

import { applyDatabaseFolder, chooseDatabaseFolder } from "../lib/databaseLocationApi.js";

// "Change location…" in Your data (Issue #198, ADR-0030). Step one opens the
// native folder picker and learns what the chosen folder holds; step two, the
// confirmation, depends on that `outcome` ("move", "current", "existing" (#199)
// or "migrate" (#200)). A new outcome adds an entry to CONFIRMATIONS rather
// than reshaping the flow.

/** What to tell the user, and whether to offer a move, for each outcome. */
const CONFIRMATIONS = {
  move: {
    describe: (choice) => (
      <>
        The current Database and its pre-migration copies will be moved to <strong>{choice.folder}</strong>. The old
        files are deleted once the move has succeeded.
      </>
    ),
    confirmLabel: "Move the Database",
  },
  current: {
    describe: () => <>The Database is already in that folder.</>,
  },
  existing: {
    describe: (choice) => (
      <>
        The Dashboard will start using the Database in <strong>{choice.folder}</strong>. Your current Database stays
        where it is - nothing is copied or overwritten. This is also how you restore a Backup: put it in a folder on
        its own and choose that folder.
      </>
    ),
    confirmLabel: "Switch to this Database",
  },
  migrate: {
    describe: (choice) => (
      <>
        The Database in <strong>{choice.folder}</strong> is from an older version. It will be migrated before the
        Dashboard starts using it, and a pre-migration copy is kept beside it. Your current Database stays where it
        is.
      </>
    ),
    confirmLabel: "Migrate and switch",
  },
};

const FALLBACK = { describe: () => <>That folder can't be used.</> };

export default function ChangeLocation({ onMoved = () => window.location.reload() }) {
  const [choice, setChoice] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function choose() {
    setBusy(true);
    setError(null);
    try {
      const answer = await chooseDatabaseFolder();
      setChoice(answer.cancelled ? null : answer);
    } catch (cause) {
      setError(cause.message);
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      await applyDatabaseFolder(choice.folder);
      onMoved();
    } catch (cause) {
      setError(cause.message);
      setChoice(null);
    } finally {
      setBusy(false);
    }
  }

  const confirmation = choice ? (CONFIRMATIONS[choice.outcome] ?? FALLBACK) : null;

  return (
    <div className="change-location">
      {error !== null && (
        <p className="state state--error" role="alert">
          {error}
        </p>
      )}
      {confirmation ? (
        <div className="change-location__confirm">
          <p>{confirmation.describe(choice)}</p>
          <div className="change-location__actions">
            {confirmation.confirmLabel && (
              <button type="button" className="button" disabled={busy} onClick={confirm}>
                {confirmation.confirmLabel}
              </button>
            )}
            <button type="button" className="button button--quiet" disabled={busy} onClick={() => setChoice(null)}>
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button type="button" className="button button--quiet" disabled={busy} onClick={choose}>
          Change location…
        </button>
      )}
    </div>
  );
}
