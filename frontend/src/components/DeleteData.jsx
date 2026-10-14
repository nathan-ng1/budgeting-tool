import { useEffect, useState } from "react";

import { downloadBackup, fetchResetSummary, resetDatabase } from "../lib/dataApi.js";

// The danger area at the very bottom of Settings (Issue #201, ADR-0030): a
// dialog that lists what "Delete data and reset dashboard" will lose, then
// gates the final button behind a Backup (or an explicit "no Backup" tick) and
// a typed DELETE. The server checks the typed word too.

const CONFIRMATION = "DELETE";

const count = (n) => n.toLocaleString("en-US");
const plural = (n, one, many = `${one}s`) => `${count(n)} ${n === 1 ? one : many}`;

export default function DeleteData({ onReset = () => window.location.reload() }) {
  const [open, setOpen] = useState(false);
  const [summary, setSummary] = useState(null);
  const [backedUp, setBackedUp] = useState(false);
  const [noBackup, setNoBackup] = useState(false);
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open) {
      return undefined;
    }
    const controller = new AbortController();

    fetchResetSummary({ signal: controller.signal })
      .then(setSummary)
      .catch((cause) => {
        if (cause.name !== "AbortError") {
          setError(cause.message);
        }
      });

    return () => controller.abort();
  }, [open]);

  function show() {
    setSummary(null);
    setBackedUp(false);
    setNoBackup(false);
    setTyped("");
    setError(null);
    setOpen(true);
  }

  async function backUp() {
    setBusy(true);
    setError(null);
    try {
      await downloadBackup();
      setBackedUp(true);
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
      await resetDatabase(typed);
      onReset();
    } catch (cause) {
      setError(cause.message);
    } finally {
      setBusy(false);
    }
  }

  const canDelete = summary !== null && (backedUp || noBackup) && typed === CONFIRMATION;

  return (
    <section className="danger-zone">
      <h3>Danger area</h3>
      <p className="card__note">Deletes everything you have put in the Dashboard and starts again from scratch.</p>
      <button type="button" className="button button--warning" onClick={show}>
        Delete data and reset dashboard
      </button>

      {open && (
        <div className="danger-zone__backdrop">
          <div className="danger-zone__dialog" role="dialog" aria-modal="true" aria-labelledby="delete-data-title">
            <h4 id="delete-data-title">Delete data and reset dashboard</h4>
            {error !== null && (
              <p className="state state--error" role="alert">
                {error}
              </p>
            )}

            <p>This will permanently delete:</p>
            {summary && (
              <ul>
                <li>{plural(summary.transactions, "Transaction")}</li>
                <li>{plural(summary.recurring_rules, "Recurring Transactions Config rule")}</li>
                <li>{plural(summary.category_budgets, "Category Budget")}</li>
                <li>{plural(summary.custom_categories, "custom Category", "custom Categories")}</li>
                <li>{plural(summary.goals, "Goal")}</li>
                <li>{plural(summary.display_settings, "Display Setting")}</li>
                <li>
                  the Database file <span className="danger-zone__path">{summary.path}</span>
                </li>
                <li>{plural(summary.pre_migration_files, "pre-migration copy", "pre-migration copies")} beside it</li>
              </ul>
            )}
            <p className="card__note">
              Your Processed archive, your Transactions Inbox and the browser&apos;s saved theme and Financial Year
              choice are not touched.
            </p>

            <div className="danger-zone__step">
              <button type="button" className="button button--quiet" disabled={busy} onClick={backUp}>
                Download Backup first
              </button>
              {backedUp && <span className="danger-zone__done">Backup downloaded</span>}
            </div>
            <label className="danger-zone__check">
              <input type="checkbox" checked={noBackup} onChange={(event) => setNoBackup(event.target.checked)} />
              I understand this cannot be undone and I have no Backup
            </label>

            <label className="danger-zone__confirm">
              Type {CONFIRMATION} to confirm
              <input type="text" value={typed} autoComplete="off" onChange={(event) => setTyped(event.target.value)} />
            </label>

            <div className="danger-zone__actions">
              <button type="button" className="button button--warning" disabled={!canDelete || busy} onClick={confirm}>
                Delete everything
              </button>
              <button type="button" className="button button--quiet" disabled={busy} onClick={() => setOpen(false)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
