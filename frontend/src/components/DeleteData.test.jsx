import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DeleteData from "./DeleteData.jsx";

const SUMMARY = {
  path: "D:\\Budget\\budget.db",
  transactions: 1234,
  recurring_rules: 5,
  category_budgets: 40,
  custom_categories: 3,
  goals: 4,
  display_settings: 2,
  pre_migration_files: 2,
};

// A stand-in backend: the summary, the Backup download and the reset.
function backend({ resetReply = { ok: true, status: 200, body: { path: SUMMARY.path } } } = {}) {
  const fetchMock = vi.fn(async (url) => {
    if (url === "/api/database/reset-summary") {
      return { ok: true, status: 200, json: async () => SUMMARY };
    }
    if (url === "/api/database/backup") {
      return {
        ok: true,
        status: 200,
        headers: { get: () => 'attachment; filename="budget-backup.db"' },
        blob: async () => new Blob(["sqlite"]),
      };
    }
    return { ok: resetReply.ok, status: resetReply.status, json: async () => resetReply.body };
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function openDialog() {
  await userEvent.click(screen.getByRole("button", { name: "Delete data and reset dashboard" }));
  return screen.findByRole("dialog");
}

function finalButton(dialog) {
  return within(dialog).getByRole("button", { name: "Delete everything" });
}

beforeEach(() => {
  URL.createObjectURL = vi.fn(() => "blob:backup");
  URL.revokeObjectURL = vi.fn();
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("DeleteData", () => {
  it("offers the danger button but fetches and shows nothing until it is pressed", () => {
    const fetchMock = backend();

    render(<DeleteData />);

    expect(screen.getByRole("button", { name: "Delete data and reset dashboard" })).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("lists live counts, the path, the pre-migration files and what is not touched", async () => {
    backend();
    render(<DeleteData />);

    const dialog = await openDialog();

    expect(await within(dialog).findByText("D:\\Budget\\budget.db")).toBeInTheDocument();
    expect(within(dialog).getByText(/1,234 Transactions/)).toBeInTheDocument();
    expect(within(dialog).getByText(/5 Recurring Transactions Config rules/)).toBeInTheDocument();
    expect(within(dialog).getByText(/40 Category Budgets/)).toBeInTheDocument();
    expect(within(dialog).getByText(/3 custom Categories/)).toBeInTheDocument();
    expect(within(dialog).getByText(/4 Goals/)).toBeInTheDocument();
    expect(within(dialog).getByText(/2 Display Settings/)).toBeInTheDocument();
    expect(within(dialog).getByText(/2 pre-migration copies/)).toBeInTheDocument();
    expect(within(dialog).getByText(/Processed archive/)).toHaveTextContent(/not touched/i);
    expect(within(dialog).getByText(/Transactions Inbox/)).toBeInTheDocument();
    expect(within(dialog).getByText(/saved theme and Financial Year/)).toBeInTheDocument();
  });

  it("singularises counts of one", async () => {
    const fetchMock = backend();
    fetchMock.mockImplementationOnce(async () => ({
      ok: true,
      status: 200,
      json: async () => ({ ...SUMMARY, transactions: 1, pre_migration_files: 1 }),
    }));
    render(<DeleteData />);

    const dialog = await openDialog();

    expect(await within(dialog).findByText(/1 Transaction\b(?!s)/)).toBeInTheDocument();
    expect(within(dialog).getByText(/1 pre-migration copy\b/)).toBeInTheDocument();
  });

  describe("the final button", () => {
    async function ready() {
      backend();
      render(<DeleteData />);
      const dialog = await openDialog();
      await within(dialog).findByText("D:\\Budget\\budget.db");
      return dialog;
    }
    const type = (dialog, text) => userEvent.type(within(dialog).getByLabelText(/type DELETE/i), text);
    const tick = (dialog) => userEvent.click(within(dialog).getByRole("checkbox", { name: /no Backup/i }));
    const backUp = async (dialog) => {
      await userEvent.click(within(dialog).getByRole("button", { name: "Download Backup first" }));
      await waitFor(() => expect(within(dialog).getByText(/Backup downloaded/i)).toBeInTheDocument());
    };

    it("starts disabled", async () => {
      const dialog = await ready();
      expect(finalButton(dialog)).toBeDisabled();
    });

    it("stays disabled with DELETE typed but neither a Backup nor the box", async () => {
      const dialog = await ready();
      await type(dialog, "DELETE");
      expect(finalButton(dialog)).toBeDisabled();
    });

    it("stays disabled with a Backup downloaded but DELETE not typed", async () => {
      const dialog = await ready();
      await backUp(dialog);
      expect(finalButton(dialog)).toBeDisabled();
    });

    it("stays disabled with the box ticked but DELETE not typed", async () => {
      const dialog = await ready();
      await tick(dialog);
      expect(finalButton(dialog)).toBeDisabled();
    });

    it("stays disabled when the typed text is not exactly DELETE", async () => {
      const dialog = await ready();
      await tick(dialog);
      await type(dialog, "delete");
      expect(finalButton(dialog)).toBeDisabled();
    });

    it("enables with a Backup downloaded and DELETE typed", async () => {
      const dialog = await ready();
      await backUp(dialog);
      await type(dialog, "DELETE");
      expect(finalButton(dialog)).toBeEnabled();
    });

    it("enables with the no-Backup box ticked and DELETE typed", async () => {
      const dialog = await ready();
      await tick(dialog);
      await type(dialog, "DELETE");
      expect(finalButton(dialog)).toBeEnabled();
    });
  });

  it("downloads the Backup from the dialog", async () => {
    const fetchMock = backend();
    render(<DeleteData />);
    const dialog = await openDialog();

    await userEvent.click(within(dialog).getByRole("button", { name: "Download Backup first" }));

    await waitFor(() => expect(fetchMock.mock.calls.map(([url]) => url)).toContain("/api/database/backup"));
  });

  it("sends the typed confirmation, then reloads the page", async () => {
    const fetchMock = backend();
    const onReset = vi.fn();
    render(<DeleteData onReset={onReset} />);
    const dialog = await openDialog();
    await within(dialog).findByText("D:\\Budget\\budget.db");

    await userEvent.click(within(dialog).getByRole("checkbox", { name: /no Backup/i }));
    await userEvent.type(within(dialog).getByLabelText(/type DELETE/i), "DELETE");
    expect(onReset).not.toHaveBeenCalled();
    await userEvent.click(finalButton(dialog));

    await waitFor(() => expect(onReset).toHaveBeenCalledTimes(1));
    const [url, options] = fetchMock.mock.calls.at(-1);
    expect(url).toBe("/api/database/reset");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ confirmation: "DELETE" });
  });

  it("shows why and does not reload when the delete fails", async () => {
    backend({ resetReply: { ok: false, status: 500, body: { error: "Couldn't delete budget.db" } } });
    const onReset = vi.fn();
    render(<DeleteData onReset={onReset} />);
    const dialog = await openDialog();
    await within(dialog).findByText("D:\\Budget\\budget.db");

    await userEvent.click(within(dialog).getByRole("checkbox", { name: /no Backup/i }));
    await userEvent.type(within(dialog).getByLabelText(/type DELETE/i), "DELETE");
    await userEvent.click(finalButton(dialog));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Couldn't delete budget.db");
    expect(onReset).not.toHaveBeenCalled();
  });

  it("closes on Cancel without deleting anything", async () => {
    const fetchMock = backend();
    render(<DeleteData />);
    const dialog = await openDialog();

    await userEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([url]) => url)).not.toContain("/api/database/reset");
  });
});
