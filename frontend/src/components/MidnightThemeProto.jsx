import { useEffect, useState } from "react";

// PROTOTYPE (Midnight dark theme, /grilling session) - throwaway.
// Unlike OrchidPaletteProto (which reused Blossom's existing theme slot),
// there's no spare production theme to hijack here - Terracotta and Orchid
// are both real. So this component is fully self-contained: its own toggle
// sets/restores data-theme directly (bypassing theme.js's storeTheme, so it
// never touches localStorage or collides with the real ThemeSwitcher), and
// it injects a COMPLETE [data-theme="midnight"] block via <style> rather
// than overriding an existing one.
//
// What's fixed (settled in /grilling, not being compared): the role mapping
// (page bg #1B262C, card #082A42 - darkened from the source palette's
// #0F4C75 after a live look showed the card too close to accent-600, accent-
// 600 #3282B8, text white - changed from the source palette's #BBE1FA after
// a live look read as too blue), the
// desaturated-blue neutral ramp, Debt/Transfer (steps within that ramp),
// Income/Remaining (its own amber shade), a new --color-shadow token
// (decoupled from --color-text so shadows stay dark instead of inverting
// into light glows), and the category chart's 12-slot palette (exported as
// MIDNIGHT_PALETTE in lib/categoryColours.js).
//
// What's being compared (three variants, ?variant=A/B/C): how bright/
// saturated the two new hues (amber positive, red negative - red also
// doubles as the Midnight-specific --color-danger override) should be, and
// how big the inverted hover lift (accent-700/800 LIGHTER than accent-600,
// the opposite of every other theme) should be.
//
// Delete this file, its App.jsx wiring, and the MIDNIGHT_PALETTE export +
// branch in categoryColours.js once a variant wins (or the idea is
// dropped) - the winner's exact values get folded into styles.css/theme.js
// for real.

const FIXED_TOKENS = `
  --color-text: #ffffff;
  --color-card: #082a42;
  --color-accent-600: #3282b8;

  --color-neutral-100: #1c252c;
  --color-neutral-200: #28353e;
  --color-neutral-300: #3c505d;
  --color-neutral-400: #547083;
  --color-neutral-500: #7694a7;
  --color-neutral-600: #a2b6c3;
  --color-neutral-700: #cdd8df;

  --color-debt: #627f93;
  --color-transfer: #495f6e;
  --color-accent-2-500: #dcbd74;

  --color-shadow: #0b1014;
`;

const VARIANTS = {
  A: {
    name: "Moderate",
    accent: "#3282b8",
    accent700: "#64a9d8",
    accent800: "#8dc0e2",
    positive: "#e2b95a",
    positiveTint: "#473815",
    negative: "#efb1a9",
    negativeTint: "#4d1f19",
  },
  B: {
    name: "Vivid",
    accent: "#3282b8",
    accent700: "#6cb4e5",
    accent800: "#a0ceee",
    positive: "#f5ca66",
    positiveTint: "#43330e",
    negative: "#f8b3aa",
    negativeTint: "#491912",
  },
  C: {
    name: "Muted",
    accent: "#3282b8",
    accent700: "#679dc1",
    accent800: "#8bb4d0",
    positive: "#c4aa6e",
    positiveTint: "#453a21",
    negative: "#ddb6b0",
    negativeTint: "#4a2a26",
  },
};

const ORDER = ["A", "B", "C"];
const STYLE_ID = "proto-midnight-style";
// Setting data-theme here is a direct DOM mutation, not React state - so
// components that compute a colour from getCurrentTheme() at render time
// (colourForCategory() and friends) don't re-render when it changes, and
// stay frozen on whatever theme was active at their last real render (e.g.
// Full year's Spending by Category, still showing Orchid after toggling the
// preview on then off). This event lets App.jsx force a remount so those
// colours get recomputed - see its THEME_CHANGE_EVENT listener.
export const THEME_CHANGE_EVENT = "proto-midnight-theme-change";

function styleRules(variant) {
  const v = VARIANTS[variant];
  return `
    [data-theme="midnight"] {
      --color-accent: ${v.accent};
      --color-accent-700: ${v.accent700};
      --color-accent-800: ${v.accent800};
      --color-positive: ${v.positive};
      --color-positive-tint: ${v.positiveTint};
      --color-negative: ${v.negative};
      --color-negative-tint: ${v.negativeTint};
      --color-danger: ${v.negative};
      ${FIXED_TOKENS}
    }
  `;
}

function getVariantFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const requested = params.get("variant");
  return ORDER.includes(requested) ? requested : "A";
}

function getPreviewFromUrl() {
  return new URLSearchParams(window.location.search).get("midnight") === "1";
}

export default function MidnightThemeProto() {
  const [previewOn, setPreviewOn] = useState(getPreviewFromUrl);
  const [variant, setVariant] = useState(getVariantFromUrl);

  // Own toggle, own restoration - never reads or writes theme.js's storage
  // key, and restores whatever data-theme the real ThemeSwitcher had set
  // before the preview was switched on.
  useEffect(() => {
    const previous = document.documentElement.dataset.theme;
    let styleTag = document.getElementById(STYLE_ID);

    if (!previewOn) {
      styleTag?.remove();
      return undefined;
    }

    if (!styleTag) {
      styleTag = document.createElement("style");
      styleTag.id = STYLE_ID;
      document.head.appendChild(styleTag);
    }
    styleTag.textContent = styleRules(variant);
    document.documentElement.dataset.theme = "midnight";
    window.dispatchEvent(new Event(THEME_CHANGE_EVENT));

    return () => {
      if (previous === undefined) {
        delete document.documentElement.dataset.theme;
      } else {
        document.documentElement.dataset.theme = previous;
      }
      window.dispatchEvent(new Event(THEME_CHANGE_EVENT));
    };
  }, [previewOn, variant]);

  function togglePreview() {
    const next = !previewOn;
    setPreviewOn(next);
    const params = new URLSearchParams(window.location.search);
    if (next) {
      params.set("midnight", "1");
    } else {
      params.delete("midnight");
    }
    window.history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
  }

  function go(delta) {
    const index = ORDER.indexOf(variant);
    const next = ORDER[(index + delta + ORDER.length) % ORDER.length];
    setVariant(next);
    const params = new URLSearchParams(window.location.search);
    params.set("variant", next);
    window.history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
  }

  useEffect(() => {
    function onKeyDown(event) {
      const target = event.target;
      const isEditable = target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;
      if (isEditable || !previewOn) return;
      if (event.key === "ArrowLeft") go(-1);
      if (event.key === "ArrowRight") go(1);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  });

  return (
    <div
      style={{
        position: "fixed",
        bottom: 16,
        left: "50%",
        transform: "translateX(-50%)",
        zIndex: 999,
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "8px 10px",
        borderRadius: 999,
        background: "#201e1d",
        color: "#fff",
        fontSize: 13,
        boxShadow: "0 8px 24px rgba(0,0,0,0.25)",
      }}
    >
      <button
        type="button"
        onClick={togglePreview}
        style={{
          all: "unset",
          cursor: "pointer",
          padding: "4px 10px",
          borderRadius: 999,
          background: previewOn ? "#3282b8" : "#3c3a38",
        }}
      >
        {previewOn ? "Midnight ON" : "Preview Midnight"}
      </button>
      {previewOn && (
        <>
          <button type="button" onClick={() => go(-1)} style={{ all: "unset", cursor: "pointer", padding: "0 6px" }}>
            ←
          </button>
          <span>
            {variant} — {VARIANTS[variant].name}
          </span>
          <button type="button" onClick={() => go(1)} style={{ all: "unset", cursor: "pointer", padding: "0 6px" }}>
            →
          </button>
        </>
      )}
    </div>
  );
}
