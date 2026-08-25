// The Dashboard's colour theme is a device-local display preference, not
// domain data (ADR-0008 is a strictly local single-user app) - so it lives
// in localStorage, not the backend. Themes are keyed by string rather than a
// boolean so a third theme is "add an entry" later, not a rework.

const STORAGE_KEY = "dashboard.theme";

export const THEMES = [
  { key: "terracotta", label: "Terracotta", swatch: "#c67139" },
  { key: "blossom", label: "Blossom", swatch: "#d46b91" },
];

export const DEFAULT_THEME = "terracotta";

const THEME_KEYS = new Set(THEMES.map((theme) => theme.key));

export function getStoredTheme() {
  const stored = localStorage.getItem(STORAGE_KEY);
  return THEME_KEYS.has(stored) ? stored : DEFAULT_THEME;
}

export function storeTheme(themeKey) {
  localStorage.setItem(STORAGE_KEY, themeKey);
}

export function applyTheme(themeKey) {
  // The default theme has no CSS block of its own (it's the plain :root),
  // so it stays the implicit default rather than an explicit attribute -
  // matching index.html's pre-paint script, which does the same.
  if (themeKey === DEFAULT_THEME) {
    delete document.documentElement.dataset.theme;
  } else {
    document.documentElement.dataset.theme = themeKey;
  }
}

export function getCurrentTheme() {
  return document.documentElement.dataset.theme ?? DEFAULT_THEME;
}
