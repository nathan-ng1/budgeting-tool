import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { categoryLabel, emojiLookup, groupByType } from "../lib/categories.js";
import { FINANCIAL_YEAR_START_MONTH, financialYearFor } from "../lib/financialYear.js";
import { preciseMoney } from "../lib/format.js";
import { blankValues, toPayload, valuesFrom, withType } from "../lib/transactionForm.js";
import {
  ALL_CATEGORIES,
  ALL_MONTHS,
  ALL_TYPES,
  DEFAULT_PAGE_SIZE,
  PAGE_SIZE_OPTIONS,
  TYPES,
  categoryOptions,
  monthOptions,
  nextSort,
  pageCount,
  paginate,
  visibleTransactions,
} from "../lib/transactionsView.js";
import {
  commitImport,
  createTransaction,
  deleteTransaction,
  fetchCategories,
  fetchTransactions,
  previewImport,
  updateTransaction,
} from "../lib/transactionsApi.js";

function currentFinancialYear() {
  const today = new Date();
  return financialYearFor(today.getFullYear(), today.getMonth() + 1);
}

// The Financial Year's own bounds - July 1 through June 30 (see
// lib/financialYear.js) - the Export panel's default date range (Issue #96).
function defaultExportRange(financialYear) {
  return { start: `${financialYear}-07-01`, end: `${financialYear + 1}-06-30` };
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
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [page, setPage] = useState(1);
  const [adding, setAdding] = useState(null);
  const [editing, setEditing] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [deleteError, setDeleteError] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  // Which "…" menu panel (if any) is open - null | "export" | "import". A
  // single flag rather than one boolean/state per panel, so a third panel
  // only needs a third value here, not a third clause on every visibility
  // check below (Issue #97 code review).
  const [panel, setPanel] = useState(null);
  // The commit summary shown after a successful Import (Issue #98) - cleared
  // whenever another panel or the Add form opens, so it can't go stale.
  const [importMessage, setImportMessage] = useState(null);
  const menuRef = useRef(null);

  const financialYear = currentFinancialYear();

  // Clicking anywhere outside the "…" menu closes it, same as clicking the
  // button again - Issue #96.
  useEffect(() => {
    if (!menuOpen) {
      return undefined;
    }

    function handleClick(event) {
      if (menuRef.current !== null && !menuRef.current.contains(event.target)) {
        setMenuOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [menuOpen]);

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

  const totalPages = useMemo(() => pageCount(visible.length, pageSize), [visible.length, pageSize]);
  // Clamped rather than reset via effect, so a page that's now out of range
  // (e.g. after a filter narrows the list) just falls back to the last page.
  const currentPage = Math.min(page, totalPages);
  const pageItems = useMemo(
    () => paginate(visible, currentPage, pageSize),
    [visible, currentPage, pageSize],
  );

  function setFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
    setPage(1);
  }

  function handleSort(key) {
    setSort((current) => nextSort(current, key));
  }

  function changePageSize(size) {
    setPageSize(size);
    setPage(1);
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

  function openExport() {
    setMenuOpen(false);
    setImportMessage(null);
    setPanel("export");
  }

  function openImport() {
    setMenuOpen(false);
    setImportMessage(null);
    setPanel("import");
  }

  function closePanel() {
    setPanel(null);
  }

  // Flags a written row whose Date falls outside the Financial Year on
  // screen, since the `load()` refresh below won't surface it (Issue #98).
  async function handleImportComplete(written) {
    setPanel(null);
    const outsideCount = written.filter((row) => {
      const [year, month] = row.date.split("-").map(Number);
      return financialYearFor(year, month) !== financialYear;
    }).length;
    setImportMessage(importSummary(written.length, outsideCount));
    await load();
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
        <div className="card__actions">
          {adding === null && panel === null && (
            <button
              type="button"
              className="button"
              onClick={() => {
                setImportMessage(null);
                setAdding(blankValues());
              }}
            >
              Add transaction
            </button>
          )}
          {adding === null && editing === null && panel === null && (
            <div className="menu" ref={menuRef}>
              <button
                type="button"
                className="button button--quiet"
                aria-haspopup="true"
                aria-expanded={menuOpen}
                aria-label="More options"
                onClick={() => setMenuOpen((open) => !open)}
              >
                &hellip;
              </button>
              {menuOpen && (
                <div className="menu__list" role="menu">
                  <button type="button" role="menuitem" className="menu__item" onClick={openImport}>
                    Import transactions
                  </button>
                  <button type="button" role="menuitem" className="menu__item" onClick={openExport}>
                    Export transactions
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
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

      {panel === "export" && (
        <ExportPanel initial={defaultExportRange(financialYear)} onCancel={closePanel} />
      )}

      {panel === "import" && <ImportPanel onCancel={closePanel} onImported={handleImportComplete} />}

      {importMessage !== null && (
        <p className="state" role="status">
          {importMessage}
        </p>
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

            <label className="field">
              <span className="field__label">Rows per page</span>
              <select value={pageSize} onChange={(event) => changePageSize(Number(event.target.value))}>
                {PAGE_SIZE_OPTIONS.map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
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
                  {pageItems.map((transaction) => {
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

          {visible.length > 0 && totalPages > 1 && (
            <div className="pagination">
              <button
                type="button"
                className="button button--quiet"
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                disabled={currentPage === 1}
              >
                Previous
              </button>
              <span className="pagination__status">
                Page {currentPage} of {totalPages}
              </span>
              <button
                type="button"
                className="button button--quiet"
                onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                disabled={currentPage === totalPages}
              >
                Next
              </button>
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

function ExportPanel({ initial, onCancel }) {
  const [start, setStart] = useState(initial.start);
  const [end, setEnd] = useState(initial.end);

  return (
    <div className="rule-form">
      <div className="rule-form__grid">
        <label className="field">
          <span className="field__label">Start date</span>
          <input type="date" required value={start} onChange={(event) => setStart(event.target.value)} />
        </label>

        <label className="field">
          <span className="field__label">End date</span>
          <input type="date" required value={end} onChange={(event) => setEnd(event.target.value)} />
        </label>
      </div>

      <div className="rule-form__actions">
        <a className="button" href={`/api/transactions/export?start=${start}&end=${end}`}>
          Download CSV
        </a>
        <button type="button" className="button button--quiet" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}

// Reads a File as base64 (no data: URL prefix) - the shape
// dashboard.transactions.decode_import_file expects, since the backend's
// _read_json/_send_json handling is JSON-only, not multipart (Issue #98).
function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1] ?? "");
    reader.onerror = () => reject(reader.error ?? new Error("Could not read the selected file"));
    reader.readAsDataURL(file);
  });
}

function summariseRows(rows) {
  return {
    write: rows.filter((row) => row.outcome === "write").length,
    duplicate: rows.filter((row) => row.outcome === "duplicate").length,
    rejected: rows.filter((row) => row.outcome === "rejected").length,
  };
}

function importSummary(writtenCount, outsideCount) {
  const base = `Imported ${writtenCount} transaction${writtenCount === 1 ? "" : "s"}.`;
  if (outsideCount === 0) {
    return base;
  }
  return `${base} ${outsideCount} ${outsideCount === 1 ? "is" : "are"} outside the Financial Year currently on screen and won't appear in the table above.`;
}

// Upload -> preview -> confirm (Issue #98). The preview writes nothing; only
// "Confirm import" does, sending back exactly the to-write Candidates the
// preview returned - no re-upload of the file, no server-held state between
// the two calls.
function ImportPanel({ onCancel, onImported }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function upload() {
    if (file === null) {
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const fileBase64 = await readFileAsBase64(file);
      setPreview(await previewImport(fileBase64));
    } catch (cause) {
      setError(cause.message);
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    setError(null);
    setBusy(true);
    try {
      const { written } = await commitImport(preview.candidates);
      onImported(written);
    } catch (cause) {
      setError(cause.message);
      setBusy(false);
    }
  }

  const counts = preview === null ? null : summariseRows(preview.rows);
  const rejections = preview === null ? [] : preview.rows.filter((row) => row.outcome === "rejected");

  return (
    <div className="rule-form">
      {preview === null && (
        <>
          <p>
            Download the template, fill in your Transactions using the Category dropdowns, then come back here to
            import it.
          </p>
          <label className="field">
            <span className="field__label">Import file</span>
            <input
              type="file"
              accept=".xlsx"
              onChange={(event) => setFile(event.target.files[0] ?? null)}
            />
          </label>
        </>
      )}

      {preview !== null && (
        <div>
          <p>
            {counts.write} to write, {counts.duplicate} already in the Transaction Log, {counts.rejected} rejected.
          </p>
          {rejections.length > 0 && (
            <ul>
              {rejections.map((row) => (
                <li key={row.row}>
                  Row {row.row}: {row.reason}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {error !== null && (
        <p className="state state--error" role="alert">
          {error}
        </p>
      )}

      <div className="rule-form__actions">
        <a className="button" href="/api/transactions/import-template">
          Download template
        </a>
        {preview === null && (
          <button type="button" className="button" disabled={file === null || busy} onClick={upload}>
            Upload
          </button>
        )}
        {preview !== null && (
          <button type="button" className="button" disabled={busy} onClick={confirm}>
            Confirm import
          </button>
        )}
        <button type="button" className="button button--quiet" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
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
