import { useCallback, useEffect, useState } from "react";

import EmojiPicker from "./EmojiPicker.jsx";
import { TYPE_ORDER } from "../lib/categories.js";
import { createCategory, deleteCategory, fetchCategories, updateCategory } from "../lib/categoriesApi.js";

// Category Management (Issue #91) - one card spanning all four fixed Types,
// each holding a chip per Category. Add/edit happen inline in the chip grid;
// delete goes through an inline "Delete 'X'?" confirm step rather than a
// native confirm() dialog. Beem Adjustment (or any other locked Category)
// shows with no edit/delete controls - the store itself refuses those
// mutations regardless, this is only the UI matching that.
export default function CategoryManagement() {
  const [categories, setCategories] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async (signal) => {
    const loaded = await fetchCategories({ signal });
    setCategories(loaded);
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    load(controller.signal).catch((cause) => {
      if (cause.name !== "AbortError") {
        setError(cause.message);
      }
    });

    return () => controller.abort();
  }, [load]);

  async function add(type, { name, emoji }) {
    const created = await createCategory({ type, name, emoji: emoji || null });
    setCategories((current) => [...current, created]);
  }

  async function edit(id, { name, emoji }) {
    const updated = await updateCategory(id, { name, emoji: emoji || null });
    setCategories((current) => current.map((category) => (category.id === id ? updated : category)));
  }

  async function remove(id) {
    await deleteCategory(id);
    setCategories((current) => current.filter((category) => category.id !== id));
  }

  if (error !== null && categories === null) {
    return (
      <section className="card">
        <h3>Category Management</h3>
        <p className="state state--error" role="alert">
          {error}
        </p>
      </section>
    );
  }

  return (
    <section className="card">
      <h3>Category Management</h3>

      {categories === null && <p className="state">Loading Categories&hellip;</p>}

      {categories !== null &&
        TYPE_ORDER.map((type) => (
          <TypeGroup
            key={type}
            type={type}
            categories={categories.filter((category) => category.type === type)}
            onAdd={add}
            onEdit={edit}
            onDelete={remove}
          />
        ))}
    </section>
  );
}

function TypeGroup({ type, categories, onAdd, onEdit, onDelete }) {
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [confirmingId, setConfirmingId] = useState(null);
  const [deleteError, setDeleteError] = useState(null);

  const sorted = [...categories].sort((a, b) => a.name.localeCompare(b.name));

  function startDelete(category) {
    setDeleteError(null);
    setConfirmingId(category.id);
  }

  function cancelDelete() {
    setDeleteError(null);
    setConfirmingId(null);
  }

  async function confirmDelete(category) {
    setDeleteError(null);
    try {
      await onDelete(category.id);
      setConfirmingId(null);
    } catch (cause) {
      setDeleteError(cause.message);
    }
  }

  return (
    <div className="category-group">
      <h4 className="category-group__heading">{type}</h4>
      <div className="category-chip-grid">
        {sorted.map((category) => {
          if (confirmingId === category.id) {
            return (
              <div key={category.id} className="category-chip category-chip--confirm">
                <span>Delete “{category.name}”?</span>
                <span className="category-chip__actions">
                  <button
                    type="button"
                    aria-label={`Confirm delete ${category.name}`}
                    onClick={() => confirmDelete(category)}
                  >
                    ✓
                  </button>
                  <button type="button" aria-label="Cancel delete" onClick={cancelDelete}>
                    ✕
                  </button>
                </span>
                {deleteError !== null && (
                  <p className="state state--error category-chip__error" role="alert">
                    {deleteError}
                  </p>
                )}
              </div>
            );
          }

          if (editingId === category.id) {
            return (
              <CategoryChipForm
                key={category.id}
                initial={{ name: category.name, emoji: category.emoji ?? "" }}
                onCancel={() => setEditingId(null)}
                onSave={async (values) => {
                  await onEdit(category.id, values);
                  setEditingId(null);
                }}
              />
            );
          }

          return (
            <div key={category.id} className="category-chip">
              {category.emoji && <span className="category-chip__emoji">{category.emoji}</span>}
              <span className="category-chip__name">{category.name}</span>
              {!category.locked && (
                <span className="category-chip__actions">
                  <button
                    type="button"
                    aria-label={`Edit ${category.name}`}
                    onClick={() => setEditingId(category.id)}
                  >
                    ✎
                  </button>
                  <button
                    type="button"
                    aria-label={`Delete ${category.name}`}
                    onClick={() => startDelete(category)}
                  >
                    ×
                  </button>
                </span>
              )}
              {category.locked && (
                <span className="category-chip__lock" title="Locked - can't be renamed or deleted">
                  🔒
                </span>
              )}
            </div>
          );
        })}

        {adding ? (
          <CategoryChipForm
            initial={{ name: "", emoji: "" }}
            onCancel={() => setAdding(false)}
            onSave={async (values) => {
              await onAdd(type, values);
              setAdding(false);
            }}
          />
        ) : (
          <button type="button" className="category-chip category-chip--add" onClick={() => setAdding(true)}>
            + Add category
          </button>
        )}
      </div>
    </div>
  );
}

function CategoryChipForm({ initial, onCancel, onSave }) {
  const [name, setName] = useState(initial.name);
  const [emoji, setEmoji] = useState(initial.emoji);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  async function submit(event) {
    event.preventDefault();
    if (!name.trim()) {
      return;
    }

    setError(null);
    setSaving(true);
    try {
      await onSave({ name: name.trim(), emoji });
    } catch (cause) {
      // The store is the authority on what a valid Category is, so its
      // message is the one worth showing - the form stays open to fix it.
      setError(cause.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="category-chip category-chip--form" onSubmit={submit}>
      <EmojiPicker value={emoji} onChange={setEmoji} />
      <input
        type="text"
        autoFocus
        aria-label="Category name"
        placeholder="Category name"
        value={name}
        onChange={(event) => setName(event.target.value)}
      />
      <button type="submit" className="category-chip__save" aria-label="Save" disabled={saving}>
        ✓
      </button>
      <button type="button" className="category-chip__cancel" aria-label="Cancel" onClick={onCancel}>
        ✕
      </button>
      {error !== null && (
        <p className="state state--error category-chip__error" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
