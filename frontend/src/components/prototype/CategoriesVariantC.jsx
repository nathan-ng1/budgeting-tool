import { useState } from "react";

import EmojiPicker from "./EmojiPicker.jsx";

// PROTOTYPE ONLY — Variant C: master-detail. A Type sidebar on the left,
// the selected Type's Categories + add/edit panel on the right. Only one
// Type's Categories are visible at a time, unlike Variants A and B.

export const LABEL = "Master-detail: Type sidebar + Category panel";

const TYPE_ORDER = ["Income", "Expense", "Debt", "Transfer"];

export default function CategoriesVariantC({ categories, onAdd, onEdit, onDelete }) {
  const [activeType, setActiveType] = useState("Expense");
  const [editing, setEditing] = useState(null);

  const visible = categories.filter((category) => category.type === activeType);

  return (
    <section className="card">
      <div className="card__head">
        <div>
          <h3>Categories</h3>
          <p className="card__note">Manage the Category list offered for every Type across the Dashboard.</p>
        </div>
      </div>

      <div className="proto-master-detail">
        <nav className="proto-type-nav">
          {TYPE_ORDER.map((type) => {
            const count = categories.filter((category) => category.type === type).length;
            return (
              <button
                key={type}
                type="button"
                className={`proto-type-nav__item ${type === activeType ? "proto-type-nav__item--active" : ""}`}
                onClick={() => {
                  setActiveType(type);
                  setEditing(null);
                }}
              >
                <span>{type}</span>
                <span className="proto-type-nav__count">{count}</span>
              </button>
            );
          })}
        </nav>

        <div className="proto-detail">
          {visible.length === 0 && <p className="state">No {activeType} Categories yet.</p>}

          {visible.length > 0 && (
            <ul className="proto-detail__list">
              {visible.map((category) => (
                <li key={category.id} className="proto-detail__row">
                  <span className="proto-detail__emoji">{category.emoji || "—"}</span>
                  <span className="proto-detail__name">{category.name}</span>
                  {category.locked ? (
                    <span className="muted" style={{ fontSize: "12.5px" }}>
                      locked
                    </span>
                  ) : (
                    <span className="table__actions">
                      <button
                        type="button"
                        className="button button--quiet"
                        onClick={() => setEditing({ id: category.id, name: category.name, emoji: category.emoji })}
                      >
                        Edit
                      </button>
                      <button type="button" className="button button--quiet button--danger" onClick={() => onDelete(category.id)}>
                        Delete
                      </button>
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}

          {editing !== null ? (
            <form
              className="rule-form"
              onSubmit={(event) => {
                event.preventDefault();
                if (editing.id === null) {
                  onAdd(activeType, editing);
                } else {
                  onEdit(editing.id, editing);
                }
                setEditing(null);
              }}
            >
              <div className="rule-form__grid">
                <label className="field">
                  <span className="field__label">Emoji</span>
                  <EmojiPicker value={editing.emoji} onChange={(emoji) => setEditing((current) => ({ ...current, emoji }))} />
                </label>
                <label className="field field--wide">
                  <span className="field__label">Name</span>
                  <input
                    type="text"
                    required
                    autoFocus
                    value={editing.name}
                    onChange={(event) => setEditing((current) => ({ ...current, name: event.target.value }))}
                  />
                </label>
              </div>
              <div className="rule-form__actions">
                <button type="submit" className="button">
                  Save category
                </button>
                <button type="button" className="button button--quiet" onClick={() => setEditing(null)}>
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <button type="button" className="button" onClick={() => setEditing({ id: null, name: "", emoji: "" })}>
              Add {activeType} category
            </button>
          )}
        </div>
      </div>
    </section>
  );
}
