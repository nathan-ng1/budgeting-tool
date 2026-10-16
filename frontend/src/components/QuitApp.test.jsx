import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import QuitApp from "./QuitApp.jsx";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("QuitApp", () => {
  it("quits through the backend and says the app has stopped", async () => {
    const fetchMock = vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ quitting: true }) }));
    vi.stubGlobal("fetch", fetchMock);
    render(<QuitApp active />);

    await userEvent.click(screen.getByRole("button", { name: "Quit" }));

    expect(await screen.findByText("The app has stopped. You can close this tab.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/quit", { method: "POST" });
    expect(screen.queryByRole("button", { name: "Quit" })).not.toBeInTheDocument();
  });

  it("says so and lets the user try again when the quit fails", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 500, json: async () => ({}) })));
    render(<QuitApp active />);

    await userEvent.click(screen.getByRole("button", { name: "Quit" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("500");
    expect(screen.getByRole("button", { name: "Quit" })).toBeEnabled();
  });

  it("is absent when the launcher is not running the Dashboard", () => {
    const { container } = render(<QuitApp active={false} />);

    expect(container).toBeEmptyDOMElement();
  });
});
