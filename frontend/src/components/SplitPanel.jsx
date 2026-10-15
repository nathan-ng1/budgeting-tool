import { useEffect, useState } from "react";

import { fetchMonthOverview } from "../lib/api.js";
import { previewSplit, splitSavings } from "../lib/goalsApi.js";
import { plural } from "../lib/goalFigures.js";
import { loadLastSplit, saveLastSplit } from "../lib/lastSplit.js";
import { useMoney } from "../lib/settings.jsx";

// Mirrors SPLIT_REMAINDER_CATEGORIES in src/dashboard/goals.py; no endpoint exposes
// the list, so the two are kept in step by hand.
const REMAINDER_CATEGORIES = ["Savings", "Investments"];

// Percentages are compared in hundredths of a percent so 33.33 + 33.33 + 33.34
// is exactly 100, not 99.99999999999999.
const hundredths = (text) => Math.round(Number(text) * 100);

// The Split savings panel that slides down from the Goals header (Goals spec
// section 9). It gathers a total, a date and a percentage per active Goal; the
// backend owns the allocation (largest-remainder cents), so the preview below
// the form is the backend's own answer to the same request that Write split
// then sends - never a client-side recomputation.
export default function SplitPanel({ goals, today, month, onWritten, onClose }) {
  const { preciseMoney } = useMoney();
  const [total, setTotal] = useState("");
  const [date, setDate] = useState(today);
  const [percents, setPercents] = useState(() => {
    const last = loadLastSplit();
    return Object.fromEntries(goals.map((goal) => [goal.id, last[goal.id] === undefined ? "" : String(last[goal.id])]));
  });
  const [category, setCategory] = useState(REMAINDER_CATEGORIES[0]);
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(null);
  const [confirmation, setConfirmation] = useState(null);
  const [saving, setSaving] = useState(false);

  // Prefill the total from the month's Unallocated when it is positive, unless
  // the user has already typed one.
  useEffect(() => {
    const controller = new AbortController();
    fetchMonthOverview(month, { signal: controller.signal })
      .then((overview) => {
        const unallocated = overview?.stat_tiles?.unallocated;
        if (typeof unallocated === "number" && unallocated > 0) {
          setTotal((typed) => (typed === "" ? String(unallocated) : typed));
        }
      })
      .catch(() => {
        // The prefill is a convenience: without it the total is just typed.
      });
    return () => controller.abort();
  }, [month.year, month.month]);

  const sum = goals.reduce((acc, goal) => acc + (hundredths(percents[goal.id] || 0) || 0), 0);
  const overCap = sum > 10000;
  const request =
    Number(total) > 0 && date !== "" && !overCap
      ? {
          total: Number(total),
          date,
          allocations: goals
            .filter((goal) => percents[goal.id] !== "")
            .map((goal) => ({ goal_id: goal.id, percent: Number(percents[goal.id]) })),
          remainder_category: category,
        }
      : null;
  const requestKey = JSON.stringify(request);

  // The live preview: ask the backend what this exact request would write.
  useEffect(() => {
    if (request === null) {
      setRows(null);
      setError(null);
      return undefined;
    }
    const controller = new AbortController();
    previewSplit(request, { signal: controller.signal })
      .then((preview) => {
        setError(null);
        setRows(preview.rows);
      })
      .catch((cause) => {
        if (cause.name !== "AbortError") {
          setRows(null);
          setError(cause.message);
        }
      });
    return () => controller.abort();
  }, [requestKey]);

  function edit(setter) {
    return (event) => {
      setConfirmation(null);
      setter(event.target.value);
    };
  }

  async function write() {
    setSaving(true);
    try {
      const written = await splitSavings(request);
      saveLastSplit(Object.fromEntries(request.allocations.map((a) => [a.goal_id, a.percent])));
      setConfirmation(describeWrite(written.rows, preciseMoney));
      setRows(null);
      setError(null);
      await onWritten();
    } catch (cause) {
      setError(cause.message);
    } finally {
      setSaving(false);
    }
  }

  const shownError = overCap ? "The percentages add up to more than 100%." : error;

  return (
    <form
      className="rule-form goals__form goals__split"
      aria-label="Split savings"
      onSubmit={(event) => {
        event.preventDefault();
        write();
      }}
    >
      <div className="rule-form__grid">
        <label className="field">
          <span className="field__label">Total to split</span>
          <input type="number" min="0.01" step="0.01" value={total} onChange={edit(setTotal)} />
        </label>
        <label className="field">
          <span className="field__label">Date</span>
          <input type="date" value={date} onChange={edit(setDate)} />
        </label>
        {goals.map((goal) => (
          <label className="field" key={goal.id}>
            <span className="field__label">{goal.title} percentage</span>
            <input
              type="number"
              min="0"
              max="100"
              step="0.01"
              value={percents[goal.id]}
              onChange={(event) => {
                setConfirmation(null);
                setPercents({ ...percents, [goal.id]: event.target.value });
              }}
            />
          </label>
        ))}
        <label className="field">
          <span className="field__label">Remainder Category</span>
          <select value={category} onChange={edit(setCategory)}>
            {REMAINDER_CATEGORIES.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <p className="field__hint">
        {Math.max(0, (10000 - sum) / 100)}% is left over and goes to {category}.
      </p>

      {shownError !== null && (
        <p className="field__hint field__hint--error" role="alert">
          {shownError}
        </p>
      )}

      {rows !== null && rows.length > 0 && (
        <div className="table-scroll">
          <table className="table" aria-label="Transactions to be written">
            <thead>
              <tr>
                <th scope="col">Category</th>
                <th scope="col">Notes</th>
                <th scope="col">Amount</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={index}>
                  <td>{row.category}</td>
                  <td>{row.notes}</td>
                  <td className="table__num">{preciseMoney(row.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {confirmation !== null && <p className="goals__confirmation">{confirmation}</p>}

      <div className="rule-form__actions">
        <button type="submit" className="button" disabled={saving || request === null || rows === null || overCap}>
          Write split
        </button>
        <button type="button" className="button button--quiet" onClick={onClose}>
          Close
        </button>
      </div>
    </form>
  );
}

// "Wrote 3 Transactions totalling $1,240.00: 2 Contributions and $310.00 to Savings."
function describeWrite(rows, preciseMoney) {
  const cents = (row) => Math.round(row.amount * 100);
  const total = rows.reduce((sum, row) => sum + cents(row), 0) / 100;
  const contributions = rows.filter((row) => row.goal_id !== null);
  const remainder = rows.find((row) => row.goal_id === null);

  const parts = [];
  if (contributions.length > 0) {
    parts.push(plural(contributions.length, "Contribution"));
  }
  if (remainder) {
    parts.push(`${preciseMoney(remainder.amount)} to ${remainder.category}`);
  }
  return `Wrote ${plural(rows.length, "Transaction")} totalling ${preciseMoney(total)}: ${parts.join(" and ")}.`;
}
