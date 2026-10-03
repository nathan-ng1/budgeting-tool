import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import RecurringRules from "./RecurringRules.jsx";

const CATEGORIES = [
  { id: 1, type: "Expense", name: "Groceries", emoji: null, locked: false },
  { id: 2, type: "Expense", name: "Subscriptions", emoji: null, locked: false },
  { id: 3, type: "Income", name: "Salary", emoji: null, locked: false },
];

function rule(overrides = {}) {
  return {
    id: 1,
    amount: 100,
    type: "Expense",
    category: "Subscriptions",
    notes: "Streaming service",
    frequency: "Weekly",
    interval: 1,
    day: "Wednesday",
    start_date: "2026-08-05",
    end_date: null,
    ...overrides,
  };
}

let fetchMock;

/** Answer each endpoint from `rules`, so the screen reloads real state. */
function backend(rules = [], categories = CATEGORIES) {
  let stored = [...rules];
  let nextId = 100;

  return vi.fn(async (url, options = {}) => {
    const method = options.method ?? "GET";

    if (url === "/api/categories") {
      return { ok: true, status: 200, json: async () => categories };
    }
    if (url === "/api/recurring-rules/run") {
      return { ok: true, status: 200, json: async () => ({ written: 0 }) };
    }
    if (url === "/api/recurring-rules/split") {
      // Stands in for the backend's own occurrence count: every split in
      // these tests runs monthly across a 12-month schedule.
      const { total_amount: total } = JSON.parse(options.body);
      return { ok: true, status: 200, json: async () => ({ amount: total / 12, occurrences: 12 }) };
    }
    if (method === "GET") {
      return { ok: true, status: 200, json: async () => stored };
    }
    if (method === "POST") {
      const { total_amount: total, ...body } = JSON.parse(options.body);
      const created = { id: (nextId += 1), ...body, ...(total === undefined ? {} : { amount: total / 12 }) };
      stored = [...stored, created];
      return { ok: true, status: 201, json: async () => created };
    }
    if (method === "PUT") {
      const id = Number(url.split("/").pop());
      const updated = { id, ...JSON.parse(options.body) };
      stored = stored.map((r) => (r.id === id ? updated : r));
      return { ok: true, status: 200, json: async () => updated };
    }
    const id = Number(url.split("/").pop());
    stored = stored.filter((r) => r.id !== id);
    return { ok: true, status: 204 };
  });
}

beforeEach(() => {
  fetchMock = backend();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function useBackend(rules) {
  fetchMock = backend(rules);
  vi.stubGlobal("fetch", fetchMock);
}

async function openForm(name) {
  await userEvent.click(await screen.findByRole("button", { name }));
}

async function fillMonthlyYear() {
  await userEvent.type(screen.getByLabelText("Notes"), "Annual software licence");
  await userEvent.selectOptions(screen.getByLabelText("Category"), "Subscriptions");
  await userEvent.selectOptions(screen.getByLabelText("Frequency"), "Monthly");
  await userEvent.clear(screen.getByLabelText("Start Date"));
  await userEvent.type(screen.getByLabelText("Start Date"), "2026-01-15");
  await userEvent.type(screen.getByLabelText("End Date"), "2026-12-31");
}

function splitCalls() {
  return fetchMock.mock.calls.filter(([url]) => url === "/api/recurring-rules/split");
}

describe("RecurringRules", () => {
  it("lists every existing rule", async () => {
    useBackend([rule(), rule({ id: 2, notes: "Employer Pty Ltd", type: "Income", category: "Salary" })]);
    render(<RecurringRules />);

    expect(await screen.findByText("Streaming service")).toBeInTheDocument();
    expect(screen.getByText("Employer Pty Ltd")).toBeInTheDocument();
  });

  it("says so plainly when there are no rules yet", async () => {
    render(<RecurringRules />);

    expect(await screen.findByText(/No rules in the Recurring Transactions Config/i)).toBeInTheDocument();
  });

  it("creates a rule and shows it in the list without a reload", async () => {
    render(<RecurringRules />);
    await openForm("Add rule");

    await userEvent.type(screen.getByLabelText("Amount"), "100");
    await userEvent.type(screen.getByLabelText("Notes"), "Streaming service");
    await userEvent.selectOptions(screen.getByLabelText("Category"), "Subscriptions");
    await userEvent.clear(screen.getByLabelText("Start Date"));
    await userEvent.type(screen.getByLabelText("Start Date"), "2026-08-05");
    await userEvent.click(screen.getByRole("button", { name: "Save rule" }));

    expect(await screen.findByText("Streaming service")).toBeInTheDocument();

    const posted = fetchMock.mock.calls.find(([, options]) => options?.method === "POST");
    expect(JSON.parse(posted[1].body)).toMatchObject({
      amount: 100,
      type: "Expense",
      category: "Subscriptions",
      notes: "Streaming service",
      frequency: "Weekly",
      day: "Wednesday",
      start_date: "2026-08-05",
      end_date: null,
    });
  });

  it("edits an existing rule in place", async () => {
    useBackend([rule()]);
    render(<RecurringRules />);
    await openForm("Edit Streaming service");

    const amount = screen.getByLabelText("Amount");
    expect(amount).toHaveValue(100);

    await userEvent.clear(amount);
    await userEvent.type(amount, "150");
    await userEvent.click(screen.getByRole("button", { name: "Save rule" }));

    const put = await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, options]) => options?.method === "PUT");
      expect(call).toBeTruthy();
      return call;
    });
    expect(put[0]).toBe("/api/recurring-rules/1");
    expect(JSON.parse(put[1].body).amount).toBe(150);
    expect(await screen.findByText("$150.00")).toBeInTheDocument();
  });

  it("deletes a rule and drops it from the list", async () => {
    useBackend([rule()]);
    render(<RecurringRules />);

    await userEvent.click(await screen.findByRole("button", { name: "Delete Streaming service" }));

    await waitFor(() => expect(screen.queryByText("Streaming service")).not.toBeInTheDocument());
    expect(fetchMock.mock.calls.some(([url, o]) => url === "/api/recurring-rules/1" && o?.method === "DELETE")).toBe(
      true,
    );
  });

  it("shows the store's own rejection and keeps the form open to fix it", async () => {
    render(<RecurringRules />);
    await openForm("Add rule");
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ error: "Category 'Salary' is not a valid Expense Category" }),
    });

    await userEvent.type(screen.getByLabelText("Amount"), "100");
    await userEvent.type(screen.getByLabelText("Notes"), "Streaming service");
    await userEvent.selectOptions(screen.getByLabelText("Category"), "Subscriptions");
    await userEvent.click(screen.getByRole("button", { name: "Save rule" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("not a valid Expense Category");
    expect(screen.getByLabelText("Amount")).toBeInTheDocument();
  });

  it("offers only the Categories that belong to the chosen Type", async () => {
    render(<RecurringRules />);
    await openForm("Add rule");

    const category = screen.getByLabelText("Category");
    expect(within(category).getByRole("option", { name: "Subscriptions" })).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText("Type"), "Income");

    expect(within(category).queryByRole("option", { name: "Subscriptions" })).not.toBeInTheDocument();
    expect(within(category).getByRole("option", { name: "Salary" })).toBeInTheDocument();
  });

  it("shows a Category's emoji next to its name, in the table and in the Category select", async () => {
    fetchMock = backend(
      [rule()],
      [
        { id: 1, type: "Expense", name: "Groceries", emoji: null, locked: false },
        { id: 2, type: "Expense", name: "Subscriptions", emoji: "📺", locked: false },
        { id: 3, type: "Income", name: "Salary", emoji: null, locked: false },
      ],
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<RecurringRules />);

    expect(await screen.findByText("📺 Subscriptions")).toBeInTheDocument();

    await openForm("Edit Streaming service");
    const category = screen.getByLabelText("Category");
    expect(within(category).getByRole("option", { name: "📺 Subscriptions" })).toBeInTheDocument();
    // The value posted back is still the bare name, not the decorated label.
    expect(within(category).getByRole("option", { name: "📺 Subscriptions" })).toHaveValue("Subscriptions");
  });

  it("derives a Weekly rule's Day from its Start Date, so the two cannot disagree", async () => {
    render(<RecurringRules />);
    await openForm("Add rule");

    await userEvent.clear(screen.getByLabelText("Start Date"));
    await userEvent.type(screen.getByLabelText("Start Date"), "2026-08-06");

    expect(screen.getByLabelText("Day")).toHaveTextContent("Thursday");
  });

  it("lets a Monthly rule keep a Day past the end of a short month", async () => {
    render(<RecurringRules />);
    await openForm("Add rule");

    await userEvent.selectOptions(screen.getByLabelText("Frequency"), "Monthly");
    await userEvent.clear(screen.getByLabelText("Start Date"));
    await userEvent.type(screen.getByLabelText("Start Date"), "2026-02-28");
    await userEvent.clear(screen.getByLabelText("Day"));
    await userEvent.type(screen.getByLabelText("Day"), "31");

    expect(screen.getByLabelText("Day")).toHaveValue(31);
  });

  it("surfaces a failure to load rather than showing an empty list", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500, json: async () => ({}) });
    render(<RecurringRules />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/500/);
  });

  it("describes both ways Recurring Transactions get expanded", async () => {
    render(<RecurringRules />);

    expect(
      await screen.findByText(
        "Predictable items expanded into the Transaction Log via an automated Statement Export or manual run.",
      ),
    ).toBeInTheDocument();
  });

  it("disables Run now until there is at least one rule", async () => {
    render(<RecurringRules />);

    expect(await screen.findByText(/No rules in the Recurring Transactions Config/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run now" })).toBeDisabled();
  });

  it("enables Run now once a rule exists", async () => {
    useBackend([rule()]);
    render(<RecurringRules />);

    expect(await screen.findByRole("button", { name: "Run now" })).toBeEnabled();
  });

  it("runs the rules and reports how many transactions were added", async () => {
    useBackend([rule()]);
    render(<RecurringRules />);
    await screen.findByText("Streaming service");

    fetchMock.mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ written: 3 }) });
    await userEvent.click(screen.getByRole("button", { name: "Run now" }));

    expect(await screen.findByText("3 transactions added.")).toBeInTheDocument();
    const posted = fetchMock.mock.calls.find(([url]) => url === "/api/recurring-rules/run");
    expect(posted[1]).toMatchObject({ method: "POST" });
  });

  it("uses singular phrasing for exactly one transaction added", async () => {
    useBackend([rule()]);
    render(<RecurringRules />);
    await screen.findByText("Streaming service");

    fetchMock.mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ written: 1 }) });
    await userEvent.click(screen.getByRole("button", { name: "Run now" }));

    expect(await screen.findByText("1 transaction added.")).toBeInTheDocument();
  });

  it("says there's nothing new to add when the run writes zero rows", async () => {
    useBackend([rule()]);
    render(<RecurringRules />);
    await screen.findByText("Streaming service");

    fetchMock.mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ written: 0 }) });
    await userEvent.click(screen.getByRole("button", { name: "Run now" }));

    expect(await screen.findByText("Nothing new to add.")).toBeInTheDocument();
  });

  it("disables Run now and shows it's running while the request is in flight", async () => {
    useBackend([rule()]);
    render(<RecurringRules />);
    await screen.findByText("Streaming service");

    let resolveRun;
    fetchMock.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveRun = resolve;
        }),
    );

    await userEvent.click(screen.getByRole("button", { name: "Run now" }));

    expect(await screen.findByRole("button", { name: "Running…" })).toBeDisabled();

    resolveRun({ ok: true, status: 200, json: async () => ({ written: 1 }) });

    expect(await screen.findByRole("button", { name: "Run now" })).toBeEnabled();
  });

  it("splits a Total Amount across the schedule and shows the per-occurrence Amount", async () => {
    render(<RecurringRules />);
    await openForm("Add rule");
    await fillMonthlyYear();

    await userEvent.click(screen.getByLabelText("Enter a Total Amount instead"));
    await userEvent.type(screen.getByLabelText("Total Amount"), "1200");

    expect(await screen.findByText("$100.00 × 12 occurrences")).toBeInTheDocument();
    expect(JSON.parse(splitCalls().at(-1)[1].body)).toMatchObject({
      total_amount: 1200,
      frequency: "Monthly",
      interval: 1,
      day: 15,
      start_date: "2026-01-15",
      end_date: "2026-12-31",
    });
  });

  it("saves a split rule as an ordinary rule with the computed Amount", async () => {
    render(<RecurringRules />);
    await openForm("Add rule");
    await fillMonthlyYear();
    await userEvent.click(screen.getByLabelText("Enter a Total Amount instead"));
    await userEvent.type(screen.getByLabelText("Total Amount"), "1200");
    await screen.findByText("$100.00 × 12 occurrences");

    await userEvent.click(screen.getByRole("button", { name: "Save rule" }));

    expect(await screen.findByText("Annual software licence")).toBeInTheDocument();
    expect(screen.getByText("$100.00")).toBeInTheDocument();
    const posted = fetchMock.mock.calls.find(([url, o]) => url === "/api/recurring-rules" && o?.method === "POST");
    const body = JSON.parse(posted[1].body);
    expect(body.total_amount).toBe(1200);
    expect(body).not.toHaveProperty("amount");
  });

  it("fills the Amount field with the computed Amount when switched back", async () => {
    render(<RecurringRules />);
    await openForm("Add rule");
    await fillMonthlyYear();
    await userEvent.click(screen.getByLabelText("Enter a Total Amount instead"));
    await userEvent.type(screen.getByLabelText("Total Amount"), "1200");
    await screen.findByText("$100.00 × 12 occurrences");

    await userEvent.click(screen.getByLabelText("Enter a Total Amount instead"));

    expect(screen.getByLabelText("Amount")).toHaveValue(100);
  });

  it("asks for an End Date before it will split a Total Amount", async () => {
    render(<RecurringRules />);
    await openForm("Add rule");

    await userEvent.click(screen.getByLabelText("Enter a Total Amount instead"));
    await userEvent.type(screen.getByLabelText("Total Amount"), "1200");

    expect(screen.getByText("Enter an End Date to split the Total across.")).toBeInTheDocument();
    expect(screen.getByLabelText("End Date")).toBeRequired();
    expect(splitCalls()).toHaveLength(0);
  });

  it("opens an existing rule with a plain Amount, with no split carried over", async () => {
    useBackend([rule({ amount: 100, frequency: "Monthly", day: 15, start_date: "2026-01-15", end_date: "2026-12-31" })]);
    render(<RecurringRules />);
    await openForm("Edit Streaming service");

    expect(screen.getByLabelText("Amount")).toHaveValue(100);
    expect(screen.getByLabelText("Enter a Total Amount instead")).not.toBeChecked();
  });
});
