// PROTOTYPE - throwaway (branch prototype/unallocated-placement). Not for master.
//
// Floating bottom bar that cycles a `?<param>=` URL search param through a
// list of variants, plus optional extra toggles that live in the URL too.
import { useEffect, useState } from "react";

export function useUrlParam(name, fallback) {
  const read = () => new URLSearchParams(window.location.search).get(name) ?? fallback;
  const [value, setValue] = useState(read);

  useEffect(() => {
    const sync = () => setValue(read());
    window.addEventListener("popstate", sync);
    window.addEventListener("prototype-param", sync);
    return () => {
      window.removeEventListener("popstate", sync);
      window.removeEventListener("prototype-param", sync);
    };
  });

  function update(next) {
    const params = new URLSearchParams(window.location.search);
    params.set(name, next);
    window.history.replaceState(null, "", `?${params}`);
    window.dispatchEvent(new Event("prototype-param"));
  }

  return [value, update];
}

// `toggles`: [{ param, label, options: [{ key, label }] }] - each cycles on click.
export default function PrototypeSwitcher({ param, title, variants, toggles = [] }) {
  const [current, setCurrent] = useUrlParam(param, variants[0].key);
  const index = Math.max(
    0,
    variants.findIndex((v) => v.key === current),
  );

  function step(delta) {
    setCurrent(variants[(index + delta + variants.length) % variants.length].key);
  }

  useEffect(() => {
    function onKey(event) {
      const target = event.target;
      if (target.closest?.("input, textarea, select, [contenteditable]")) return;
      if (event.key === "ArrowLeft") step(-1);
      if (event.key === "ArrowRight") step(1);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (import.meta.env.PROD) return null;

  return (
    <div className="proto-switcher" role="toolbar" aria-label="Prototype variant switcher">
      <span className="proto-switcher__title">{title}</span>
      <button type="button" onClick={() => step(-1)} aria-label="Previous variant">
        ←
      </button>
      <span className="proto-switcher__label">
        {variants[index].key} · {variants[index].name}
      </span>
      <button type="button" onClick={() => step(1)} aria-label="Next variant">
        →
      </button>
      {toggles.map((toggle) => (
        <Toggle key={toggle.param} {...toggle} />
      ))}
    </div>
  );
}

function Toggle({ param, label, options }) {
  const [value, setValue] = useUrlParam(param, options[0].key);
  const index = Math.max(
    0,
    options.findIndex((o) => o.key === value),
  );
  return (
    <button
      type="button"
      className="proto-switcher__toggle"
      onClick={() => setValue(options[(index + 1) % options.length].key)}
    >
      {label}: <strong>{options[index].label}</strong>
    </button>
  );
}
