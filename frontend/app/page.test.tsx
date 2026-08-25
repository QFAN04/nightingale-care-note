import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "./page";

describe("Nightingale application shell", () => {
  it("renders Sarah Lim's role-aware longitudinal care note", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", { level: 1, name: "Nightingale" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Longitudinal care, clearly understood."),
    ).toBeInTheDocument();
    expect(screen.getByText("Clinician view")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: "Sarah Lim" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 3, name: "Longitudinal timeline" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Worsening chest pressure")).toBeInTheDocument();
    expect(screen.getByText(/Penicillin allergy confirmed/)).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "View source" })).not.toHaveLength(0);
  });
});
