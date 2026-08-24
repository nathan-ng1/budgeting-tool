import { useCallback, useEffect, useState } from "react";

// PROTOTYPE ONLY — shared variant switcher for UI prototypes. Delete
// alongside the rest of components/prototype/ once a variant is folded in.

const PARAM = "variant";

function readVariant(keys, fallback) {
  const params = new URLSearchParams(window.location.search);
  const value = params.get(PARAM);
  return keys.includes(value) ? value : fallback;
}

export function useVariantParam(keys, fallback = keys[0]) {
  const [variant, setVariantState] = useState(() => readVariant(keys, fallback));

  const setVariant = useCallback((next) => {
    setVariantState(next);
    const params = new URLSearchParams(window.location.search);
    params.set(PARAM, next);
    window.history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
  }, []);

  useEffect(() => {
    function onPopState() {
      setVariantState(readVariant(keys, fallback));
    }
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [keys, fallback]);

  return [variant, setVariant];
}

export default function PrototypeSwitcher({ variants, labels, current, onSelect }) {
  useEffect(() => {
    function onKeyDown(event) {
      const target = event.target;
      const isEditable =
        target instanceof HTMLElement &&
        (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable);
      if (isEditable) return;

      const index = variants.indexOf(current);
      if (event.key === "ArrowLeft") {
        onSelect(variants[(index - 1 + variants.length) % variants.length]);
      } else if (event.key === "ArrowRight") {
        onSelect(variants[(index + 1) % variants.length]);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [variants, current, onSelect]);

  const index = variants.indexOf(current);
  const label = labels?.[current] ?? current;

  return (
    <div className="proto-switcher">
      <button
        type="button"
        className="proto-switcher__arrow"
        onClick={() => onSelect(variants[(index - 1 + variants.length) % variants.length])}
        aria-label="Previous variant"
      >
        ←
      </button>
      <span className="proto-switcher__label">
        {current} — {label}
      </span>
      <button
        type="button"
        className="proto-switcher__arrow"
        onClick={() => onSelect(variants[(index + 1) % variants.length])}
        aria-label="Next variant"
      >
        →
      </button>
    </div>
  );
}
