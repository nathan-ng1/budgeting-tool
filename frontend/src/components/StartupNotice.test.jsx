import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import StartupNotice from "./StartupNotice.jsx";

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  localStorage.clear();
});

describe("StartupNotice", () => {
  it("explains background running, Quit and opening from the icon", () => {
    render(<StartupNotice active />);

    const notice = screen.getByRole("region", { name: "Before you start" });
    expect(notice).toHaveTextContent("keeps running in the background");
    expect(notice).toHaveTextContent("Quit");
    expect(notice).toHaveTextContent("icon rather than a bookmark");
  });

  it("can be dismissed, and stays dismissed on the next visit", async () => {
    const { unmount } = render(<StartupNotice active />);

    await userEvent.click(screen.getByRole("button", { name: "Got it" }));
    expect(screen.queryByRole("region", { name: "Before you start" })).not.toBeInTheDocument();

    unmount();
    render(<StartupNotice active />);
    expect(screen.queryByRole("region", { name: "Before you start" })).not.toBeInTheDocument();
  });

  it("is not shown when the launcher is not running the Dashboard", () => {
    render(<StartupNotice active={false} />);

    expect(screen.queryByRole("region", { name: "Before you start" })).not.toBeInTheDocument();
  });
});
