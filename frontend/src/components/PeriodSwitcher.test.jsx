import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import PeriodSwitcher from "./PeriodSwitcher.jsx";

describe("PeriodSwitcher", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date(2026, 7, 21)); // 21 August 2026 - Financial Year 2026
    localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  function renderSwitcher(overrides = {}) {
    const onPeriodTypeChange = vi.fn();
    const onReferenceYearChange = vi.fn();
    render(
      <PeriodSwitcher
        periodType="financial"
        referenceYear={2026}
        earliestTransactionDate="2025-12-17"
        onPeriodTypeChange={onPeriodTypeChange}
        onReferenceYearChange={onReferenceYearChange}
        {...overrides}
      />,
    );
    return { onPeriodTypeChange, onReferenceYearChange };
  }

  it("labels the active Financial Year", () => {
    renderSwitcher();

    expect(screen.getByText("2026-2027 Financial Year")).toBeInTheDocument();
  });

  it("labels the active Calendar Year", () => {
    renderSwitcher({ periodType: "calendar", referenceYear: 2026 });

    expect(screen.getByText("Calendar Year 2026")).toBeInTheDocument();
  });

  it("steps back a year on Previous", async () => {
    const { onReferenceYearChange } = renderSwitcher();

    await userEvent.click(screen.getByRole("button", { name: "Previous year" }));
    expect(onReferenceYearChange).toHaveBeenCalledWith(2025);
  });

  it("steps forward a year on Next", async () => {
    const { onReferenceYearChange } = renderSwitcher({ referenceYear: 2025 });

    await userEvent.click(screen.getByRole("button", { name: "Next year" }));
    expect(onReferenceYearChange).toHaveBeenCalledWith(2026);
  });

  it("disables Previous at the Financial Year containing the earliest Transaction", async () => {
    const { onReferenceYearChange } = renderSwitcher({ referenceYear: 2025 });

    const previous = screen.getByRole("button", { name: "Previous year" });
    expect(previous).toBeDisabled();

    await userEvent.click(previous);
    expect(onReferenceYearChange).not.toHaveBeenCalled();
  });

  it("disables Next at the Financial Year containing today", async () => {
    const { onReferenceYearChange } = renderSwitcher({ referenceYear: 2026 });

    const next = screen.getByRole("button", { name: "Next year" });
    expect(next).toBeDisabled();

    await userEvent.click(next);
    expect(onReferenceYearChange).not.toHaveBeenCalled();
  });

  it("never disables Previous when the Transaction Log's date range is unknown", () => {
    renderSwitcher({ referenceYear: 2010, earliestTransactionDate: null });

    expect(screen.getByRole("button", { name: "Previous year" })).not.toBeDisabled();
  });

  it("switches periodType when the other toggle option is clicked", async () => {
    const { onPeriodTypeChange } = renderSwitcher();

    await userEvent.click(screen.getByRole("button", { name: "Calendar Year" }));

    expect(onPeriodTypeChange).toHaveBeenCalledWith("calendar");
  });

  it("does nothing when the already-active toggle option is clicked", async () => {
    const { onPeriodTypeChange } = renderSwitcher();

    await userEvent.click(screen.getByRole("button", { name: "Financial Year" }));

    expect(onPeriodTypeChange).not.toHaveBeenCalled();
  });

  it("marks the active toggle option as pressed, and only that one", () => {
    renderSwitcher({ periodType: "calendar" });

    expect(screen.getByRole("button", { name: "Financial Year" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "Calendar Year" })).toHaveAttribute("aria-pressed", "true");
  });

  it("persists periodType to localStorage when the toggle is clicked", async () => {
    renderSwitcher();

    await userEvent.click(screen.getByRole("button", { name: "Calendar Year" }));

    expect(localStorage.getItem("dashboard.periodType")).toBe("calendar");
  });

  it("does not touch localStorage when the already-active toggle option is clicked", async () => {
    renderSwitcher();

    await userEvent.click(screen.getByRole("button", { name: "Financial Year" }));

    expect(localStorage.getItem("dashboard.periodType")).toBeNull();
  });
});
