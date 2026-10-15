import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SettingsProvider } from "../lib/settings.jsx";
import Goals from "./Goals.jsx";

function goal(overrides = {}) {
  return {
    id: 1,
    title: "Japan trip",
    description: "Flights and a rail pass",
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
    contributions: [],
    ...overrides,
  };
}

function listing(goals = [], past = []) {
  return { today: "2026-10-14", goals, past };
}

let calls;

/** A stand-in backend holding `stored` Goals, answering GET, POST and PUT. */
function backend(initial = [], { refuse = null } = {}) {
  let stored = [...initial];
  calls = [];

  const fetchMock = vi.fn(async (url, options = {}) => {
    const method = options.method ?? "GET";
    calls.push({ url, method, body: options.body ? JSON.parse(options.body) : null });

    if (url === "/api/goals" && method === "GET") {
      return {
        ok: true,
        status: 200,
        json: async () =>
          listing(
            stored.filter((g) => g.state === "active"),
            stored.filter((g) => g.state !== "active"),
          ),
      };
    }
    if (refuse && method !== "GET") {
      return { ok: false, status: 400, json: async () => ({ error: refuse }) };
    }
    if (url === "/api/goals" && method === "POST") {
      const created = goal({ id: 50, ...JSON.parse(options.body), saved: 0, fraction: 0 });
      stored = [...stored, created];
      return { ok: true, status: 201, json: async () => created };
    }
    const contribution = url.match(/^\/api\/goals\/(\d+)\/contributions$/);
    if (contribution && method === "POST") {
      const id = Number(contribution[1]);
      const sent = JSON.parse(options.body);
      stored = stored.map((g) =>
        g.id === id
          ? { ...g, saved: g.saved + sent.amount, fraction: (g.saved + sent.amount) / g.target_amount, flag: "On track" }
          : g,
      );
      return { ok: true, status: 201, json: async () => ({ id: 900, goal_id: id, ...sent }) };
    }
    const action = url.match(/^\/api\/goals\/(\d+)\/(archive|delete)$/);
    if (action && method === "POST") {
      const id = Number(action[1]);
      const state = action[2] === "archive" ? "archived" : "deleted";
      stored = stored.map((g) => (g.id === id ? { ...g, state } : g));
      return { ok: true, status: 200, json: async () => stored.find((g) => g.id === id) };
    }
    const edit = url.match(/^\/api\/goals\/(\d+)$/);
    if (edit && method === "PUT") {
      const id = Number(edit[1]);
      stored = stored.map((g) => (g.id === id ? { ...g, ...JSON.parse(options.body) } : g));
      return { ok: true, status: 200, json: async () => stored.find((g) => g.id === id) };
    }
    return { ok: false, status: 404, json: async () => ({ error: "Not found" }) };
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderGoals(settings = {}) {
  return render(
    <SettingsProvider settings={{ currency: "AUD", financial_year_start_month: 7, date_order: "day-first", ...settings }}>
      <Goals />
    </SettingsProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Goals", () => {
  it("shows an empty state and a New goal button when there are no Goals", async () => {
    backend([]);
    renderGoals();

    expect(await screen.findByText(/no goals yet/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New goal" })).toBeInTheDocument();
  });

  it("shows one card per Goal with its Status chip, headline monthly figure and progress", async () => {
    backend([goal()]);
    renderGoals();

    const card = (await screen.findByRole("heading", { name: "Japan trip" })).closest("section");
    expect(within(card).getByText("Behind")).toBeInTheDocument();
    expect(within(card).getByText("Flights and a rail pass")).toBeInTheDocument();
    expect(within(card).getByText("Save $750 / month")).toBeInTheDocument();
    expect(within(card).getByText("to finish by 31 Mar 2027 (6 months left)")).toBeInTheDocument();
    expect(within(card).getByText("$1,500 of $6,000")).toBeInTheDocument();
    expect(within(card).getByText("25%")).toBeInTheDocument();
    expect(within(card).getByText("Original plan: $667 / month")).toBeInTheDocument();
    expect(within(card).getByRole("progressbar")).toHaveAttribute("aria-valuenow", "25");
  });

  it("marks where an even pace would have the Goal today", async () => {
    backend([goal()]);
    renderGoals();

    const card = (await screen.findByRole("heading", { name: "Japan trip" })).closest("section");
    expect(within(card).getByTitle(/even pace/i)).toHaveStyle({ left: "40%" });
  });

  it("writes dates in the saved Date Order", async () => {
    backend([goal()]);
    renderGoals({ date_order: "month-first" });

    expect(await screen.findByText("to finish by Mar 31, 2027 (6 months left)")).toBeInTheDocument();
  });

  it("says a single remaining month in the singular", async () => {
    backend([goal({ months_left: 1, required_per_month: 4500 })]);
    renderGoals();

    expect(await screen.findByText("to finish by 31 Mar 2027 (1 month left)")).toBeInTheDocument();
  });

  it("shows an On track chip for a Goal at or above its pace", async () => {
    backend([goal({ flag: "On track", on_track: true, saved: 2400, fraction: 0.4 })]);
    renderGoals();

    expect(await screen.findByText("On track")).toBeInTheDocument();
  });

  it("celebrates an Achieved Goal instead of asking for a monthly figure", async () => {
    backend([
      goal({ status: "Achieved", flag: "Achieved", saved: 6200, over: 200, remaining: 0, fraction: 1, required_per_month: null }),
    ]);
    renderGoals();

    const card = (await screen.findByRole("heading", { name: "Japan trip" })).closest("section");
    expect(within(card).getByText("Achieved")).toBeInTheDocument();
    expect(within(card).getByText("Goal reached")).toBeInTheDocument();
    expect(within(card).getByText("+$200 over target")).toBeInTheDocument();
    expect(within(card).queryByText(/Original plan/)).not.toBeInTheDocument();
  });

  it("shows how far short an Ended Goal fell", async () => {
    backend([
      goal({ status: "Ended", flag: "Ended", saved: 5000, remaining: 1000, months_left: 0, required_per_month: null }),
    ]);
    renderGoals();

    const card = (await screen.findByRole("heading", { name: "Japan trip" })).closest("section");
    expect(within(card).getByText("Ended")).toBeInTheDocument();
    expect(within(card).getByText("$1,000 short")).toBeInTheDocument();
  });

  it("shows an Upcoming Goal's monthly figure from today", async () => {
    backend([goal({ status: "Upcoming", flag: "Upcoming", saved: 0, fraction: 0, pace_fraction: 0 })]);
    renderGoals();

    expect(await screen.findByText("Upcoming")).toBeInTheDocument();
    expect(screen.getByText("Save $750 / month")).toBeInTheDocument();
  });

  it("summarises the active Goals and what is saved toward them", async () => {
    backend([goal(), goal({ id: 2, title: "Car", saved: 500 })]);
    renderGoals();

    expect(await screen.findByText("2 active goals · $2,000 saved toward goals")).toBeInTheDocument();
  });

  it("counts every Goal on the tab as active, whatever its Status", async () => {
    backend([
      goal(),
      goal({ id: 2, title: "Done", status: "Achieved", flag: "Achieved", saved: 6000, remaining: 0, fraction: 1, required_per_month: null }),
      goal({ id: 3, title: "Missed", status: "Ended", flag: "Ended", months_left: 0, required_per_month: null }),
    ]);
    renderGoals();

    expect(await screen.findByText(/^3 active goals · /)).toBeInTheDocument();
  });

  it("caps an over-target Goal's percentage at 100, matching its progress bar", async () => {
    backend([goal({ status: "Achieved", flag: "Achieved", saved: 7200, over: 1200, remaining: 0, fraction: 1, required_per_month: null })]);
    renderGoals();

    const card = (await screen.findByRole("heading", { name: "Japan trip" })).closest("section");
    expect(within(card).getByText("100%")).toBeInTheDocument();
    expect(within(card).getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
  });

  it("marks the pace at zero on an Upcoming Goal's progress bar", async () => {
    backend([goal({ status: "Upcoming", flag: "Upcoming", saved: 0, fraction: 0, pace_fraction: 0 })]);
    renderGoals();

    const card = (await screen.findByRole("heading", { name: "Japan trip" })).closest("section");
    expect(within(card).getByTitle(/even pace/i)).toHaveStyle({ left: "0%" });
  });

  it("creates a Goal with the typed fields, starting today by default, and lists it", async () => {
    backend([]);
    renderGoals();
    await userEvent.click(await screen.findByRole("button", { name: "New goal" }));

    expect(screen.getByLabelText("Start date")).toHaveValue("2026-10-14");
    await userEvent.type(screen.getByLabelText("Title"), "  Laptop ");
    await userEvent.type(screen.getByLabelText("Target amount"), "2400");
    await userEvent.type(screen.getByLabelText(/End date/), "2027-02-28");
    await userEvent.type(screen.getByLabelText(/Description/), "For uni");
    await userEvent.click(screen.getByRole("button", { name: "Save goal" }));

    expect(await screen.findByRole("heading", { name: "Laptop" })).toBeInTheDocument();
    const post = calls.find((call) => call.method === "POST");
    expect(post.body).toEqual({
      title: "Laptop",
      description: "For uni",
      target_amount: 2400,
      start_date: "2026-10-14",
      end_date: "2027-02-28",
    });
    expect(screen.queryByLabelText("Title")).not.toBeInTheDocument();
  });

  it("shows the backend's reason when it refuses a Goal and keeps the form open", async () => {
    backend([], { refuse: "Another Goal already uses the title 'Laptop' (Past goals count too)" });
    renderGoals();
    await userEvent.click(await screen.findByRole("button", { name: "New goal" }));
    await userEvent.type(screen.getByLabelText("Title"), "laptop");
    await userEvent.type(screen.getByLabelText("Target amount"), "10");
    await userEvent.type(screen.getByLabelText(/End date/), "2027-02-28");
    await userEvent.click(screen.getByRole("button", { name: "Save goal" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Another Goal already uses the title");
    expect(screen.getByLabelText("Title")).toHaveValue("laptop");
  });

  it("edits a Goal from a pre-filled form and saves the changes", async () => {
    backend([goal()]);
    renderGoals();
    const card = (await screen.findByRole("heading", { name: "Japan trip" })).closest("section");
    await userEvent.click(within(card).getByRole("button", { name: "Edit" }));

    expect(screen.getByLabelText("Title")).toHaveValue("Japan trip");
    expect(screen.getByLabelText("Target amount")).toHaveValue(6000);
    expect(screen.getByLabelText("Start date")).toHaveValue("2026-07-01");
    expect(screen.getByLabelText(/End date/)).toHaveValue("2027-03-31");

    await userEvent.clear(screen.getByLabelText("Title"));
    await userEvent.type(screen.getByLabelText("Title"), "Japan 2027");
    await userEvent.click(screen.getByRole("button", { name: "Save goal" }));

    expect(await screen.findByRole("heading", { name: "Japan 2027" })).toBeInTheDocument();
    const put = calls.find((call) => call.method === "PUT");
    expect(put.url).toBe("/api/goals/1");
    expect(put.body).toMatchObject({ title: "Japan 2027", target_amount: 6000, end_date: "2027-03-31" });
  });

  describe("Add contribution", () => {
    async function openContributionForm() {
      const card = (await screen.findByRole("heading", { name: "Japan trip" })).closest("section");
      await userEvent.click(within(card).getByRole("button", { name: "Add contribution" }));
      return card;
    }

    it("opens a form with the date defaulting to today and Notes to the Goal's title", async () => {
      backend([goal()]);
      renderGoals();
      await openContributionForm();

      expect(screen.getByLabelText("Date")).toHaveValue("2026-10-14");
      expect(screen.getByLabelText("Notes")).toHaveValue("Japan trip");
      expect(screen.getByLabelText("Amount")).toHaveValue(null);
    });

    it("posts the Contribution to the Goal and refreshes saved, percent funded and the chip", async () => {
      backend([goal()]);
      renderGoals();
      const card = await openContributionForm();

      await userEvent.type(screen.getByLabelText("Amount"), "1500");
      await userEvent.click(screen.getByRole("button", { name: "Save contribution" }));

      expect(await within(card).findByText("$3,000 of $6,000")).toBeInTheDocument();
      expect(within(card).getByText("50%")).toBeInTheDocument();
      expect(within(card).getByText("On track")).toBeInTheDocument();
      const post = calls.find((call) => call.method === "POST");
      expect(post.url).toBe("/api/goals/1/contributions");
      expect(post.body).toEqual({ amount: 1500, date: "2026-10-14", notes: "Japan trip" });
      expect(screen.queryByLabelText("Amount")).not.toBeInTheDocument();
    });

    it("sends the edited date and Notes", async () => {
      backend([goal()]);
      renderGoals();
      await openContributionForm();

      await userEvent.type(screen.getByLabelText("Amount"), "20.50");
      await userEvent.clear(screen.getByLabelText("Notes"));
      await userEvent.type(screen.getByLabelText("Notes"), "Bonus");
      await userEvent.clear(screen.getByLabelText("Date"));
      await userEvent.type(screen.getByLabelText("Date"), "2026-10-01");
      await userEvent.click(screen.getByRole("button", { name: "Save contribution" }));

      await screen.findByText("$1,521 of $6,000");
      const post = calls.find((call) => call.method === "POST");
      expect(post.body).toEqual({ amount: 20.5, date: "2026-10-01", notes: "Bonus" });
    });

    it("shows the backend's reason when it refuses and keeps the form open", async () => {
      backend([goal()], { refuse: "Goal 'Japan trip' is not active, so it can't take new Contributions" });
      renderGoals();
      await openContributionForm();
      await userEvent.type(screen.getByLabelText("Amount"), "10");
      await userEvent.click(screen.getByRole("button", { name: "Save contribution" }));

      expect(await screen.findByRole("alert")).toHaveTextContent("is not active");
      expect(screen.getByLabelText("Amount")).toHaveValue(10);
    });

    it("closes without saving when cancelled", async () => {
      backend([goal()]);
      renderGoals();
      await openContributionForm();
      await userEvent.click(screen.getByRole("button", { name: "Cancel" }));

      expect(screen.queryByLabelText("Amount")).not.toBeInTheDocument();
      expect(calls.some((call) => call.method === "POST")).toBe(false);
    });
  });

  describe("Past goals", () => {
    it("archives a Goal into a collapsed Past goals list with an Archived badge", async () => {
      backend([goal(), goal({ id: 2, title: "Laptop" })]);
      renderGoals();
      const card = (await screen.findByRole("heading", { name: "Japan trip" })).closest("section");
      await userEvent.click(within(card).getByRole("button", { name: "Archive" }));

      expect(await screen.findByText("Past goals (1)")).toBeInTheDocument();
      expect(calls.find((call) => call.url === "/api/goals/1/archive").method).toBe("POST");
      expect(screen.queryByRole("heading", { name: "Japan trip" })).not.toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Laptop" })).toBeInTheDocument();
      const past = screen.getByText("Past goals (1)").closest("details");
      expect(past).not.toHaveAttribute("open");
      expect(within(past).getByText("Japan trip")).toBeInTheDocument();
      expect(within(past).getByText("Archived")).toBeInTheDocument();
    });

    it("deletes a Goal into Past goals with a Deleted badge", async () => {
      backend([goal()]);
      renderGoals();
      const card = (await screen.findByRole("heading", { name: "Japan trip" })).closest("section");
      await userEvent.click(within(card).getByRole("button", { name: "Delete" }));

      const past = (await screen.findByText("Past goals (1)")).closest("details");
      expect(calls.find((call) => call.url === "/api/goals/1/delete").method).toBe("POST");
      expect(within(past).getByText("Deleted")).toBeInTheDocument();
    });

    it("shows a Past goal's saved of target and offers no way to add a contribution", async () => {
      backend([goal({ state: "archived" })]);
      renderGoals();

      const past = (await screen.findByText("Past goals (1)")).closest("details");
      expect(within(past).getByText("$1,500 of $6,000")).toBeInTheDocument();
      expect(within(past).getByRole("button", { name: "Reactivate" })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Add contribution" })).not.toBeInTheDocument();
      expect(screen.getByText(/no goals yet/i)).toBeInTheDocument();
    });

    it("shows no Past goals section when there are none", async () => {
      backend([goal()]);
      renderGoals();
      await screen.findByRole("heading", { name: "Japan trip" });

      expect(screen.queryByText(/Past goals/)).not.toBeInTheDocument();
    });

    it("reactivates through the pre-filled edit form, so extending the end date is one step", async () => {
      backend([goal({ state: "deleted" })]);
      renderGoals();
      await userEvent.click(await screen.findByRole("button", { name: "Reactivate" }));

      expect(screen.getByLabelText("Title")).toHaveValue("Japan trip");
      expect(screen.getByLabelText(/End date/)).toHaveValue("2027-03-31");
      fireEvent.change(screen.getByLabelText(/End date/), { target: { value: "2027-09-30" } });
      await userEvent.click(screen.getByRole("button", { name: "Save goal" }));

      expect(await screen.findByRole("heading", { name: "Japan trip" })).toBeInTheDocument();
      const put = calls.find((call) => call.method === "PUT");
      expect(put.url).toBe("/api/goals/1");
      expect(put.body).toMatchObject({ end_date: "2027-09-30", state: "active" });
      expect(screen.queryByText(/Past goals/)).not.toBeInTheDocument();
    });

    it("does not send a state when editing an active Goal", async () => {
      backend([goal()]);
      renderGoals();
      const card = (await screen.findByRole("heading", { name: "Japan trip" })).closest("section");
      await userEvent.click(within(card).getByRole("button", { name: "Edit" }));
      await userEvent.click(screen.getByRole("button", { name: "Save goal" }));

      await screen.findByRole("heading", { name: "Japan trip" });
      expect(calls.find((call) => call.method === "PUT").body).not.toHaveProperty("state");
    });
  });

  describe("Details view", () => {
    const LEDGER = [
      { date: "2026-08-15", notes: "Bonus", amount: 1000 },
      { date: "2026-10-01", notes: "Japan trip", amount: 500 },
    ];

    async function openDetails(settings = {}, overrides = {}) {
      backend([goal({ contributions: LEDGER, ...overrides })]);
      renderGoals(settings);
      await userEvent.click(await screen.findByRole("button", { name: "Details" }));
    }

    it("opens from a Details button on the card, in place of the grid", async () => {
      await openDetails();

      expect(screen.getByRole("heading", { name: "Japan trip" })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Details" })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "New goal" })).not.toBeInTheDocument();
    });

    it("shows the Status chip beside the title and the stats strip, without the headline in it", async () => {
      await openDetails();

      const view = screen.getByRole("heading", { name: "Japan trip" }).closest("section");
      expect(within(view).getByText("Behind")).toBeInTheDocument();
      const stats = within(view).getByLabelText("Goal stats");
      expect(within(stats).getAllByRole("term").map((term) => term.textContent)).toEqual([
        "Saved",
        "Left",
        "Remaining time",
        "End date",
        "Original plan",
        "Start date",
      ]);
      expect(within(stats).getAllByRole("definition").map((value) => value.textContent)).toEqual([
        "$1,500 of $6,000",
        "$4,500",
        "6 months",
        "31 Mar 2027",
        "$667 / month",
        "1 Jul 2026",
      ]);
    });

    it("puts what the Goal needs per month in a headline pill beside All goals", async () => {
      await openDetails();

      const pill = within(screen.getByRole("heading", { name: "Japan trip" }).closest("section")).getByLabelText("Goal headline");
      expect(pill).toHaveTextContent("You need to save");
      expect(pill).toHaveTextContent("$750 / month");
      expect(pill.nextElementSibling).toHaveTextContent("All goals");
    });

    it("says how an Achieved Goal finished in the headline pill, with any amount over target", async () => {
      await openDetails(
        {},
        { status: "Achieved", flag: "Achieved", saved: 11000, over: 5000, remaining: 0, fraction: 1, months_left: 0, required_per_month: null },
      );

      const pill = screen.getByLabelText("Goal headline");
      expect(pill).toHaveTextContent("Status");
      expect(pill).toHaveTextContent("Goal reached");
      expect(pill).toHaveTextContent("+$5,000 over target");
    });

    it("shows what an Ended Goal fell short by in the headline pill", async () => {
      await openDetails(
        {},
        { status: "Ended", flag: "Ended", remaining: 1000, months_left: 0, required_per_month: null },
      );

      const pill = screen.getByLabelText("Goal headline");
      expect(pill).toHaveTextContent("Shortfall");
      expect(pill).toHaveTextContent("$1,000 short");
    });

    it("shows an Achieved Goal past its end date as Achieved, not Ended, under Remaining time", async () => {
      await openDetails(
        {},
        { status: "Achieved", flag: "Achieved", saved: 6000, remaining: 0, fraction: 1, months_left: 0, required_per_month: null },
      );

      const stats = within(screen.getByRole("heading", { name: "Japan trip" }).closest("section")).getByLabelText("Goal stats");
      const remaining = within(stats).getByText("Remaining time").closest("div");
      expect(within(remaining).getByRole("definition")).toHaveTextContent("Achieved");
    });

    it("lists the Contributions as Date, Notes and Amount, newest first", async () => {
      await openDetails();

      const ledger = screen.getByRole("table", { name: "Contributions" });
      expect(within(ledger).getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["Date", "Notes", "Amount"]);
      const rows = within(ledger).getAllByRole("row").slice(1);
      expect(rows.map((row) => within(row).getAllByRole("cell").map((c) => c.textContent))).toEqual([
        ["1 Oct 2026", "Japan trip", "$500"],
        ["15 Aug 2026", "Bonus", "$1,000"],
      ]);
    });

    it("follows the Date Order and Display Currency settings", async () => {
      await openDetails({ date_order: "month-first", currency: "EUR" });

      const ledger = screen.getByRole("table", { name: "Contributions" });
      expect(within(ledger).getByText("Aug 15, 2026")).toBeInTheDocument();
      expect(within(ledger).getByText(/^1\.000\s€$/)).toBeInTheDocument();
      expect(within(screen.getByLabelText("Goal stats")).getByText("Mar 31, 2027")).toBeInTheDocument();
    });

    it("says so when the Goal has no Contributions yet", async () => {
      await openDetails({}, { contributions: [], saved: 0 });

      expect(screen.getByText(/no contributions yet/i)).toBeInTheDocument();
    });

    it("draws the trajectory chart with a point per Contribution and the labels in place", async () => {
      await openDetails();

      const chart = screen.getByRole("img", { name: /japan trip/i });
      expect(chart.querySelectorAll("[data-contribution-point]")).toHaveLength(2);
      for (const label of ["Target $6,000", "Even pace", "Saved $1,500", "Today", "Amount saved", "Date"]) {
        expect(within(chart).getByText(label)).toBeInTheDocument();
      }
      expect(within(chart).getByText("$2,000")).toBeInTheDocument();
      expect(within(chart).getByText("Nov")).toBeInTheDocument();
    });

    it("carries the Saved line flat to today at the running total", async () => {
      await openDetails();

      const line = screen.getByRole("img", { name: /japan trip/i }).querySelector("[data-saved-line]");
      const points = line
        .getAttribute("points")
        .split(" ")
        .map((pair) => pair.split(",").map(Number));
      // Start at zero, one point per Contribution, then today: the last two share
      // a height only when the line is carried flat.
      expect(points).toHaveLength(4);
      expect(points[3][1]).toBe(points[2][1]);
      expect(points[3][0]).toBeGreaterThan(points[2][0]);
    });

    it("has no actions apart from returning to the grid", async () => {
      await openDetails();

      expect(screen.getAllByRole("button").map((b) => b.textContent)).toEqual(["← All goals"]);
    });

    it("returns to the card grid from the All goals button", async () => {
      await openDetails();
      await userEvent.click(screen.getByRole("button", { name: /all goals/i }));

      expect(await screen.findByRole("button", { name: "Details" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "New goal" })).toBeInTheDocument();
    });
  });

  it("closes the form without saving when cancelled", async () => {
    backend([]);
    renderGoals();
    await userEvent.click(await screen.findByRole("button", { name: "New goal" }));
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.queryByLabelText("Title")).not.toBeInTheDocument();
    expect(calls.some((call) => call.method === "POST")).toBe(false);
  });

  it("explains a failed load rather than showing an empty tab", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 500, json: async () => ({}) })));
    renderGoals();

    expect(await screen.findByRole("alert")).toHaveTextContent("500");
  });
});
