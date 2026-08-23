import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import MonthSelector from "./MonthSelector.jsx";

describe("MonthSelector", () => {
  it("offers a Full year pill plus the twelve months of the Financial Year, July first", () => {
    render(<MonthSelector financialYear={2026} selected={{ year: 2026, month: 8 }} onSelect={() => {}} />);

    const pills = screen.getAllByRole("button");

    expect(pills).toHaveLength(13);
    expect(pills[0]).toHaveTextContent("Full year");
    expect(pills[1]).toHaveTextContent("Jul");
    expect(pills[12]).toHaveTextContent("Jun");
  });

  it("marks the selected month, and only that one", () => {
    render(<MonthSelector financialYear={2026} selected={{ year: 2026, month: 8 }} onSelect={() => {}} />);

    const pressed = screen.getAllByRole("button").filter((pill) => pill.getAttribute("aria-pressed") === "true");

    expect(pressed).toHaveLength(1);
    expect(pressed[0]).toHaveTextContent("Aug");
  });

  it("marks Full year as pressed, and only that, when selected is null", () => {
    render(<MonthSelector financialYear={2026} selected={null} onSelect={() => {}} />);

    const pressed = screen.getAllByRole("button").filter((pill) => pill.getAttribute("aria-pressed") === "true");

    expect(pressed).toHaveLength(1);
    expect(pressed[0]).toHaveTextContent("Full year");
  });

  it("reports the calendar year alongside the month, so January means the next one", async () => {
    const onSelect = vi.fn();
    render(<MonthSelector financialYear={2026} selected={{ year: 2026, month: 8 }} onSelect={onSelect} />);

    await userEvent.click(screen.getByRole("button", { name: "Jan" }));

    expect(onSelect).toHaveBeenCalledWith({ year: 2027, month: 1 });
  });

  it("selects Full year with null", async () => {
    const onSelect = vi.fn();
    render(<MonthSelector financialYear={2026} selected={{ year: 2026, month: 8 }} onSelect={onSelect} />);

    await userEvent.click(screen.getByRole("button", { name: "Full year" }));

    expect(onSelect).toHaveBeenCalledWith(null);
  });

  it("omits the Full year pill when includeFullYear is false, leaving only the twelve months", () => {
    render(
      <MonthSelector
        financialYear={2026}
        selected={{ year: 2026, month: 8 }}
        onSelect={() => {}}
        includeFullYear={false}
      />,
    );

    const pills = screen.getAllByRole("button");

    expect(pills).toHaveLength(12);
    expect(screen.queryByRole("button", { name: "Full year" })).not.toBeInTheDocument();
    expect(pills[0]).toHaveTextContent("Jul");
  });
});
