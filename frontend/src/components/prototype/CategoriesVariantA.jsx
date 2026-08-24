import { useState } from "react";

// PROTOTYPE ONLY — Variant A: stacked cards per Type, table + inline form.
// Closest to the existing RecurringRules.jsx pattern.

export const LABEL = "Stacked cards + tables (closest to Recurring Rules)";

const TYPE_ORDER = ["Income", "Expense", "Debt", "Transfer"];

export default function CategoriesVariantA({ categories, onAdd, onEdit, onDelete }) {
  return (
    <>
      {TYPE_ORDER.map((type) => (
        <TypeCard
          key={type}
          type={type}
          categories={categories.filter((category) => category.type === type)}
          onAdd={onAdd}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}
    </>
  );
}

function TypeCard({ type, categories, onAdd, onEdit, onDelete }) {
  const [editing, setEditing] = useState(null);

  return (
    <section className="card">
      <div className="card__head">
        <div>
          <h3>{type} Categories</h3>
          <p className="card__note">Categories offered for {type} Transactions across the Dashboard.</p>
        </div>
        {editing === null && (
          <button type="button" className="button" onClick={() => setEditing({ id: null, name: "", emoji: "" })}>
            Add category
          </button>
        )}
      </div>

      {editing !== null && (
        <CategoryForm
          initial={editing}
          onCancel={() => setEditing(null)}
          onSave={(values) => {
            if (editing.id === null) {
              onAdd(type, values);
            } else {
              onEdit(editing.id, values);
            }
            setEditing(null);
          }}
        />
      )}

      {categories.length === 0 && <p className="state">No Categories yet — Add category to create the first one.</p>}

      {categories.length > 0 && (
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th scope="col"></th>
                <th scope="col">Name</th>
                <th scope="col"></th>
              </tr>
            </thead>
            <tbody>
              {categories.map((category) => (
                <tr key={category.id}>
                  <td style={{ fontSize: "18px" }}>{category.emoji || "—"}</td>
                  <td>{category.name}</td>
                  <td className="table__actions">
                    {category.locked ? (
                      <span className="muted" style={{ fontSize: "12.5px" }}>
                        locked — used by Beem Report processing
                      </span>
                    ) : (
                      <>
                        <button
                          type="button"
                          className="button button--quiet"
                          aria-label={`Edit ${category.name}`}
                          onClick={() => setEditing({ id: category.id, name: category.name, emoji: category.emoji })}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="button button--quiet button--danger"
                          aria-label={`Delete ${category.name}`}
                          onClick={() => onDelete(category.id)}
                        >
                          Delete
                        </button>
                      </>
                    )}
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

function CategoryForm({ initial, onCancel, onSave }) {
  const [name, setName] = useState(initial.name);
  const [emoji, setEmoji] = useState(initial.emoji);

  function submit(event) {
    event.preventDefault();
    onSave({ name, emoji });
  }

  return (
    <form className="rule-form" onSubmit={submit}>
      <div className="rule-form__grid">
        <label className="field">
          <span className="field__label">Emoji (optional)</span>
          <input type="text" maxLength={4} placeholder="🛒" value={emoji} onChange={(event) => setEmoji(event.target.value)} />
        </label>
        <label className="field field--wide">
          <span className="field__label">Name</span>
          <input type="text" required value={name} onChange={(event) => setName(event.target.value)} />
        </label>
      </div>
      <div className="rule-form__actions">
        <button type="submit" className="button">
          Save category
        </button>
        <button type="button" className="button button--quiet" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
