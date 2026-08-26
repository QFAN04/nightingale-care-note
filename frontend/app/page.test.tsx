import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import Home from "./page";

describe("Nightingale application shell", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

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
    expect(screen.getAllByText("Worsening chest pressure")).not.toHaveLength(0);
    expect(screen.getAllByText(/Penicillin allergy confirmed/)).not.toHaveLength(0);
    expect(screen.getAllByRole("link", { name: "View source" })).not.toHaveLength(0);
  });

  it("renders the explainable four-section Care Glance with source jumps", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", { level: 3, name: "Care Glance" }),
    ).toBeInTheDocument();

    const critical = screen.getByRole("region", { name: "Critical" });
    const recent = screen.getByRole("region", { name: "Recent changes" });
    const actions = screen.getByRole("region", { name: "Open actions" });
    const conflicts = screen.getByRole("region", { name: "Conflicts" });

    expect(within(critical).getByText("Penicillin allergy")).toBeInTheDocument();
    expect(within(recent).getByText("Worsening chest pressure")).toBeInTheDocument();
    expect(within(actions).getByText(/Clinician to review/)).toBeInTheDocument();
    expect(within(conflicts).getByText("Atorvastatin dose discrepancy")).toBeInTheDocument();

    const evidenceToggle = within(critical).getByText("Evidence & details");
    fireEvent.click(evidenceToggle);
    expect(evidenceToggle.closest("details")).toHaveAttribute("open");
    expect(
      within(critical).getByText(/previous reaction was urticaria/),
    ).toBeInTheDocument();
    expect(within(critical).getByRole("link", { name: "Jump to source" })).toHaveAttribute(
      "href",
      "#entry-apr-15",
    );
    expect(document.body.textContent).not.toMatch(/base_score|learned_score|final_score/i);
  });

  it("lands on the timeline entry that marks the exact source quote", () => {
    render(<Home />);

    const recent = screen.getByRole("region", { name: "Recent changes" });
    const sourceLink = within(recent).getByRole("link", { name: "Jump to source" });
    expect(sourceLink).toHaveAttribute("href", "#entry-aug-23");

    const target = document.querySelector<HTMLElement>("#entry-aug-23");
    expect(target).not.toBeNull();
    expect(within(target!).getByText("Source evidence")).toBeInTheDocument();
    expect(target!.querySelector("mark")).toHaveTextContent(
      "Last night the chest pressure felt stronger than before.",
    );
  });

  it("runs the frozen AI scribe modal and refreshes the timeline", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        summary: "Patient reports newly worsening chest pressure.",
        facts: [
          {
            fact_type: "symptom",
            entity_name: "chest pressure",
            value_text: "worsening",
            value_number: null,
            unit: null,
            risk_hint: "high",
            persistence_hint: "transient",
            source_quote: "chest pressure felt stronger",
            extraction_confidence: 0.96,
          },
        ],
        tasks: [],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<Home />);

    fireEvent.click(screen.getByRole("button", { name: "New AI Scribe" }));
    expect(screen.getByRole("dialog", { name: "New AI Scribe" })).toBeInTheDocument();
    expect(screen.getByLabelText("Interaction type")).toHaveValue("doctor_patient");

    fireEvent.change(screen.getByLabelText("Transcript"), {
      target: { value: "Doctor: How are you? Patient: chest pressure felt stronger" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Generate" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/v1\/patients\/.*\/scribe$/),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          interaction_type: "doctor_patient",
          raw_text: "Doctor: How are you? Patient: chest pressure felt stronger",
        }),
      }),
    );
    expect(await screen.findByText("PHI redacted")).toBeInTheDocument();
    expect(screen.getAllByText("Patient reports newly worsening chest pressure.")).toHaveLength(2);
    expect(screen.getByText("chest pressure")).toBeInTheDocument();
    expect(screen.getByText("Added to the top of the timeline")).toBeInTheDocument();
  });
});
