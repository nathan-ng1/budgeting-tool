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

  it("shows the top three lifecycle-active Goals, soonest end date first, and the count of all of them", async () => {
    respondWith([
      goal({ id: 1, title: "Car", end_date: "2028-01-01" }),
      goal({ id: 2, title: "Holiday", end_date: "2026-12-01" }),
      goal({ id: 3, title: "Bond", end_date: "2027-06-01" }),
      goal({ id: 4, title: "Laptop", end_date: "2027-01-01" }),
      goal({ id: 5, title: "Quiet one", end_date: "2029-01-01" }),
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
    expect(screen.queryByText("Quiet one")).not.toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument(); // the active count
  });

  it("includes Achieved, Ended and Upcoming Goals, with their chips and no 'null / month'", async () => {
    respondWith([
      goal({ id: 1, title: "Done", end_date: "2026-11-01", status: "Achieved", flag: "Achieved", saved: 6200, over: 200, remaining: 0, fraction: 1, required_per_month: null }),
      goal({ id: 2, title: "Missed", end_date: "2026-09-01", status: "Ended", flag: "Ended", remaining: 1000, months_left: 0, required_per_month: null }),
      goal({ id: 3, title: "Later", end_date: "2027-12-01", status: "Upcoming", flag: "Upcoming", saved: 0, fraction: 0, pace_fraction: 0 }),
    ]);
    renderTile();

    await screen.findByText("Missed");
    const items = screen.getAllByRole("listitem");
    expect(items.map((item) => within(item).getByRole("heading", { level: 4 }).textContent)).toEqual([
      "Missed",
      "Done",
      "Later",
    ]);
    expect(within(items[0]).getByText("Ended")).toBeInTheDocument();
    expect(within(items[1]).getByText("Achieved")).toBeInTheDocument();
    expect(within(items[2]).getByText("Upcoming")).toBeInTheDocument();
    expect(screen.queryByText(/null|NaN/)).not.toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("caps % funded at 100, like the progress bar and the Goals tab", async () => {
    respondWith([goal({ status: "Achieved", flag: "Achieved", saved: 7200, over: 1200, remaining: 0, fraction: 1, required_per_month: null })]);
    renderTile();

    expect(await screen.findByText("100% funded")).toBeInTheDocument();
  });

  it("links to the Goals tab with 'View all goals'", async () => {
    respondWith([goal()]);
    const onViewAll = vi.fn();
    renderTile(onViewAll);

    const button = await screen.findByRole("button", { name: "View all goals" });
    // A filled button like the rest of the Dashboard's actions, not a text link.
    expect(button).toHaveClass("button");
    await userEvent.click(button);

    expect(onViewAll).toHaveBeenCalledTimes(1);
  });

  it("shows an empty state, and no Unassigned line, when no Goal is active", async () => {
    respondWith([]);
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
