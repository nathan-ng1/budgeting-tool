import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { DEFAULT_THEME, THEMES, applyTheme, getCurrentTheme, getStoredTheme, storeTheme } from "./theme.js";

describe("THEMES", () => {
  it("lists Terracotta and Blossom, each with a key, label and swatch", () => {
    const keys = THEMES.map((theme) => theme.key);

    expect(keys).toEqual(["terracotta", "blossom"]);
    THEMES.forEach((theme) => {
      expect(theme.label).toEqual(expect.any(String));
      expect(theme.swatch).toMatch(/^#[0-9a-f]{6}$/i);
    });
  });
});

describe("getStoredTheme", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("falls back to the default theme when nothing is stored", () => {
    expect(getStoredTheme()).toBe(DEFAULT_THEME);
  });

  it("returns a previously stored theme", () => {
    localStorage.setItem("dashboard.theme", "blossom");

    expect(getStoredTheme()).toBe("blossom");
  });

  it("falls back to the default theme for a value that isn't a known theme", () => {
    // Guards against a future build removing a theme a past visit stored.
    localStorage.setItem("dashboard.theme", "midnight");

    expect(getStoredTheme()).toBe(DEFAULT_THEME);
  });
});

describe("storeTheme", () => {
  afterEach(() => {
    localStorage.clear();
  });

  it("persists the theme so a later getStoredTheme call returns it", () => {
    storeTheme("blossom");

    expect(getStoredTheme()).toBe("blossom");
  });
});

describe("applyTheme", () => {
  afterEach(() => {
    delete document.documentElement.dataset.theme;
  });

  it("sets the data-theme attribute on <html> to the given theme", () => {
    applyTheme("blossom");

    expect(document.documentElement.dataset.theme).toBe("blossom");
  });

  it("leaves the data-theme attribute unset for the default theme", () => {
    // The default theme has no CSS block of its own - it's the plain :root -
    // so setting the attribute explicitly would be inert but would leave the
    // DOM in a different state than a fresh page load (index.html's
    // pre-paint script also leaves it unset for the default theme).
    applyTheme("blossom");
    applyTheme(DEFAULT_THEME);

    expect(document.documentElement.dataset.theme).toBeUndefined();
  });
});

describe("getCurrentTheme", () => {
  afterEach(() => {
    delete document.documentElement.dataset.theme;
  });

  it("returns the default theme when no data-theme attribute is set", () => {
    expect(getCurrentTheme()).toBe(DEFAULT_THEME);
  });

  it("returns the applied theme", () => {
    applyTheme("blossom");

    expect(getCurrentTheme()).toBe("blossom");
  });
});
