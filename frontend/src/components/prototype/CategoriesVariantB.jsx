import { useState } from "react";

import EmojiPicker from "./EmojiPicker.jsx";

// PROTOTYPE ONLY — Variant B: emoji-forward chip grid, edit in place. One
// "Category Management" card covers every Type (grouped under subheadings)
// rather than a separate card per Type.

export const LABEL = "Emoji-forward chip grid, edit in place";

const TYPE_ORDER = ["Income", "Expense", "Debt", "Transfer"];

export default function CategoriesVariantB({ categories, onAdd, onEdit, onDelete }) {
  return (
    <section className="card">
      <h3>Category Management</h3>
      {TYPE_ORDER.map((type) => (
        <TypeGroup
          key={type}
          type={type}
          categories={categories.filter((category) => category.type === type)}
          onAdd={onAdd}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}
    </section>
  );
}

function TypeGroup({ type, categories, onAdd, onEdit, onDelete }) {
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState({ name: "", emoji: "" });
  const [editingId, setEditingId] = useState(null);
  const [confirmingId, setConfirmingId] = useState(null);

  function saveAdd(event) {
    event.preventDefault();
    if (!draft.name.trim()) return;
    onAdd(type, draft);
    setAdding(false);
  }

  return (
    <div className="proto-type-group">
      <h4 className="proto-type-group__heading">{type}</h4>
      <div className="proto-chip-grid">
        {categories.map((category) => {
          if (confirmingId === category.id) {
            return (
              <div key={category.id} className="proto-chip proto-chip--confirm">
                <span>Delete “{category.name}”?</span>
                <span className="proto-chip__actions">
                  <button
                    type="button"
                    className="proto-chip__confirm-yes"
                    aria-label={`Confirm delete ${category.name}`}
                    onClick={() => {
                      onDelete(category.id);
                      setConfirmingId(null);
                    }}
                  >
                    ✓
                  </button>
                  <button
                    type="button"
                    className="proto-chip__cancel"
                    aria-label="Cancel delete"
                    onClick={() => setConfirmingId(null)}
                  >
                    ✕
                  </button>
                </span>
              </div>
            );
          }

          if (editingId === category.id) {
            return (
              <EditChip
                key={category.id}
                category={category}
                onCancel={() => setEditingId(null)}
                onSave={(values) => {
                  onEdit(category.id, values);
                  setEditingId(null);
                }}
              />
            );
          }

          return (
            <div key={category.id} className="proto-chip">
              {category.emoji && <span className="proto-chip__emoji">{category.emoji}</span>}
              <span className="proto-chip__name">{category.name}</span>
              {!category.locked && (
                <span className="proto-chip__actions">
                  <button type="button" aria-label={`Edit ${category.name}`} onClick={() => setEditingId(category.id)}>
                    ✎
                  </button>
                  <button
                    type="button"
                    aria-label={`Delete ${category.name}`}
                    onClick={() => setConfirmingId(category.id)}
                  >
                    ×
                  </button>
                </span>
              )}
              {category.locked && (
                <span className="proto-chip__lock" title="Locked — used by Beem Report processing">
                  🔒
                </span>
              )}
            </div>
          );
        })}

        {adding ? (
          <form className="proto-chip proto-chip--form" onSubmit={saveAdd}>
            <EmojiPicker value={draft.emoji} onChange={(emoji) => setDraft((current) => ({ ...current, emoji }))} />
            <input
              type="text"
              autoFocus
              placeholder="Category name"
              value={draft.name}
              onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))}
            />
            <button type="submit" className="proto-chip__save" aria-label="Save">
              ✓
            </button>
            <button type="button" className="proto-chip__cancel" aria-label="Cancel" onClick={() => setAdding(false)}>
              ✕
            </button>
          </form>
        ) : (
          <button
            type="button"
            className="proto-chip proto-chip--add"
            onClick={() => {
              setDraft({ name: "", emoji: "" });
              setAdding(true);
            }}
          >
            + Add category
          </button>
        )}
      </div>
    </div>
  );
}

function EditChip({ category, onCancel, onSave }) {
  const [name, setName] = useState(category.name);
  const [emoji, setEmoji] = useState(category.emoji);

  function submit(event) {
    event.preventDefault();
    onSave({ name, emoji });
  }

  return (
    <form className="proto-chip proto-chip--form" onSubmit={submit}>
      <EmojiPicker value={emoji} onChange={setEmoji} />
      <input type="text" autoFocus value={name} onChange={(event) => setName(event.target.value)} />
      <button type="submit" className="proto-chip__save" aria-label="Save">
        ✓
      </button>
      <button type="button" className="proto-chip__cancel" aria-label="Cancel" onClick={onCancel}>
        ✕
      </button>
    </form>
  );
}
