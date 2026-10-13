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

  it("offers Terracotta, Orchid, Midnight and Sage, in that order", () => {
    render(<ThemeSwitcher />);

    const options = screen.getAllByRole("button");

    expect(options).toHaveLength(4);
    expect(options[0]).toHaveTextContent("Terracotta");
    expect(options[1]).toHaveTextContent("Orchid");
    expect(options[2]).toHaveTextContent("Midnight");
    expect(options[3]).toHaveTextContent("Sage");
  });

  it("marks Terracotta as pressed when no theme is stored yet", () => {
    render(<ThemeSwitcher />);

    expect(screen.getByRole("button", { name: /Terracotta/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /Orchid/ })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: /Sage/ })).toHaveAttribute("aria-pressed", "false");
  });

  it("marks the previously stored theme as pressed on load", () => {
    localStorage.setItem("dashboard.theme", "orchid");

    render(<ThemeSwitcher />);

    expect(screen.getByRole("button", { name: /Orchid/ })).toHaveAttribute("aria-pressed", "true");
  });

  it("marks a previously stored Sage theme as pressed on load and no other option", () => {
    localStorage.setItem("dashboard.theme", "sage");

    render(<ThemeSwitcher />);

    expect(screen.getByRole("button", { name: /Sage/ })).toHaveAttribute("aria-pressed", "true");
    ["Terracotta", "Orchid", "Midnight"].forEach((name) =>
      expect(screen.getByRole("button", { name: new RegExp(name) })).toHaveAttribute("aria-pressed", "false"),
    );
  });

  it("applies and persists Sage on click, with no separate Save step", async () => {
    render(<ThemeSwitcher />);

    await userEvent.click(screen.getByRole("button", { name: /Sage/ }));

    expect(document.documentElement.dataset.theme).toBe("sage");
    expect(localStorage.getItem("dashboard.theme")).toBe("sage");
    expect(screen.getByRole("button", { name: /Sage/ })).toHaveAttribute("aria-pressed", "true");
    ["Terracotta", "Orchid", "Midnight"].forEach((name) =>
      expect(screen.getByRole("button", { name: new RegExp(name) })).toHaveAttribute("aria-pressed", "false"),
    );
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
