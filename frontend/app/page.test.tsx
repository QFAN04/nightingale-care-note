import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "./page";

describe("Nightingale application shell", () => {
  it("identifies the product, care-note purpose, and active demo role", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", { level: 1, name: "Nightingale" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Longitudinal care, clearly understood."),
    ).toBeInTheDocument();
    expect(screen.getByText("Clinician view")).toBeInTheDocument();
  });
});
