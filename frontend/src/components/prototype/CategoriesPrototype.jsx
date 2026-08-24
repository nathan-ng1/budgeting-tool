import { useState } from "react";

import { seedCategories } from "./categoriesPrototypeData.js";
import CategoriesVariantA, { LABEL as LABEL_A } from "./CategoriesVariantA.jsx";
import CategoriesVariantB, { LABEL as LABEL_B } from "./CategoriesVariantB.jsx";
import CategoriesVariantC, { LABEL as LABEL_C } from "./CategoriesVariantC.jsx";
import PrototypeSwitcher, { useVariantParam } from "./PrototypeSwitcher.jsx";
import "./prototype.css";

// PROTOTYPE — throwaway UI exploration for the customizable Category list
// feature (Settings tab). Three variants of a Category management screen,
// mounted inside the real Settings tab (dev build only), switchable via
// ?variant=A|B|C. In-memory only, no API calls — nothing here is saved.
// See the `prototype/categories-settings-ui` branch for the full variant
// set once a winner is picked; delete this whole folder from main then.

const VARIANTS = ["A", "B", "C"];
const LABELS = { A: LABEL_A, B: LABEL_B, C: LABEL_C };

let nextId = 1000;

export default function CategoriesPrototype() {
  const [categories, setCategories] = useState(seedCategories);
  const [variant, setVariant] = useVariantParam(VARIANTS, "B");

  function add(type, values) {
    setCategories((current) => [
      ...current,
      { id: nextId++, type, name: values.name, emoji: values.emoji, locked: false },
    ]);
  }

  function edit(id, values) {
    setCategories((current) => current.map((category) => (category.id === id ? { ...category, ...values } : category)));
  }

  function remove(id) {
    setCategories((current) => current.filter((category) => category.id !== id));
  }

  const props = { categories, onAdd: add, onEdit: edit, onDelete: remove };

  return (
    <div className="proto-section">
      <div className="proto-banner">
        PROTOTYPE — Category management UI exploration ({variant} of {VARIANTS.length}). In-memory only, nothing here is
        saved.
      </div>

      {variant === "A" && <CategoriesVariantA {...props} />}
      {variant === "B" && <CategoriesVariantB {...props} />}
      {variant === "C" && <CategoriesVariantC {...props} />}

      <PrototypeSwitcher variants={VARIANTS} labels={LABELS} current={variant} onSelect={setVariant} />
    </div>
  );
}
