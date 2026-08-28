import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import MonthSelector from "./MonthSelector.jsx";

describe("MonthSelector", () => {
  it("offers a Full year pill plus the twelve months of the Financial Year, July first", () => {
    render(
      <MonthSelector
        referenceYear={2026}
        periodType="financial"
        selected={{ year: 2026, month: 8 }}
        onSelect={() => {}}
      />,
    );

    const pills = screen.getAllByRole("button");

    expect(pills).toHaveLength(13);
    expect(pills[0]).toHaveTextContent("Full year");
    expect(pills[1]).toHaveTextContent("Jul");
    expect(pills[12]).toHaveTextContent("Jun");
  });

  it("offers the twelve months of the Calendar Year, January first", () => {
    render(
      <MonthSelector
        referenceYear={2026}
        periodType="calendar"
        selected={{ year: 2026, month: 8 }}
        onSelect={() => {}}
      />,
    );

    const pills = screen.getAllByRole("button");

    expect(pills).toHaveLength(13);
    expect(pills[1]).toHaveTextContent("Jan");
    expect(pills[12]).toHaveTextContent("Dec");
  });

  it("marks the selected month, and only that one", () => {
    render(
      <MonthSelector
        referenceYear={2026}
        periodType="financial"
        selected={{ year: 2026, month: 8 }}
        onSelect={() => {}}
      />,
    );

    const pressed = screen.getAllByRole("button").filter((pill) => pill.getAttribute("aria-pressed") === "true");

    expect(pressed).toHaveLength(1);
    expect(pressed[0]).toHaveTextContent("Aug");
  });

  it("marks Full year as pressed, and only that, when selected is null", () => {
    render(<MonthSelector referenceYear={2026} periodType="financial" selected={null} onSelect={() => {}} />);

    const pressed = screen.getAllByRole("button").filter((pill) => pill.getAttribute("aria-pressed") === "true");

    expect(pressed).toHaveLength(1);
    expect(pressed[0]).toHaveTextContent("Full year");
  });

  it("reports the calendar year alongside the month, so January means the next one", async () => {
    const onSelect = vi.fn();
    render(
      <MonthSelector
        referenceYear={2026}
        periodType="financial"
        selected={{ year: 2026, month: 8 }}
        onSelect={onSelect}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Jan" }));

    expect(onSelect).toHaveBeenCalledWith({ year: 2027, month: 1 });
  });

  it("selects Full year with null", async () => {
    const onSelect = vi.fn();
    render(
      <MonthSelector
        referenceYear={2026}
        periodType="financial"
        selected={{ year: 2026, month: 8 }}
        onSelect={onSelect}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Full year" }));

    expect(onSelect).toHaveBeenCalledWith(null);
  });
});
