import { useCallback, useEffect, useRef, useState } from "react";

import { valuesFrom, changesFrom } from "../lib/budgetEditorForm.js";
import { deleteCategoryBudget, fetchBudgetEditor, fetchBudgetGrid, saveCategoryBudget } from "../lib/budgetsApi.js";
import { financialYearFor, monthsOfFinancialYear } from "../lib/financialYear.js";
import { UNSET, money, signedPct } from "../lib/format.js";
import MonthSelector from "./MonthSelector.jsx";

// The trailing windows the Budget tab's dropdown offers - see
// dashboard.queries.TRAILING_WINDOWS.
const TRAILING_WINDOWS = [3, 6, 12];

function currentMonth() {
  const today = new Date();
  return { year: today.getFullYear(), month: today.getMonth() + 1 };
}

export default function Budget() {
  // `selected` is null for Full year (the read-only grid, Issue #64) or
  // `{ year, month }` for the editable per-month editor - it defaults to the
  // current month, unlike Overview's Full year default (ADR-0011), since the
  // Budget tab's primary job is editing one month at a time.
  const [selected, setSelected] = useState(currentMonth);
  // 3 matches dashboard.budgets.DEFAULT_TRAILING_WINDOW - kept in sync by
  // hand since the two live either side of the HTTP boundary.
  const [trailingWindow, setTrailingWindow] = useState(3);
  const [editor, setEditor] = useState(null);
  const [values, setValues] = useState({});
  const [initial, setInitial] = useState({});
  const [grid, setGrid] = useState(null);
  const [error, setError] = useState(null);
  const [saveError, setSaveError] = useState(null);
  const [saving, setSaving] = useState(false);

  // The Budget tab has no Financial Year switcher: every pill (Full year
  // included) always belongs to the FY containing today, the same way
  // App.jsx's Overview tab has none either (ADR-0011).
  const today = currentMonth();
  const financialYear = financialYearFor(today.year, today.month);

  // The Amount a Category is Budgeted this month doesn't depend on the
  // trailing window - only the grey historical columns do. `load` always
  // refreshes what's on screen, but only resets the Amount editing state
  // (`values`/`initial`) when the month itself changed, so switching the
  // window dropdown never discards an unsaved edit.
  const load = useCallback(async (month, window, signal, resetValues) => {
    const loaded = await fetchBudgetEditor(month, { window, signal });
    setEditor(loaded);
    if (resetValues) {
      const asValues = valuesFrom(loaded);
      setValues(asValues);
      setInitial(asValues);
    }
  }, []);

  const loadGrid = useCallback(async (year, signal) => {
    setGrid(await fetchBudgetGrid(year, { signal }));
  }, []);

  const previousMonthKey = useRef(null);

  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    setSaveError(null);

    // Full year is read-only (Issue #64), so there is no editor state to
    // keep in sync here - just the grid.
    if (selected === null) {
      setEditor(null);
      loadGrid(financialYear, controller.signal).catch((cause) => {
        if (cause.name !== "AbortError") {
          setError(cause.message);
        }
      });
      return () => controller.abort();
    }

    setGrid(null);
    const monthKey = `${selected.year}-${selected.month}`;
    const isMonthChange = previousMonthKey.current !== monthKey;
    previousMonthKey.current = monthKey;
    if (isMonthChange) {
      setEditor(null);
    }

    load(selected, trailingWindow, controller.signal, isMonthChange).catch((cause) => {
      if (cause.name !== "AbortError") {
        setError(cause.message);
      }
    });

    return () => controller.abort();
  }, [selected, trailingWindow, financialYear, load, loadGrid]);

  function set(category, value) {
    setValues((current) => ({ ...current, [category]: value }));
  }

  const changes = changesFrom(initial, values);

  async function save() {
    setSaveError(null);
    setSaving(true);
    try {
      await Promise.all(
        changes.map(({ category, amount }) =>
          amount === null
            ? deleteCategoryBudget(selected, category)
            : saveCategoryBudget(selected, category, amount),
        ),
      );
      // Re-reads rather than assuming every write landed as sent, so what's
      // on screen after Save is what the store actually holds.
      await load(selected, trailingWindow, undefined, true);
    } catch (cause) {
      setSaveError(cause.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="card">
      <div className="card__head">
        <div>
          <h3>Budget</h3>
          <p className="card__note">
            {selected === null
              ? "Full year is read-only — select a month to edit its Category Budgets."
              : "Set this month’s Category Budgets, then Save to apply them."}
          </p>
        </div>
        {selected !== null && (
          <button type="button" className="button" disabled={saving || changes.length === 0} onClick={save}>
            Save budgets
          </button>
        )}
      </div>

      <MonthSelector financialYear={financialYear} selected={selected} onSelect={setSelected} />

      {selected !== null && (
        <div className="filters">
          <label className="field">
            <span className="field__label">Trailing window</span>
            <select
              value={trailingWindow}
              onChange={(event) => setTrailingWindow(Number(event.target.value))}
            >
              {TRAILING_WINDOWS.map((months) => (
                <option key={months} value={months}>
                  {months} months
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      {error !== null && (
        <p className="state state--error" role="alert">
          {error}
        </p>
      )}

      {saveError !== null && (
        <p className="state state--error" role="alert">
          {saveError}
        </p>
      )}

      {error === null && selected !== null && editor === null && (
        <p className="state">Loading this month&rsquo;s Category Budgets&hellip;</p>
      )}

      {error === null && selected === null && grid === null && (
        <p className="state">Loading the Full year&rsquo;s Category Budgets&hellip;</p>
      )}

      {selected !== null && editor !== null && (
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Category</th>
                <th scope="col" className="table__num">
                  Last Month Actual
                </th>
                <th scope="col" className="table__num">
                  {trailingWindow}-Month Avg Actual
                </th>
                <th scope="col" className="table__num">
                  Avg Variance %
                </th>
                <th scope="col" className="table__num">
                  Budgeted Amount
                </th>
              </tr>
            </thead>
            {Object.entries(editor).map(([type, rows]) => (
              <tbody key={type}>
                <tr>
                  <th scope="colgroup" colSpan={5} className="table__section">
                    {type}
                  </th>
                </tr>
                {rows.map(({ category, last_month_actual, trailing_average_actual, average_variance_pct }) => (
                  <tr key={category}>
                    <td>{category}</td>
                    <td className="table__num muted">{money(last_month_actual)}</td>
                    <td className="table__num muted">{trailing_average_actual === null ? UNSET : money(trailing_average_actual)}</td>
                    <td className="table__num muted">{average_variance_pct === null ? UNSET : signedPct(average_variance_pct)}</td>
                    <td className="table__num">
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        className="budget__amount-input"
                        aria-label={`${category} Budgeted Amount`}
                        value={values[category] ?? ""}
                        onChange={(event) => set(category, event.target.value)}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            ))}
          </table>
        </div>
      )}

      {selected === null && grid !== null && (
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Category</th>
                {monthsOfFinancialYear(financialYear).map(({ year, month, label }) => (
                  <th key={`${year}-${month}`} scope="col" className="table__num">
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            {Object.entries(grid).map(([type, rows]) => (
              <tbody key={type}>
                <tr>
                  <th scope="colgroup" colSpan={13} className="table__section">
                    {type}
                  </th>
                </tr>
                {rows.map(({ category, amounts }) => (
                  <tr key={category}>
                    <td>{category}</td>
                    {amounts.map((amount, index) => (
                      <td key={index} className="table__num muted">
                        {amount === null ? "" : money(amount)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            ))}
          </table>
        </div>
      )}
    </section>
  );
}
