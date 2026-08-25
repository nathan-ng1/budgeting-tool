import { useState } from "react";

import { THEMES, applyTheme, getStoredTheme, storeTheme } from "../lib/theme.js";

// Appearance (Issue #102) - a card of its own, directly above Category
// Management, so the colour theme reads as a Settings option rather than
// something buried inside another card. Selecting an option applies and
// persists it immediately: there is no Save step to forget.
export default function ThemeSwitcher() {
  const [theme, setTheme] = useState(getStoredTheme);

  function select(themeKey) {
    applyTheme(themeKey);
    storeTheme(themeKey);
    setTheme(themeKey);
  }

  return (
    <section className="card">
      <h3>Appearance</h3>
      <div className="theme-switcher" role="group" aria-label="Colour theme">
        {THEMES.map((option) => (
          <button
            key={option.key}
            type="button"
            className="theme-switcher__option"
            aria-pressed={option.key === theme}
            onClick={() => select(option.key)}
          >
            <span className="theme-switcher__swatch" style={{ background: option.swatch }} aria-hidden="true" />
            {option.label}
          </button>
        ))}
      </div>
    </section>
  );
}
