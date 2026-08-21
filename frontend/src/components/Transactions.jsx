import { useEffect, useMemo, useState } from "react";

import { FINANCIAL_YEAR_START_MONTH, financialYearFor } from "../lib/financialYear.js";
import { preciseMoney } from "../lib/format.js";
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
import { fetchTransactions } from "../lib/transactionsApi.js";

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
];

function ariaSortFor(sort, key) {
  if (sort.sortKey !== key) {
    return "none";
  }
  return sort.sortDirection === "asc" ? "ascending" : "descending";
}

export default function Transactions() {
  const [transactions, setTransactions] = useState(null);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [sort, setSort] = useState(DEFAULT_SORT);

  const financialYear = currentFinancialYear();

  useEffect(() => {
    const controller = new AbortController();

    setError(null);
    setTransactions(null);
    fetchTransactions(
      { year: currentFinancialYear(), month: FINANCIAL_YEAR_START_MONTH },
      { signal: controller.signal },
    )
      .then(setTransactions)
      .catch((cause) => {
        if (cause.name !== "AbortError") {
          setError(cause.message);
        }
      });

    return () => controller.abort();
  }, []);

  const categories = useMemo(() => categoryOptions(transactions ?? []), [transactions]);
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
      <h3>Transactions</h3>

      {transactions === null && <p className="state">Loading the Transactions&hellip;</p>}

      {transactions !== null && transactions.length === 0 && <p className="state">No Transactions yet.</p>}

      {transactions !== null && transactions.length > 0 && (
        <>
          <div className="filters">
            <label className="field">
              <span className="field__label">Category</span>
              <select value={filters.category} onChange={(event) => setFilter("category", event.target.value)}>
                <option value={ALL_CATEGORIES}>{ALL_CATEGORIES}</option>
                {categories.map((category) => (
                  <option key={category}>{category}</option>
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
                  {visible.map((transaction) => (
                    <tr key={transaction.id}>
                      <td>{transaction.date}</td>
                      <td className="table__num">{preciseMoney(transaction.amount)}</td>
                      <td>{transaction.type}</td>
                      <td>{transaction.category}</td>
                      <td>{transaction.notes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}
