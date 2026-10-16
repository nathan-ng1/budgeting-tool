import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import UpdateBanner from "./UpdateBanner.jsx";

describe("UpdateBanner", () => {
  it("names the new Version and says to re-run the installer", () => {
    render(<UpdateBanner version="1.4.0" />);

    const banner = screen.getByRole("status", { name: "Update available" });
    expect(banner).toHaveTextContent("Version 1.4.0 is available");
    expect(banner).toHaveTextContent("re-run the installer");
  });

  it("is absent when there is no update", () => {
    render(<UpdateBanner version={null} />);

    expect(screen.queryByRole("status", { name: "Update available" })).not.toBeInTheDocument();
  });
});
