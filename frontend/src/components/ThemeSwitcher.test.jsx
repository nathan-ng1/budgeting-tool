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

  it("offers Terracotta and Blossom, each with a swatch", () => {
    render(<ThemeSwitcher />);

    const options = screen.getAllByRole("button");

    expect(options).toHaveLength(2);
    expect(options[0]).toHaveTextContent("Terracotta");
    expect(options[1]).toHaveTextContent("Blossom");
  });

  it("marks Terracotta as pressed when no theme is stored yet", () => {
    render(<ThemeSwitcher />);

    expect(screen.getByRole("button", { name: /Terracotta/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /Blossom/ })).toHaveAttribute("aria-pressed", "false");
  });

  it("marks the previously stored theme as pressed on load", () => {
    localStorage.setItem("dashboard.theme", "blossom");

    render(<ThemeSwitcher />);

    expect(screen.getByRole("button", { name: /Blossom/ })).toHaveAttribute("aria-pressed", "true");
  });

  it("applies and persists a theme immediately on click, with no separate Save step", async () => {
    render(<ThemeSwitcher />);

    await userEvent.click(screen.getByRole("button", { name: /Blossom/ }));

    expect(document.documentElement.dataset.theme).toBe("blossom");
    expect(localStorage.getItem("dashboard.theme")).toBe("blossom");
    expect(screen.getByRole("button", { name: /Blossom/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /Terracotta/ })).toHaveAttribute("aria-pressed", "false");
  });
});
