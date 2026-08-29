import { useCallback, useEffect, useMemo, useState } from "react";

import { categoryLabel, emojiLookup, groupByType } from "../lib/categories.js";
import {
  createRecurringRule,
  deleteRecurringRule,
  fetchCategories,
  fetchRecurringRules,
  runRecurringRules,
  updateRecurringRule,
} from "../lib/recurringApi.js";
import { preciseMoney } from "../lib/format.js";
import {
  FREQUENCIES,
  blankValues,
  toPayload,
  valuesFrom,
  withFrequency,
  withStartDate,
  withType,
} from "../lib/ruleForm.js";

const COLUMNS = ["Amount", "Type", "Category", "Notes", "Frequency", "Start Date", "End Date", ""];

// "Every 2 weeks on Wednesday" reads better than an Interval column and a Day
// column the reader has to combine themselves.
function schedule(rule) {
  const unit = rule.frequency === "Weekly" ? "week" : "month";
  const every = rule.interval === 1 ? `Every ${unit}` : `Every ${rule.interval} ${unit}s`;
  return rule.frequency === "Weekly" ? `${every} on ${rule.day}` : `${every} on day ${rule.day}`;
}

function describeRun(written) {
  if (written === 0) {
    return "Nothing new to add.";
  }
  return `${written} transaction${written === 1 ? "" : "s"} added.`;
}

export default function RecurringRules() {
  const [rules, setRules] = useState(null);
  const [categories, setCategories] = useState({});
  const [categoryList, setCategoryList] = useState([]);
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState(null);
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState(null);

  const load = useCallback(async (signal) => {
    const [loadedRules, loadedCategories] = await Promise.all([
      fetchRecurringRules({ signal }),
      fetchCategories({ signal }),
    ]);
    setRules(loadedRules);
    setCategories(groupByType(loadedCategories));
    setCategoryList(loadedCategories);
  }, []);

  // The same flat list `categories` above was grouped from, kept around
  // separately so the table/select can show a Category's emoji (Issue #92)
  // without every consumer of the grouped Type->names shape having to
  // change too.
  const emoji = useMemo(() => emojiLookup(categoryList), [categoryList]);

  useEffect(() => {
    const controller = new AbortController();

    load(controller.signal).catch((cause) => {
      if (cause.name !== "AbortError") {
        setError(cause.message);
      }
    });

    return () => controller.abort();
  }, [load]);

  async function save(values) {
    const payload = toPayload(values);
    const saved =
      editing.id === null ? await createRecurringRule(payload) : await updateRecurringRule(editing.id, payload);

    setRules((current) =>
      editing.id === null ? [...current, saved] : current.map((rule) => (rule.id === saved.id ? saved : rule)),
    );
    setEditing(null);
  }

  async function runRules() {
    setError(null);
    setRunResult(null);
    setRunning(true);
    try {
      const { written } = await runRecurringRules();
      setRunResult(describeRun(written));
    } catch (cause) {
      setError(cause.message);
    } finally {
      setRunning(false);
    }
  }

  async function remove(rule) {
    setError(null);
    try {
      await deleteRecurringRule(rule.id);
      setRules((current) => current.filter((other) => other.id !== rule.id));
    } catch (cause) {
      setError(cause.message);
    }
  }

  if (error !== null && rules === null) {
    return (
      <section className="card">
        <h3>Recurring Transactions</h3>
        <p className="state state--error" role="alert">
          {error}
        </p>
      </section>
    );
  }

  return (
    <section className="card">
      <div className="card__head">
        <div>
          <h3>Recurring Transactions</h3>
          <p className="card__note">
            Predictable items expanded into the Transaction Log via an automated Statement Export or manual run.
          </p>
        </div>
        {editing === null && (
          <div className="card__actions">
            <button
              type="button"
              className="button"
              disabled={rules === null || rules.length === 0 || running}
              onClick={runRules}
            >
              {running ? "Running…" : "Run now"}
            </button>
            <button type="button" className="button" onClick={() => setEditing({ id: null, values: blankValues() })}>
              Add rule
            </button>
          </div>
        )}
      </div>

      {runResult !== null && (
        <p className="state" role="status">
          {runResult}
        </p>
      )}

      {error !== null && (
        <p className="state state--error" role="alert">
          {error}
        </p>
      )}

      {editing !== null && (
        <RuleForm
          key={editing.id ?? "new"}
          initial={editing.values}
          categories={categories}
          emoji={emoji}
          onCancel={() => setEditing(null)}
          onSave={save}
        />
      )}

      {rules === null && <p className="state">Loading the Recurring Transactions Config&hellip;</p>}

      {rules !== null && rules.length === 0 && <p className="state">No rules in the Recurring Transactions Config yet.</p>}

      {rules !== null && rules.length > 0 && (
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                {COLUMNS.map((column, index) => (
                  <th key={column || index} scope="col">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={rule.id}>
                  <td className="table__num">{preciseMoney(rule.amount)}</td>
                  <td>{rule.type}</td>
                  <td>{categoryLabel(rule.category, emoji)}</td>
                  <td>{rule.notes}</td>
                  <td>{schedule(rule)}</td>
                  <td>{rule.start_date}</td>
                  <td>{rule.end_date ?? "—"}</td>
                  <td className="table__actions">
                    <button
                      type="button"
                      className="button button--quiet"
                      aria-label={`Edit ${rule.notes}`}
                      onClick={() => setEditing({ id: rule.id, values: valuesFrom(rule) })}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="button button--quiet button--danger"
                      aria-label={`Delete ${rule.notes}`}
                      onClick={() => remove(rule)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function RuleForm({ initial, categories, emoji, onCancel, onSave }) {
  const [values, setValues] = useState(initial);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const types = Object.keys(categories);
  const allowed = categories[values.type] ?? [];

  function set(field, value) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await onSave(values);
    } catch (cause) {
      // The store is the authority on what a valid rule is, so its message is
      // the one worth showing - the form stays open to be corrected.
      setError(cause.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="rule-form" onSubmit={submit}>
      {error !== null && (
        <p className="state state--error" role="alert">
          {error}
        </p>
      )}

      <div className="rule-form__grid">
        <label className="field">
          <span className="field__label">Amount</span>
          <input
            type="number"
            step="0.01"
            min="0"
            required
            value={values.amount}
            onChange={(event) => set("amount", event.target.value)}
          />
        </label>

        <label className="field">
          <span className="field__label">Type</span>
          <select value={values.type} onChange={(event) => setValues(withType(values, event.target.value, categories))}>
            {types.map((type) => (
              <option key={type}>{type}</option>
            ))}
          </select>
        </label>

        <label className="field">
          <span className="field__label">Category</span>
          <select value={values.category} onChange={(event) => set("category", event.target.value)} required>
            <option value="">Choose a Category</option>
            {allowed.map((category) => (
              <option key={category} value={category}>
                {categoryLabel(category, emoji)}
              </option>
            ))}
          </select>
        </label>

        <label className="field field--wide">
          <span className="field__label">Notes</span>
          <input type="text" required value={values.notes} onChange={(event) => set("notes", event.target.value)} />
        </label>

        <label className="field">
          <span className="field__label">Frequency</span>
          <select value={values.frequency} onChange={(event) => setValues(withFrequency(values, event.target.value))}>
            {FREQUENCIES.map((frequency) => (
              <option key={frequency}>{frequency}</option>
            ))}
          </select>
        </label>

        <label className="field">
          <span className="field__label">Interval</span>
          <input
            type="number"
            min="1"
            step="1"
            required
            value={values.interval}
            onChange={(event) => set("interval", event.target.value)}
          />
        </label>

        <label className="field">
          <span className="field__label">Start Date</span>
          <input
            type="date"
            required
            value={values.start_date}
            onChange={(event) => setValues(withStartDate(values, event.target.value))}
          />
        </label>

        {/* Day follows Start Date. A Weekly rule's Day is fully determined by
            it, so it is shown rather than entered; a Monthly rule's can be
            pushed past the start's day-of-month (Day 31 starting 28 Feb), so
            that one stays editable. */}
        {values.frequency === "Weekly" ? (
          <div className="field">
            <span className="field__label" id="day-label">
              Day
            </span>
            <output className="field__derived" aria-labelledby="day-label">
              {values.day}
            </output>
          </div>
        ) : (
          <label className="field">
            <span className="field__label">Day</span>
            <input
              type="number"
              min="1"
              max="31"
              step="1"
              required
              value={values.day}
              onChange={(event) => set("day", Number(event.target.value))}
            />
          </label>
        )}

        <label className="field">
          <span className="field__label">End Date</span>
          <input type="date" value={values.end_date} onChange={(event) => set("end_date", event.target.value)} />
        </label>
      </div>

      <div className="rule-form__actions">
        <button type="submit" className="button" disabled={saving}>
          Save rule
        </button>
        <button type="button" className="button button--quiet" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
