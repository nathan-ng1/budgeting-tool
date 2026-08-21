import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import RecurringRules from "./RecurringRules.jsx";

const CATEGORIES = { Expense: ["Groceries", "Subscriptions"], Income: ["Salary"] };

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
function backend(rules = []) {
  let stored = [...rules];
  let nextId = 100;

  return vi.fn(async (url, options = {}) => {
    const method = options.method ?? "GET";

    if (url === "/api/categories") {
      return { ok: true, status: 200, json: async () => CATEGORIES };
    }
    if (method === "GET") {
      return { ok: true, status: 200, json: async () => stored };
    }
    if (method === "POST") {
      const created = { id: (nextId += 1), ...JSON.parse(options.body) };
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
});
