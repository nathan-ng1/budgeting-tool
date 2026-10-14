import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import GoalsTile from "./GoalsTile.jsx";

function goal(overrides = {}) {
  return {
    id: 1,
    title: "Japan trip",
    description: null,
    target_amount: 6000,
    start_date: "2026-07-01",
    end_date: "2027-03-31",
    state: "active",
    saved: 1500,
    remaining: 4500,
    over: 0,
    fraction: 0.25,
    status: "Active",
    flag: "Behind",
    pace_fraction: 0.4,
    pace_amount: 2400,
    on_track: false,
    months_left: 6,
    required_per_month: 750,
    original_plan_per_month: 666.67,
    ...overrides,
  };
}

function respondWith(goals, { ok = true } = {}) {
  const fetchMock = vi.fn(async () =>
    ok
      ? { ok: true, status: 200, json: async () => ({ today: "2026-10-14", goals, past: [] }) }
      : { ok: false, status: 500, json: async () => ({}) },
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderTile(onViewAll = () => {}) {
  return render(<GoalsTile onViewAll={onViewAll} />);
}

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("GoalsTile", () => {
  it("shows each Goal's title, Status chip, progress bar, % funded and $ / month", async () => {
    respondWith([goal()]);
    renderTile();

    expect(await screen.findByText("Japan trip")).toBeInTheDocument();
    expect(screen.getByText("Behind")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Japan trip progress" })).toHaveAttribute("aria-valuenow", "25");
    expect(screen.getByText("25% funded")).toBeInTheDocument();
    expect(screen.getByText("$750 / month")).toBeInTheDocument();
  });

  it("shows the top three active Goals, soonest end date first, and the count of all active Goals", async () => {
    respondWith([
      goal({ id: 1, title: "Car", end_date: "2028-01-01" }),
      goal({ id: 2, title: "Holiday", end_date: "2026-12-01" }),
      goal({ id: 3, title: "Bond", end_date: "2027-06-01" }),
      goal({ id: 4, title: "Laptop", end_date: "2027-01-01" }),
      goal({ id: 5, title: "Old plan", end_date: "2026-01-01", status: "Ended", flag: "Ended" }),
    ]);
    renderTile();

    await screen.findByText("Holiday");
    const items = screen.getAllByRole("listitem");
    expect(items.map((item) => within(item).getByRole("heading", { level: 4 }).textContent)).toEqual([
      "Holiday",
      "Laptop",
      "Bond",
    ]);
    expect(screen.queryByText("Car")).not.toBeInTheDocument();
    expect(screen.queryByText("Old plan")).not.toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument(); // the active count
  });

  it("links to the Goals tab with 'View all goals'", async () => {
    respondWith([goal()]);
    const onViewAll = vi.fn();
    renderTile(onViewAll);

    await userEvent.click(await screen.findByRole("button", { name: "View all goals" }));

    expect(onViewAll).toHaveBeenCalledTimes(1);
  });

  it("shows an empty state, and no Unassigned line, when no Goal is active", async () => {
    respondWith([goal({ status: "Achieved", flag: "Achieved" })]);
    renderTile();

    expect(await screen.findByText("No active goals yet.")).toBeInTheDocument();
    expect(screen.queryByText(/unassigned/i)).not.toBeInTheDocument();
  });

  it("asks for the Goals with no period, since the tile follows no month or Financial Year", async () => {
    const fetchMock = respondWith([goal()]);
    renderTile();
    await screen.findByText("Japan trip");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/goals");
  });

  it("says so when the Goals cannot be loaded", async () => {
    respondWith([], { ok: false });
    renderTile();

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("The Dashboard backend returned 500."));
  });
});
