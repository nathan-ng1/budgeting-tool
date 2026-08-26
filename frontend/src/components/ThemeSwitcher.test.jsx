import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import ThemeSwitcher from "./ThemeSwitcher.jsx";

describe("ThemeSwitcher", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    delete document.documentElement.dataset.theme;
  });

  it("offers Terracotta, Orchid and Midnight, each with a swatch", () => {
    render(<ThemeSwitcher />);

    const options = screen.getAllByRole("button");

    expect(options).toHaveLength(3);
    expect(options[0]).toHaveTextContent("Terracotta");
    expect(options[1]).toHaveTextContent("Orchid");
    expect(options[2]).toHaveTextContent("Midnight");
  });

  it("marks Terracotta as pressed when no theme is stored yet", () => {
    render(<ThemeSwitcher />);

    expect(screen.getByRole("button", { name: /Terracotta/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /Orchid/ })).toHaveAttribute("aria-pressed", "false");
  });

  it("marks the previously stored theme as pressed on load", () => {
    localStorage.setItem("dashboard.theme", "orchid");

    render(<ThemeSwitcher />);

    expect(screen.getByRole("button", { name: /Orchid/ })).toHaveAttribute("aria-pressed", "true");
  });

  it("applies and persists a theme immediately on click, with no separate Save step", async () => {
    render(<ThemeSwitcher />);

    await userEvent.click(screen.getByRole("button", { name: /Orchid/ }));

    expect(document.documentElement.dataset.theme).toBe("orchid");
    expect(localStorage.getItem("dashboard.theme")).toBe("orchid");
    expect(screen.getByRole("button", { name: /Orchid/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /Terracotta/ })).toHaveAttribute("aria-pressed", "false");
  });
});
