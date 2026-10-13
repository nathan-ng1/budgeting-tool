import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import YourData from "./YourData.jsx";

function respondWith(body, { ok = true, status = 200 } = {}) {
  const fetchMock = vi.fn(async () => ({ ok, status, json: async () => body }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("YourData", () => {
  it("shows where the Database lives and how big it is", async () => {
    const fetchMock = respondWith({ path: "C:\\Users\\me\\Budget\\budget.db", size_bytes: 2621440 });

    render(<YourData />);

    expect(await screen.findByText("C:\\Users\\me\\Budget\\budget.db")).toBeInTheDocument();
    expect(screen.getByText("2.5 MB")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Your data" })).toBeInTheDocument();
    expect(fetchMock.mock.calls[0][0]).toBe("/api/database");
  });

  it("sizes a small Database in kilobytes", async () => {
    respondWith({ path: "/data/budget.db", size_bytes: 53248 });

    render(<YourData />);

    expect(await screen.findByText("52.0 KB")).toBeInTheDocument();
  });

  it("shows the backend's reason when the location can't be read", async () => {
    respondWith({ error: "Database is unreadable" }, { ok: false, status: 500 });

    render(<YourData />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Database is unreadable");
  });
});
