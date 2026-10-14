// PROTOTYPE (issue #209) - throwaway. Floating bottom-centre variant switcher.
// Variant lives in the URL (?variant=A|B|C) so it is shareable and reload-stable.
import { useEffect, useSyncExternalStore } from "react";

export const VARIANTS = [
  { key: "A", name: "Cards" },
  { key: "B", name: "Ledger, split inline" },
  { key: "C", name: "Master-detail" },
];

const read = () => {
  const v = new URLSearchParams(window.location.search).get("variant");
  return VARIANTS.some((x) => x.key === v) ? v : "A";
};
const listeners = new Set();
const subscribe = (l) => {
  listeners.add(l);
  return () => listeners.delete(l);
};

export const useVariant = () => useSyncExternalStore(subscribe, read);

function setVariant(key) {
  const url = new URL(window.location.href);
  url.searchParams.set("variant", key);
  window.history.replaceState(null, "", url);
  listeners.forEach((l) => l());
}

export default function PrototypeSwitcher() {
  const current = useVariant();
  const index = VARIANTS.findIndex((v) => v.key === current);
  const step = (delta) => setVariant(VARIANTS[(index + delta + VARIANTS.length) % VARIANTS.length].key);

  useEffect(() => {
    function onKey(event) {
      const el = document.activeElement;
      if (el && (/^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName) || el.isContentEditable)) return;
      if (event.key === "ArrowLeft") step(-1);
      if (event.key === "ArrowRight") step(1);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (import.meta.env.PROD) return null;

  return (
    <div className="gp-switcher" role="group" aria-label="Prototype variant">
      <button type="button" onClick={() => step(-1)} aria-label="Previous variant">
        &larr;
      </button>
      <span>
        {current} ({VARIANTS[index].name})
      </span>
      <button type="button" onClick={() => step(1)} aria-label="Next variant">
        &rarr;
      </button>
    </div>
  );
}
