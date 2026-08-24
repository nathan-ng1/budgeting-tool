import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import CategoryManagement from "./CategoryManagement.jsx";

function category(overrides = {}) {
  return { id: 1, type: "Expense", name: "Groceries", emoji: null, locked: false, ...overrides };
}

let fetchMock;

/** Answer each endpoint from `categories`, so the screen reloads real state. */
function backend(categories = []) {
  let stored = [...categories];
  let nextId = 100;

  return vi.fn(async (url, options = {}) => {
    const method = options.method ?? "GET";

    if (method === "GET") {
      return { ok: true, status: 200, json: async () => stored };
    }
    if (method === "POST") {
      const created = { id: (nextId += 1), emoji: null, locked: false, ...JSON.parse(options.body) };
      stored = [...stored, created];
      return { ok: true, status: 201, json: async () => created };
    }
    if (method === "PUT") {
      const id = Number(url.split("/").pop());
      const existing = stored.find((c) => c.id === id);
      const updated = { ...existing, ...JSON.parse(options.body) };
      stored = stored.map((c) => (c.id === id ? updated : c));
      return { ok: true, status: 200, json: async () => updated };
    }
    const id = Number(url.split("/").pop());
    stored = stored.filter((c) => c.id !== id);
    return { ok: true, status: 204 };
  });
}

function useBackend(categories) {
  fetchMock = backend(categories);
  vi.stubGlobal("fetch", fetchMock);
}

beforeEach(() => {
  fetchMock = backend();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("CategoryManagement", () => {
  it("lists every existing Category under its Type", async () => {
    useBackend([category({ name: "Groceries", type: "Expense" }), category({ id: 2, name: "Salary", type: "Income" })]);
    render(<CategoryManagement />);

    expect(await screen.findByText("Groceries")).toBeInTheDocument();
    expect(screen.getByText("Salary")).toBeInTheDocument();
  });

  it("shows a Category's emoji next to its name, and shows nothing extra when it has none", async () => {
    useBackend([category({ name: "Groceries", emoji: "🛒" }), category({ id: 2, name: "Transport", emoji: null })]);
    render(<CategoryManagement />);

    expect(await screen.findByText("🛒")).toBeInTheDocument();
    expect(screen.getByText("Transport")).toBeInTheDocument();
  });

  it("adds a Category under a Type and shows it without a reload", async () => {
    render(<CategoryManagement />);

    await userEvent.click((await screen.findAllByRole("button", { name: "+ Add category" }))[1]);
    await userEvent.type(screen.getByLabelText("Category name"), "Pets");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Pets")).toBeInTheDocument();
    const posted = fetchMock.mock.calls.find(([, options]) => options?.method === "POST");
    expect(JSON.parse(posted[1].body)).toMatchObject({ type: "Expense", name: "Pets" });
  });

  it("adding a Category without picking an emoji sends a null emoji", async () => {
    render(<CategoryManagement />);

    await userEvent.click((await screen.findAllByRole("button", { name: "+ Add category" }))[1]);
    await userEvent.type(screen.getByLabelText("Category name"), "Pets");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    await screen.findByText("Pets");
    const posted = fetchMock.mock.calls.find(([, options]) => options?.method === "POST");
    expect(JSON.parse(posted[1].body).emoji).toBeNull();
  });

  it("renames a Category in place", async () => {
    useBackend([category({ name: "Groceries" })]);
    render(<CategoryManagement />);
    await userEvent.click(await screen.findByRole("button", { name: "Edit Groceries" }));

    const name = screen.getByLabelText("Category name");
    await userEvent.clear(name);
    await userEvent.type(name, "Food");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Food")).toBeInTheDocument();
    const put = fetchMock.mock.calls.find(([, options]) => options?.method === "PUT");
    expect(put[0]).toBe("/api/categories/1");
    expect(JSON.parse(put[1].body).name).toBe("Food");
  });

  it("only deletes a Category after the inline confirmation step", async () => {
    useBackend([category({ name: "Groceries" })]);
    render(<CategoryManagement />);
    await userEvent.click(await screen.findByRole("button", { name: "Delete Groceries" }));

    // Still there, and no DELETE sent yet - the confirm step hasn't happened.
    expect(screen.getByText(/Groceries/)).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([, o]) => o?.method === "DELETE")).toBe(false);

    await userEvent.click(screen.getByRole("button", { name: "Confirm delete Groceries" }));

    await waitFor(() => expect(screen.queryByText("Groceries")).not.toBeInTheDocument());
    expect(fetchMock.mock.calls.some(([url, o]) => url === "/api/categories/1" && o?.method === "DELETE")).toBe(true);
  });

  it("cancelling the delete confirmation leaves the Category alone", async () => {
    useBackend([category({ name: "Groceries" })]);
    render(<CategoryManagement />);
    await userEvent.click(await screen.findByRole("button", { name: "Delete Groceries" }));

    await userEvent.click(screen.getByRole("button", { name: "Cancel delete" }));

    expect(screen.getByText("Groceries")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([, o]) => o?.method === "DELETE")).toBe(false);
  });

  it("shows no edit or delete control for a locked Category", async () => {
    useBackend([category({ name: "Beem Adjustment", locked: true })]);
    render(<CategoryManagement />);

    await screen.findByText("Beem Adjustment");
    expect(screen.queryByRole("button", { name: "Edit Beem Adjustment" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete Beem Adjustment" })).not.toBeInTheDocument();
  });

  it("shows the store's own rejection and keeps the form open to fix it", async () => {
    render(<CategoryManagement />);
    await userEvent.click((await screen.findAllByRole("button", { name: "+ Add category" }))[1]);
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ error: "Category 'Groceries' already exists" }),
    });

    await userEvent.type(screen.getByLabelText("Category name"), "Groceries");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("already exists");
    expect(screen.getByLabelText("Category name")).toBeInTheDocument();
  });

  it("surfaces a failure to load rather than showing an empty screen", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500, json: async () => ({}) });
    render(<CategoryManagement />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/500/);
  });
});
