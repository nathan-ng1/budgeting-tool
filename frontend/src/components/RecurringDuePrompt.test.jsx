import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import RecurringDuePrompt from "./RecurringDuePrompt.jsx";

let fetchMock;

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body };
}

/** Answers the due count with `due`, and the run with `written`. */
function backend({ due, written = due }) {
  fetchMock.mockImplementation(async (url, options = {}) => {
    if (url === "/api/recurring-rules/due") {
      return json({ due });
    }
    if (url === "/api/recurring-rules/run" && options.method === "POST") {
      return json({ written });
    }
    throw new Error(`Unexpected request to ${url}`);
  });
}

function runCalls() {
  return fetchMock.mock.calls.filter(([url]) => url === "/api/recurring-rules/run");
}

describe("RecurringDuePrompt", () => {
  it("offers to run the due recurring transactions, saying how many", async () => {
    backend({ due: 3 });
    render(<RecurringDuePrompt />);

    expect(await screen.findByText("3 recurring transactions are due.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run now" })).toBeEnabled();
  });

  it("uses the singular for exactly one", async () => {
    backend({ due: 1 });
    render(<RecurringDuePrompt />);

    expect(await screen.findByText("1 recurring transaction is due.")).toBeInTheDocument();
  });

  it("shows nothing when none are due", async () => {
    backend({ due: 0 });
    const { container } = render(<RecurringDuePrompt />);

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/recurring-rules/due", expect.anything()));
    expect(container).toBeEmptyDOMElement();
  });

  it("shows nothing when the count can't be read", async () => {
    fetchMock.mockResolvedValue(json({ error: "boom" }, 500));
    const { container } = render(<RecurringDuePrompt />);

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("writes nothing until the user clicks", async () => {
    backend({ due: 2 });
    render(<RecurringDuePrompt />);
    await screen.findByText("2 recurring transactions are due.");

    expect(runCalls()).toHaveLength(0);
  });

  it("runs on click, then clears the prompt and tells the caller", async () => {
    backend({ due: 2 });
    const onRun = vi.fn();
    render(<RecurringDuePrompt onRun={onRun} />);

    await userEvent.click(await screen.findByRole("button", { name: "Run now" }));

    expect(runCalls()).toHaveLength(1);
    expect(await screen.findByRole("status")).toHaveTextContent("2 transactions added.");
    expect(screen.queryByRole("button", { name: "Run now" })).not.toBeInTheDocument();
    expect(onRun).toHaveBeenCalledWith(2);
  });

  it("keeps the prompt and shows the error when the run fails", async () => {
    fetchMock.mockImplementation(async (url) =>
      url === "/api/recurring-rules/due" ? json({ due: 2 }) : json({ error: "Disk is full" }, 500),
    );
    const onRun = vi.fn();
    render(<RecurringDuePrompt onRun={onRun} />);

    await userEvent.click(await screen.findByRole("button", { name: "Run now" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Disk is full");
    expect(screen.getByRole("button", { name: "Run now" })).toBeEnabled();
    expect(onRun).not.toHaveBeenCalled();
  });
});
