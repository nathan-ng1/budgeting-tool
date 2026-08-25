import { useEffect, useState } from "react";

import { BLOSSOM_PALETTE } from "../lib/categoryColours.js";
import { getCurrentTheme } from "../lib/theme.js";

// PROTOTYPE (Issue #102 follow-up) - throwaway. Answers two questions under
// Blossom: (1) does a stronger pink (favourable) + darker purple (adverse)
// read better than the shared green accent-2 ramp for positive/negative
// figures - three variants, switchable via ?variant=; and (2) does replacing
// Debt (blue) and Income/Remaining/the category donut's green slots with a
// neutral taupe (Debt), a dusty tan (Transfer) and a warm gold (Income /
// Remaining / donut ramp) fit the theme better - one fixed answer, applied
// under all three variants since it isn't what's being compared. Dev-only.
// Not meant to survive past the decision - see docs/agents or the issue for
// where the answer gets captured. Delete this file, its App.jsx wiring, and
// the BLOSSOM_PALETTE export in categoryColours.js once a variant wins (or
// the idea is dropped).

// Fixed across all variants (not the thing being compared) - Debt gets a
// neutral warm taupe, Transfer a lighter dusty tan distinct from both Debt
// and the pink accent, and Income/Remaining/the donut's green slots (4-7)
// move to a warm gold family so no chart colour reads as blue or green.
const BASE_OVERRIDES = {
  debt: "#6b5c5a",
  income: "#b8863a",
  incomeTint: "#f0e0c4",
  transfer: "#ab9490",
};

const DONUT_GOLD_RAMP = ["#8a6425", "#a87c2e", "#c99b4f", "#dfc08c"];
const DONUT_GOLD_START_INDEX = 4;

const VARIANTS = {
  A: {
    name: "Rose & Plum",
    positive: "#a8225f", // 6.56:1 vs Blossom card - clears the accent-2-700 baseline (6.17:1)
    positiveTint: "#f6dbe6",
    negative: "#5b3161", // 9.75:1 vs Blossom card
    negativeTint: "#e6dae8",
  },
  B: {
    name: "Hot Pink & Aubergine",
    positive: "#a52560", // 6.61:1
    positiveTint: "#f5dae5",
    negative: "#4a2545", // 12.22:1
    negativeTint: "#ddd0e0",
  },
  C: {
    name: "Coral-Pink & Mauve",
    positive: "#9c2f5c", // 6.74:1
    positiveTint: "#f2dbe4",
    negative: "#6b3d73", // 7.90:1
    negativeTint: "#e9dbe9",
  },
};

const ORDER = ["A", "B", "C"];
const STYLE_ID = "proto-102-accent-style";

function styleRules(variant) {
  const v = VARIANTS[variant];
  return `
    [data-theme="blossom"] .figure--adverse { color: ${v.negative} !important; }
    [data-theme="blossom"] .figure--favourable { color: ${v.positive} !important; }
    [data-theme="blossom"] .category-chip__save { color: ${v.positive} !important; }
    [data-theme="blossom"] .budget-suggestion__chip.figure--adverse {
      background: ${v.negativeTint} !important;
      color: ${v.negative} !important;
    }
    [data-theme="blossom"] .budget-suggestion__chip.figure--favourable {
      background: ${v.positiveTint} !important;
      color: ${v.positive} !important;
    }
    /* Fixed for all variants - see BASE_OVERRIDES above. */
    [data-theme="blossom"] {
      --color-debt: ${BASE_OVERRIDES.debt};
      --color-accent-2-500: ${BASE_OVERRIDES.income};
      --color-accent-2-700: ${DONUT_GOLD_RAMP[0]};
      --color-accent-2-300: ${BASE_OVERRIDES.incomeTint};
      --color-accent-300: ${BASE_OVERRIDES.transfer};
    }
  `;
}

function getVariantFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const requested = params.get("variant");
  return ORDER.includes(requested) ? requested : "A";
}

export default function AccentPaletteProto102() {
  const [variant, setVariant] = useState(getVariantFromUrl);
  const [theme, setTheme] = useState(getCurrentTheme);

  // ThemeSwitcher lives in a sibling component and only touches the DOM
  // attribute directly (no shared state) - watch it so the override style
  // clears itself the moment someone flips back to Terracotta.
  useEffect(() => {
    const observer = new MutationObserver(() => setTheme(getCurrentTheme()));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    let styleTag = document.getElementById(STYLE_ID);
    if (theme !== "blossom") {
      styleTag?.remove();
      return;
    }
    if (!styleTag) {
      styleTag = document.createElement("style");
      styleTag.id = STYLE_ID;
      document.head.appendChild(styleTag);
    }
    styleTag.textContent = styleRules(variant);
  }, [variant, theme]);

  // BLOSSOM_PALETTE's category-donut slots aren't CSS vars, so swap the four
  // green entries (indices 4-7) in place while comparing, and put the
  // originals back rather than leaving the module mutated once this
  // prototype is removed or the theme switches away.
  useEffect(() => {
    if (theme !== "blossom") return undefined;
    const originals = BLOSSOM_PALETTE.slice(DONUT_GOLD_START_INDEX, DONUT_GOLD_START_INDEX + DONUT_GOLD_RAMP.length);
    DONUT_GOLD_RAMP.forEach((colour, offset) => {
      BLOSSOM_PALETTE[DONUT_GOLD_START_INDEX + offset] = colour;
    });
    return () => {
      originals.forEach((colour, offset) => {
        BLOSSOM_PALETTE[DONUT_GOLD_START_INDEX + offset] = colour;
      });
    };
  }, [theme]);

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
      if (isEditable) return;
      if (event.key === "ArrowLeft") go(-1);
      if (event.key === "ArrowRight") go(1);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  });

  if (theme !== "blossom") {
    return (
      <div
        style={{
          position: "fixed",
          bottom: 16,
          left: "50%",
          transform: "translateX(-50%)",
          zIndex: 999,
          padding: "8px 16px",
          borderRadius: 999,
          background: "#201e1d",
          color: "#fff",
          fontSize: 12.5,
          boxShadow: "0 8px 24px rgba(0,0,0,0.25)",
        }}
      >
        PROTOTYPE #102-followup - switch to the Blossom theme to compare accent variants
      </div>
    );
  }

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
      <button type="button" onClick={() => go(-1)} style={{ all: "unset", cursor: "pointer", padding: "0 6px" }}>
        ←
      </button>
      <span>
        {variant} — {VARIANTS[variant].name}
      </span>
      <button type="button" onClick={() => go(1)} style={{ all: "unset", cursor: "pointer", padding: "0 6px" }}>
        →
      </button>
    </div>
  );
}
