import { useCallback, useEffect, useMemo, useState } from "react";

import { categoryLabel, emojiLookup, groupByType } from "../lib/categories.js";
import { FINANCIAL_YEAR_START_MONTH, financialYearFor } from "../lib/financialYear.js";
import { preciseMoney } from "../lib/format.js";
import { blankValues, toPayload, valuesFrom, withType } from "../lib/transactionForm.js";
import {
  ALL_CATEGORIES,
  ALL_MONTHS,
  ALL_TYPES,
  TYPES,
  categoryOptions,
  monthOptions,
  nextSort,
  visibleTransactions,
} from "../lib/transactionsView.js";
import {
  createTransaction,
  deleteTransaction,
  fetchCategories,
  fetchTransactions,
  updateTransaction,
} from "../lib/transactionsApi.js";

function currentFinancialYear() {
  const today = new Date();
  return financialYearFor(today.getFullYear(), today.getMonth() + 1);
}

const DEFAULT_FILTERS = { category: ALL_CATEGORIES, month: ALL_MONTHS, type: ALL_TYPES, search: "" };
const DEFAULT_SORT = { sortKey: "date", sortDirection: "desc" };

const COLUMNS = [
  { key: "date", label: "Date", sortable: true },
  { key: "amount", label: "Amount", sortable: true, numeric: true },
  { key: "type", label: "Type" },
  { key: "category", label: "Category" },
  { key: "notes", label: "Notes" },
  { key: "actions", label: "" },
];

function ariaSortFor(sort, key) {
  if (sort.sortKey !== key) {
    return "none";
  }
  return sort.sortDirection === "asc" ? "ascending" : "descending";
}

export default function Transactions() {
  const [transactions, setTransactions] = useState(null);
  const [categories, setCategories] = useState({});
  const [categoryList, setCategoryList] = useState([]);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [sort, setSort] = useState(DEFAULT_SORT);
  const [adding, setAdding] = useState(null);
  const [editing, setEditing] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [deleteError, setDeleteError] = useState(null);

  const financialYear = currentFinancialYear();

  const load = useCallback(async (signal) => {
    const [loadedTransactions, loadedCategories] = await Promise.all([
      fetchTransactions({ year: currentFinancialYear(), month: FINANCIAL_YEAR_START_MONTH }, { signal }),
      fetchCategories({ signal }),
    ]);
    setTransactions(loadedTransactions);
    setCategories(groupByType(loadedCategories));
    setCategoryList(loadedCategories);
  }, []);

  // The same flat list `categories` above was grouped from, kept around
  // separately so the table/filter/form can show a Category's emoji (Issue
  // #92) without the grouped Type->names shape changing.
  const emoji = useMemo(() => emojiLookup(categoryList), [categoryList]);

  useEffect(() => {
    const controller = new AbortController();

    setError(null);
    setTransactions(null);
    load(controller.signal).catch((cause) => {
      if (cause.name !== "AbortError") {
        setError(cause.message);
      }
    });

    return () => controller.abort();
  }, [load]);

  const categoryFilterOptions = useMemo(() => categoryOptions(transactions ?? []), [transactions]);
  const months = useMemo(() => monthOptions(financialYear), [financialYear]);
  // Everything below derives from the already-fetched array - no filter,
  // search, or sort change ever triggers another fetchTransactions call.
  const visible = useMemo(
    () => (transactions === null ? [] : visibleTransactions(transactions, filters, sort)),
    [transactions, filters, sort],
  );

  function setFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  function handleSort(key) {
    setSort((current) => nextSort(current, key));
  }

  async function saveNew(values) {
    const created = await createTransaction(toPayload(values));
    setTransactions((current) => [...current, created]);
    setAdding(null);
  }

  async function saveEdit(values) {
    const updated = await updateTransaction(editing.id, toPayload(values));
    setTransactions((current) => current.map((transaction) => (transaction.id === updated.id ? updated : transaction)));
    setEditing(null);
  }

  function startDelete(transaction) {
    setDeleteError(null);
    setDeletingId(transaction.id);
  }

  function cancelDelete() {
    setDeleteError(null);
    setDeletingId(null);
  }

  async function confirmDelete(transaction) {
    setDeleteError(null);
    try {
      await deleteTransaction(transaction.id);
      setTransactions((current) => current.filter((other) => other.id !== transaction.id));
      setDeletingId(null);
    } catch (cause) {
      setDeleteError(cause.message);
    }
  }

  if (error !== null) {
    return (
      <section className="card">
        <h3>Transactions</h3>
        <p className="state state--error" role="alert">
          {error}
        </p>
      </section>
    );
  }

  return (
    <section className="card">
      <div className="card__head">
        <h3>Transactions</h3>
        {adding === null && (
          <button type="button" className="button" onClick={() => setAdding(blankValues())}>
            Add transaction
          </button>
        )}
      </div>

      {adding !== null && (
        <TransactionForm
          initial={adding}
          categories={categories}
          emoji={emoji}
          onCancel={() => setAdding(null)}
          onSave={saveNew}
        />
      )}

      {transactions === null && <p className="state">Loading the Transactions&hellip;</p>}

      {transactions !== null && transactions.length === 0 && <p className="state">No Transactions yet.</p>}

      {transactions !== null && transactions.length > 0 && (
        <>
          <div className="filters">
            <label className="field">
              <span className="field__label">Category</span>
              <select value={filters.category} onChange={(event) => setFilter("category", event.target.value)}>
                <option value={ALL_CATEGORIES}>{ALL_CATEGORIES}</option>
                {categoryFilterOptions.map((category) => (
                  <option key={category} value={category}>
                    {categoryLabel(category, emoji)}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span className="field__label">Month</span>
              <select value={filters.month} onChange={(event) => setFilter("month", event.target.value)}>
                <option value={ALL_MONTHS}>{ALL_MONTHS}</option>
                {months.map(({ value, label }) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span className="field__label">Type</span>
              <select value={filters.type} onChange={(event) => setFilter("type", event.target.value)}>
                <option value={ALL_TYPES}>{ALL_TYPES}</option>
                {TYPES.map((type) => (
                  <option key={type}>{type}</option>
                ))}
              </select>
            </label>

            <label className="field field--wide">
              <span className="field__label">Search Notes</span>
              <input
                type="search"
                value={filters.search}
                onChange={(event) => setFilter("search", event.target.value)}
                placeholder="Search Notes"
              />
            </label>
          </div>

          {visible.length === 0 && <p className="state">No Transactions match.</p>}

          {visible.length > 0 && (
            <div className="table-scroll">
              <table className="table">
                <thead>
                  <tr>
                    {COLUMNS.map(({ key, label, sortable, numeric }) => (
                      <th
                        key={key}
                        scope="col"
                        className={numeric ? "table__num" : undefined}
                        aria-sort={sortable ? ariaSortFor(sort, key) : undefined}
                      >
                        {sortable ? (
                          <button type="button" className="table__sort" onClick={() => handleSort(key)}>
                            {label}
                          </button>
                        ) : (
                          label
                        )}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {visible.map((transaction) => {
                    if (editing !== null && editing.id === transaction.id) {
                      return (
                        <EditableRow
                          key={transaction.id}
                          initial={editing.values}
                          categories={categories}
                          emoji={emoji}
                          onCancel={() => setEditing(null)}
                          onSave={saveEdit}
                        />
                      );
                    }

                    return (
                      <tr key={transaction.id}>
                        <td>{transaction.date}</td>
                        <td className="table__num">{preciseMoney(transaction.amount)}</td>
                        <td>{transaction.type}</td>
                        <td>{categoryLabel(transaction.category, emoji)}</td>
                        <td>{transaction.notes}</td>
                        <td className="table__actions">
                          {deletingId === transaction.id ? (
                            <>
                              {deleteError !== null && (
                                <span className="state state--error" role="alert">
                                  {deleteError}
                                </span>
                              )}
                              <button
                                type="button"
                                className="button button--quiet button--danger"
                                onClick={() => confirmDelete(transaction)}
                              >
                                Confirm delete?
                              </button>
                              <button type="button" className="button button--quiet" onClick={cancelDelete}>
                                Cancel
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                type="button"
                                className="button button--quiet"
                                aria-label={`Edit ${transaction.notes}`}
                                onClick={() => setEditing({ id: transaction.id, values: valuesFrom(transaction) })}
                              >
                                Edit
                              </button>
                              <button
                                type="button"
                                className="button button--quiet button--danger"
                                aria-label={`Delete ${transaction.notes}`}
                                onClick={() => startDelete(transaction)}
                              >
                                Delete
                              </button>
                            </>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}

// Shared state behind TransactionForm (a block above the table, for Add) and
// EditableRow (in-row, for Edit) - same values/error/saving/save behaviour,
// just wrapped in a <form> versus a <tr> because the two live in different
// places on the page (see Issue #35).
function useTransactionEditor(initial, categories, onSave) {
  const [values, setValues] = useState(initial);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const types = Object.keys(categories);
  const allowed = categories[values.type] ?? [];

  function set(field, value) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  function setType(type) {
    setValues((current) => withType(current, type, categories));
  }

  async function save() {
    setError(null);
    setSaving(true);
    try {
      await onSave(values);
    } catch (cause) {
      // The store is the authority on what a valid transaction is, so its
      // message is the one worth showing - the form/row stays open to be corrected.
      setError(cause.message);
    } finally {
      setSaving(false);
    }
  }

  return { values, set, setType, types, allowed, error, saving, save };
}

function TransactionForm({ initial, categories, emoji, onCancel, onSave }) {
  const { values, set, setType, types, allowed, error, saving, save } = useTransactionEditor(
    initial,
    categories,
    onSave,
  );

  function submit(event) {
    event.preventDefault();
    save();
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
          <span className="field__label">Date</span>
          <input type="date" required value={values.date} onChange={(event) => set("date", event.target.value)} />
        </label>

        <label className="field">
          <span className="field__label">Amount</span>
          <input
            type="number"
            step="0.01"
            min="0.01"
            required
            value={values.amount}
            onChange={(event) => set("amount", event.target.value)}
          />
        </label>

        <label className="field">
          <span className="field__label">Type</span>
          <select value={values.type} onChange={(event) => setType(event.target.value)}>
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
      </div>

      <div className="rule-form__actions">
        <button type="submit" className="button" disabled={saving}>
          Save transaction
        </button>
        <button type="button" className="button button--quiet" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}

function EditableRow({ initial, categories, emoji, onCancel, onSave }) {
  const { values, set, setType, types, allowed, error, saving, save } = useTransactionEditor(
    initial,
    categories,
    onSave,
  );

  return (
    <tr>
      <td>
        <input type="date" aria-label="Date" value={values.date} onChange={(event) => set("date", event.target.value)} />
      </td>
      <td>
        <input
          type="number"
          step="0.01"
          min="0.01"
          aria-label="Amount"
          value={values.amount}
          onChange={(event) => set("amount", event.target.value)}
        />
      </td>
      <td>
        <select aria-label="Type" value={values.type} onChange={(event) => setType(event.target.value)}>
          {types.map((type) => (
            <option key={type}>{type}</option>
          ))}
        </select>
      </td>
      <td>
        <select aria-label="Category" value={values.category} onChange={(event) => set("category", event.target.value)}>
          <option value="">Choose a Category</option>
          {allowed.map((category) => (
            <option key={category} value={category}>
              {categoryLabel(category, emoji)}
            </option>
          ))}
        </select>
      </td>
      <td>
        <input type="text" aria-label="Notes" value={values.notes} onChange={(event) => set("notes", event.target.value)} />
      </td>
      <td className="table__actions">
        {error !== null && (
          <span className="state state--error" role="alert">
            {error}
          </span>
        )}
        <button type="button" className="button button--quiet" disabled={saving} onClick={save}>
          Save
        </button>
        <button type="button" className="button button--quiet" onClick={onCancel}>
          Cancel
        </button>
      </td>
    </tr>
  );
}
