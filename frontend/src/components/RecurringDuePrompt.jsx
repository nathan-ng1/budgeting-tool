import { useEffect, useState } from "react";

import { fetchRecurringDueCount, runRecurringRules } from "../lib/recurringApi.js";

function describeDue(due) {
  return due === 1 ? "1 recurring transaction is due." : `${due} recurring transactions are due.`;
}

function describeRun(written) {
  if (written === 0) {
    return "Nothing new to add.";
  }
  return `${written} transaction${written === 1 ? "" : "s"} added.`;
}

// The Dashboard's prompt for Recurring Transactions Config occurrences that
// are due but not yet in the Transaction Log (Issue #240). A Buyer has no
// Statement Export to expand them, so this is how they surface. Asking for
// the count writes nothing: occurrences are only written by the click, so a
// Transaction the user deleted never silently comes back. Renders nothing
// while there is nothing due - or if the count can't be read, since a missing
// prompt is a smaller problem than an error banner over a working Dashboard.
export default function RecurringDuePrompt({ onRun }) {
  const [due, setDue] = useState(0);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  useEffect(() => {
    const controller = new AbortController();

    fetchRecurringDueCount({ signal: controller.signal })
      .then((loaded) => setDue(loaded?.due ?? 0))
      .catch(() => {
        // Quiet, as above: no prompt rather than an error.
      });

    return () => controller.abort();
  }, []);

  async function run() {
    setError(null);
    setRunning(true);
    try {
      const { written } = await runRecurringRules();
      setDue(0);
      setResult(describeRun(written));
      onRun?.(written);
    } catch (cause) {
      setError(cause.message);
    } finally {
      setRunning(false);
    }
  }

  if (result !== null) {
    return (
      <p className="due-prompt" role="status">
        {result}
      </p>
    );
  }

  if (due === 0) {
    return null;
  }

  return (
    <section className="due-prompt" aria-label="Recurring transactions due">
      <p className="due-prompt__text">{describeDue(due)}</p>
      <button type="button" className="button" disabled={running} onClick={run}>
        {running ? "Running…" : "Run now"}
      </button>
      {error !== null && (
        <p className="state state--error due-prompt__error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
