import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

describe("YourData backup", () => {
  function backend({ lastBackedUp }) {
    let info = { path: "/data/budget.db", size_bytes: 53248, last_backed_up: lastBackedUp };
    return vi.fn(async (url) => {
      if (url === "/api/database/backup") {
        info = { ...info, last_backed_up: "2026-10-13T14:25:30+11:00" };
        return {
          ok: true,
          status: 200,
          headers: { get: () => 'attachment; filename="budget-backup-20261013-142530.db"' },
          blob: async () => new Blob(["sqlite"]),
        };
      }
      return { ok: true, status: 200, json: async () => info };
    });
  }

  it("says Never when no Backup has been made", async () => {
    vi.stubGlobal("fetch", backend({ lastBackedUp: null }));

    render(<YourData />);

    expect(await screen.findByText("Last backed up")).toBeInTheDocument();
    expect(screen.getByText("Never")).toBeInTheDocument();
  });

  it("downloads a Backup under its timestamped name and then shows when it was made", async () => {
    const fetchMock = backend({ lastBackedUp: null });
    vi.stubGlobal("fetch", fetchMock);
    const createObjectURL = vi.fn(() => "blob:backup");
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL: vi.fn() });
    const saved = [];
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function () {
      saved.push({ href: this.href, download: this.download });
    });

    render(<YourData />);
    await userEvent.click(await screen.findByRole("button", { name: "Download Backup" }));

    await waitFor(() => expect(screen.queryByText("Never")).not.toBeInTheDocument());
    expect(fetchMock.mock.calls.map(([url]) => url)).toContain("/api/database/backup");
    expect(saved).toEqual([{ href: "blob:backup", download: "budget-backup-20261013-142530.db" }]);
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    click.mockRestore();
  });

  it("shows the backend's reason when the Backup fails", async () => {
    vi.stubGlobal("fetch", async (url) =>
      url === "/api/database/backup"
        ? { ok: false, status: 500, json: async () => ({ error: "disk full" }) }
        : { ok: true, status: 200, json: async () => ({ path: "/d.db", size_bytes: 1, last_backed_up: null }) },
    );

    render(<YourData />);
    await userEvent.click(await screen.findByRole("button", { name: "Download Backup" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("disk full");
  });
});
