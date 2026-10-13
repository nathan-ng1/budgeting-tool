import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import ChangeLocation from "./ChangeLocation.jsx";

// A stand-in backend: `choose` is the folder-picker answer, `apply` the move's.
function backend({ choose, apply }) {
  const fetchMock = vi.fn(async (url) => {
    const reply = url.endsWith("/choose-folder") ? choose : apply;
    return { ok: reply.ok ?? true, status: reply.status ?? 200, json: async () => reply.body };
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

const chosenEmptyFolder = {
  body: { cancelled: false, folder: "D:\\Budget", outcome: "move", target: "D:\\Budget\\budget.db" },
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ChangeLocation", () => {
  it("asks for confirmation, naming the folder, once an empty folder is chosen", async () => {
    backend({ choose: chosenEmptyFolder, apply: { body: {} } });
    render(<ChangeLocation onMoved={() => {}} />);

    await userEvent.click(screen.getByRole("button", { name: "Change location…" }));

    expect(await screen.findByText(/will be moved/i)).toBeInTheDocument();
    expect(screen.getByText("D:\\Budget")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Move the Database" })).toBeInTheDocument();
  });

  it("moves nothing until confirmed, then applies the chosen folder and reloads", async () => {
    const fetchMock = backend({ choose: chosenEmptyFolder, apply: { body: { path: "D:\\Budget\\budget.db" } } });
    const onMoved = vi.fn();
    render(<ChangeLocation onMoved={onMoved} />);

    await userEvent.click(screen.getByRole("button", { name: "Change location…" }));
    await screen.findByText(/will be moved/i);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(onMoved).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: "Move the Database" }));

    await vi.waitFor(() => expect(onMoved).toHaveBeenCalledTimes(1));
    const [url, options] = fetchMock.mock.calls[1];
    expect(url).toBe("/api/database/location");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ folder: "D:\\Budget" });
  });

  it("drops the confirmation on Cancel without applying anything", async () => {
    const fetchMock = backend({ choose: chosenEmptyFolder, apply: { body: {} } });
    render(<ChangeLocation onMoved={() => {}} />);

    await userEvent.click(screen.getByRole("button", { name: "Change location…" }));
    await userEvent.click(await screen.findByRole("button", { name: "Cancel" }));

    expect(screen.queryByText(/will be moved/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Change location…" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("shows nothing when the dialog is cancelled", async () => {
    const fetchMock = backend({ choose: { body: { cancelled: true } }, apply: { body: {} } });
    render(<ChangeLocation onMoved={() => {}} />);

    await userEvent.click(screen.getByRole("button", { name: "Change location…" }));

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByText(/will be moved/i)).not.toBeInTheDocument();
  });

  it("shows why when the folder picker can't open", async () => {
    backend({ choose: { ok: false, status: 500, body: { error: "No display" } }, apply: { body: {} } });
    render(<ChangeLocation onMoved={() => {}} />);

    await userEvent.click(screen.getByRole("button", { name: "Change location…" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("No display");
  });

  it("shows why and stays put when the move fails", async () => {
    const onMoved = vi.fn();
    backend({
      choose: chosenEmptyFolder,
      apply: { ok: false, status: 500, body: { error: "The copy of budget.db failed its integrity check" } },
    });
    render(<ChangeLocation onMoved={onMoved} />);

    await userEvent.click(screen.getByRole("button", { name: "Change location…" }));
    await userEvent.click(await screen.findByRole("button", { name: "Move the Database" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("integrity check");
    expect(onMoved).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Change location…" })).toBeInTheDocument();
  });

  it("explains a folder that already holds a Database or is the current one, without offering a move", async () => {
    backend({
      choose: { body: { cancelled: false, folder: "D:\\Old", outcome: "existing", target: "D:\\Old\\budget.db" } },
      apply: { body: {} },
    });
    render(<ChangeLocation onMoved={() => {}} />);

    await userEvent.click(screen.getByRole("button", { name: "Change location…" }));

    expect(await screen.findByText(/already holds a Database/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Move the Database" })).not.toBeInTheDocument();
  });
});
