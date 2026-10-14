import { render, screen, within } from "@testing-library/react";
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
      return { ok: true, status: 200, json: async () => listing(stored) };
    }
    if (refuse && method !== "GET") {
      return { ok: false, status: 400, json: async () => ({ error: refuse }) };
    }
    if (url === "/api/goals" && method === "POST") {
      const created = goal({ id: 50, ...JSON.parse(options.body), saved: 0, fraction: 0 });
      stored = [...stored, created];
      return { ok: true, status: 201, json: async () => created };
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
