import { useCallback, useEffect, useState } from "react";

import { blankValues, changesFrom } from "../lib/budgetEditorForm.js";
import { deleteCategoryBudget, fetchBudgetEditor, saveCategoryBudget } from "../lib/budgetsApi.js";
import { financialYearFor } from "../lib/financialYear.js";
import MonthSelector from "./MonthSelector.jsx";

function currentMonth() {
  const today = new Date();
  return { year: today.getFullYear(), month: today.getMonth() + 1 };
}

export default function Budget() {
  // No Full year pill yet (Issue #62 - the read-only annual grid is Issue
  // #64), so there is always exactly one month selected, defaulting to the
  // current one - unlike Overview's Full year default (ADR-0011).
  const [selected, setSelected] = useState(currentMonth);
  const [editor, setEditor] = useState(null);
  const [values, setValues] = useState({});
  const [initial, setInitial] = useState({});
  const [error, setError] = useState(null);
  const [saveError, setSaveError] = useState(null);
  const [saving, setSaving] = useState(false);

  const financialYear = financialYearFor(selected.year, selected.month);

  const load = useCallback(async (month, signal) => {
    const loaded = await fetchBudgetEditor(month, { signal });
    const asValues = blankValues(loaded);
    setEditor(loaded);
    setValues(asValues);
    setInitial(asValues);
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    setError(null);
    setSaveError(null);
    setEditor(null);
    load(selected, controller.signal).catch((cause) => {
      if (cause.name !== "AbortError") {
        setError(cause.message);
      }
    });

    return () => controller.abort();
  }, [selected, load]);

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
      await load(selected);
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
          <p className="card__note">Set this month&rsquo;s Category Budgets, then Save to apply them.</p>
        </div>
        <button type="button" className="button" disabled={saving || changes.length === 0} onClick={save}>
          Save budgets
        </button>
      </div>

      <MonthSelector financialYear={financialYear} selected={selected} onSelect={setSelected} includeFullYear={false} />

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

      {error === null && editor === null && <p className="state">Loading this month&rsquo;s Category Budgets&hellip;</p>}

      {editor !== null && (
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Category</th>
                <th scope="col" className="table__num">
                  Budgeted Amount
                </th>
              </tr>
            </thead>
            {Object.entries(editor).map(([type, rows]) => (
              <tbody key={type}>
                <tr>
                  <th scope="colgroup" colSpan={2} className="table__section">
                    {type}
                  </th>
                </tr>
                {rows.map(({ category }) => (
                  <tr key={category}>
                    <td>{category}</td>
                    <td className="table__num">
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        className="budget-amount-input"
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
    </section>
  );
}
