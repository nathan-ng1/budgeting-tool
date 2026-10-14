import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SettingsProvider } from "../lib/settings.jsx";
import Goals from "./Goals.jsx";

function goal(id, title) {
  return {
    id,
    title,
    description: null,
    target_amount: 6000,
    start_date: "2026-07-01",
    end_date: "2027-03-31",
    state: "active",
    saved: 0,
    remaining: 6000,
    over: 0,
    fraction: 0,
    status: "Active",
    flag: "Behind",
    pace_fraction: 0.4,
    pace_amount: 2400,
    on_track: false,
    months_left: 6,
    required_per_month: 750,
    original_plan_per_month: 666.67,
  };
}

const GOALS = [goal(1, "Japan trip"), goal(2, "New car")];

let calls;

/**
 * A stand-in backend: lists GOALS, answers the month Overview with `unallocated`,
 * and answers the split endpoints with whatever `rows` it is given - the rows
 * themselves are the server's to compute, so the UI is only checked for
 * showing and sending the right things.
 */
function backend({ unallocated = 1240, rows = [], refuse = null } = {}) {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url, options = {}) => {
      const method = options.method ?? "GET";
      calls.push({ url, method, body: options.body ? JSON.parse(options.body) : null });

      if (url === "/api/goals") {
        return { ok: true, status: 200, json: async () => ({ today: "2026-10-14", goals: GOALS, past: [] }) };
      }
      if (url.startsWith("/api/overview")) {
        return { ok: true, status: 200, json: async () => ({ stat_tiles: { unallocated } }) };
      }
      if (url === "/api/goals/split/preview") {
        return { ok: true, status: 200, json: async () => ({ rows }) };
      }
      if (url === "/api/goals/split") {
        if (refuse) {
          return { ok: false, status: 400, json: async () => ({ error: refuse }) };
        }
        return { ok: true, status: 201, json: async () => ({ rows }) };
      }
      return { ok: false, status: 404, json: async () => ({ error: "Not found" }) };
    }),
  );
}

const ROWS = [
  { date: "2026-10-14", amount: 620, type: "Savings", category: "Goals", notes: "Japan trip", goal_id: 1, goal_title: "Japan trip" },
  { date: "2026-10-14", amount: 310, type: "Savings", category: "Goals", notes: "New car", goal_id: 2, goal_title: "New car" },
  { date: "2026-10-14", amount: 310, type: "Savings", category: "Savings", notes: "Split savings remainder", goal_id: null, goal_title: null },
];

function renderGoals(props = {}) {
  return render(
    <SettingsProvider settings={{ currency: "AUD", financial_year_start_month: 7, date_order: "day-first" }}>
      <Goals {...props} />
    </SettingsProvider>,
  );
}

async function openPanel() {
  await userEvent.click(await screen.findByRole("button", { name: "Split savings" }));
  return screen.findByRole("form", { name: "Split savings" });
}

function splitCalls(path) {
  return calls.filter((call) => call.url === path);
}

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Split savings", () => {
  it("prefills the total from the selected month's Unallocated", async () => {
    backend({ unallocated: 1240 });
    renderGoals({ selectedMonth: { year: 2026, month: 9 } });

    await openPanel();

    expect(await screen.findByLabelText("Total to split")).toHaveValue(1240);
    expect(calls.some((call) => call.url === "/api/overview?year=2026&month=9")).toBe(true);
  });

  it("uses today's month when the Overview has no month selected", async () => {
    backend({ unallocated: 500 });
    renderGoals({ selectedMonth: null });

    await openPanel();

    expect(await screen.findByLabelText("Total to split")).toHaveValue(500);
    expect(calls.some((call) => call.url === "/api/overview?year=2026&month=10")).toBe(true);
  });

  it("leaves the total empty when Unallocated is not positive", async () => {
    backend({ unallocated: -50 });
    renderGoals();

    await openPanel();

    await waitFor(() => expect(calls.some((call) => call.url.startsWith("/api/overview"))).toBe(true));
    expect(screen.getByLabelText("Total to split")).toHaveValue(null);
  });

  it("offers a percentage per active Goal and a Savings or Investments remainder", async () => {
    backend();
    renderGoals();

    await openPanel();

    expect(screen.getByLabelText("Japan trip percentage")).toBeInTheDocument();
    expect(screen.getByLabelText("New car percentage")).toBeInTheDocument();
    expect(screen.getByLabelText("Remainder Category")).toHaveValue("Savings");
    expect(screen.getByRole("option", { name: "Investments" })).toBeInTheDocument();
  });

  it("shows the server's rows as a live preview of what will be written", async () => {
    backend({ unallocated: 1240, rows: ROWS });
    renderGoals();
    await openPanel();

    await userEvent.type(screen.getByLabelText("Japan trip percentage"), "50");
    await userEvent.type(screen.getByLabelText("New car percentage"), "25");

    expect(await screen.findByText("Split savings remainder")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Transactions to be written" })).toHaveTextContent("$620.00");
    const lastPreview = splitCalls("/api/goals/split/preview").at(-1);
    expect(lastPreview.body).toEqual({
      total: 1240,
      date: "2026-10-14",
      allocations: [
        { goal_id: 1, percent: 50 },
        { goal_id: 2, percent: 25 },
      ],
      remainder_category: "Savings",
    });
  });

  it("caps the percentages at 100 with an inline error and asks for no preview or split", async () => {
    backend({ rows: ROWS });
    renderGoals();
    await openPanel();

    await userEvent.type(screen.getByLabelText("Japan trip percentage"), "70");
    await userEvent.type(screen.getByLabelText("New car percentage"), "40");

    expect(await screen.findByRole("alert")).toHaveTextContent(/more than 100%/i);
    expect(screen.getByRole("button", { name: "Write split" })).toBeDisabled();
    const sums = splitCalls("/api/goals/split/preview").map((call) =>
      call.body.allocations.reduce((sum, allocation) => sum + allocation.percent, 0),
    );
    expect(sums.every((sum) => sum <= 100)).toBe(true);
  });

  it("writes the split, confirms in one line, and reloads the Goals", async () => {
    backend({ rows: ROWS });
    renderGoals();
    await openPanel();
    await userEvent.type(screen.getByLabelText("Japan trip percentage"), "50");
    await userEvent.type(screen.getByLabelText("New car percentage"), "25");
    await screen.findByText("Split savings remainder");
    const goalReloads = calls.filter((call) => call.url === "/api/goals").length;

    await userEvent.click(screen.getByRole("button", { name: "Write split" }));

    expect(await screen.findByText("Wrote 3 Transactions totalling $1,240.00: 2 Contributions and $310.00 to Savings.")).toBeInTheDocument();
    expect(splitCalls("/api/goals/split")).toHaveLength(1);
    expect(calls.filter((call) => call.url === "/api/goals").length).toBeGreaterThan(goalReloads);
  });

  it("says when Goals took everything and no remainder row was written", async () => {
    backend({ rows: ROWS.slice(0, 2) });
    renderGoals();
    await openPanel();
    await userEvent.type(screen.getByLabelText("Japan trip percentage"), "60");
    await userEvent.type(screen.getByLabelText("New car percentage"), "40");
    await screen.findByRole("table", { name: "Transactions to be written" });

    await userEvent.click(screen.getByRole("button", { name: "Write split" }));

    expect(await screen.findByText("Wrote 2 Transactions totalling $930.00: 2 Contributions.")).toBeInTheDocument();
  });

  it("prefills the percentages from the last split", async () => {
    backend({ rows: ROWS });
    const first = renderGoals();
    await openPanel();
    await userEvent.type(screen.getByLabelText("Japan trip percentage"), "50");
    await userEvent.type(screen.getByLabelText("New car percentage"), "25");
    await screen.findByText("Split savings remainder");
    await userEvent.click(screen.getByRole("button", { name: "Write split" }));
    await screen.findByText(/^Wrote 3 Transactions/);
    first.unmount();

    backend({ rows: ROWS });
    renderGoals();
    await openPanel();

    expect(screen.getByLabelText("Japan trip percentage")).toHaveValue(50);
    expect(screen.getByLabelText("New car percentage")).toHaveValue(25);
  });

  it("shows why the server refused a split and keeps the panel open", async () => {
    backend({ rows: ROWS, refuse: "Goal 'New car' is not active, so it can't take new Contributions" });
    renderGoals();
    await openPanel();
    await userEvent.type(screen.getByLabelText("Japan trip percentage"), "50");
    await screen.findByRole("table", { name: "Transactions to be written" });

    await userEvent.click(screen.getByRole("button", { name: "Write split" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("is not active");
    expect(screen.getByRole("form", { name: "Split savings" })).toBeInTheDocument();
  });
});
