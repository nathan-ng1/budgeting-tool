import { useCallback, useEffect, useState } from "react";

// PROTOTYPE (prototype/orchid-theme-variants) - throwaway. Forces the Orchid
// theme on and lets you flip between the three derived-shade variants
// (styles.css [data-orchid-variant], categoryColours.js ORCHID_PALETTE_VARIANTS)
// via a floating switcher, so they can be judged against the real app.
// Not for production: gated on import.meta.env.DEV. Delete this file, its
// import in App.jsx, and the variant plumbing in styles.css/categoryColours.js
// once a variant wins.

const VARIANTS = [
  { key: "A", name: "Moderate — hue-locked, same weight as today" },
  { key: "B", name: "Richer — more saturated throughout" },
  { key: "C", name: "Muted — soft, closer to pastel" },
];

function variantFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const requested = params.get("variant");
  return VARIANTS.some((v) => v.key === requested) ? requested : "A";
}

export default function OrchidVariantPrototypeSwitcher() {
  const [variant, setVariant] = useState(variantFromUrl);

  useEffect(() => {
    document.documentElement.dataset.theme = "orchid";
    document.documentElement.dataset.orchidVariant = variant;

    const params = new URLSearchParams(window.location.search);
    params.set("variant", variant);
    window.history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);

    return () => {
      delete document.documentElement.dataset.orchidVariant;
    };
  }, [variant]);

  const cycle = useCallback((direction) => {
    setVariant((current) => {
      const index = VARIANTS.findIndex((v) => v.key === current);
      const next = VARIANTS[(index + direction + VARIANTS.length) % VARIANTS.length];
      return next.key;
    });
  }, []);

  useEffect(() => {
    function onKeyDown(event) {
      const target = event.target;
      const isEditable = target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;
      if (isEditable) {
        return;
      }
      if (event.key === "ArrowLeft") {
        cycle(-1);
      } else if (event.key === "ArrowRight") {
        cycle(1);
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [cycle]);

  if (!import.meta.env.DEV) {
    return null;
  }

  const current = VARIANTS.find((v) => v.key === variant);

  return (
    <div
      style={{
        position: "fixed",
        bottom: 16,
        left: "50%",
        transform: "translateX(-50%)",
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "10px 16px",
        borderRadius: 999,
        background: "#111",
        color: "#fff",
        boxShadow: "0 8px 24px rgba(0,0,0,0.35)",
        fontFamily: "system-ui, sans-serif",
        fontSize: 13,
        zIndex: 9999,
      }}
    >
      <button
        type="button"
        onClick={() => cycle(-1)}
        style={{ background: "none", border: "none", color: "#fff", fontSize: 16, cursor: "pointer" }}
        aria-label="Previous variant"
      >
        ←
      </button>
      <span style={{ whiteSpace: "nowrap" }}>
        <strong>{current.key}</strong> — {current.name}
      </span>
      <button
        type="button"
        onClick={() => cycle(1)}
        style={{ background: "none", border: "none", color: "#fff", fontSize: 16, cursor: "pointer" }}
        aria-label="Next variant"
      >
        →
      </button>
    </div>
  );
}
