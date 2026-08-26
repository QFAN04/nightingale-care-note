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

  it("switches the demo identity in the application header", () => {
    render(<Home />);

    const roleSwitcher = screen.getByLabelText("Demo role");
    expect(roleSwitcher).toHaveValue("clinician");
    fireEvent.change(roleSwitcher, { target: { value: "staff" } });

    expect(roleSwitcher).toHaveValue("staff");
    expect(screen.getByText("Staff view")).toBeInTheDocument();
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

  it("lets a clinician accept an AI suggestion and shows who reviewed it", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: "00000000-0000-0000-0000-000000000029",
        status: "accepted",
        reviewed_by: {
          id: "00000000-0000-0000-0000-000000000005",
          display_name: "Dr Priya Nair",
        },
        reviewed_at: "2026-08-26T05:00:00Z",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<Home />);

    const recent = screen.getByRole("region", { name: "Recent changes" });
    expect(within(recent).getByText(/AI suggestion/)).toBeInTheDocument();
    fireEvent.click(within(recent).getByRole("button", { name: "Accept" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/highlights/00000000-0000-0000-0000-000000000029/accept",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          "X-Demo-User-ID": "00000000-0000-0000-0000-000000000005",
        }),
      }),
    );
    await waitFor(() =>
      expect(within(recent).getByText(/Accepted by/)).toHaveTextContent(
        "Accepted by Dr Priya Nair",
      ),
    );
    expect(within(recent).queryByRole("button", { name: "Accept" })).not.toBeInTheDocument();
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
        headers: expect.objectContaining({
          "X-Demo-User-ID": "00000000-0000-0000-0000-000000000005",
        }),
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

  it("adds an @clinician comment to the staff note thread", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: "00000000-0000-0000-0000-000000000061",
        entry_id: "00000000-0000-0000-0000-00000000000d",
        content: "@clinician Reviewed during today's consultation.",
        mentioned_role: "clinician",
        author: {
          id: "00000000-0000-0000-0000-000000000005",
          display_name: "Dr Priya Nair",
        },
        resolved: false,
        resolved_by: null,
        resolved_at: null,
        created_at: "2026-08-26T06:00:00Z",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<Home />);

    const staffCard = screen.getByRole("heading", { name: "Follow-up escalated" }).closest("article");
    expect(staffCard).not.toBeNull();
    expect(within(staffCard!).getByText(/Please review the persistent chest pressure/)).toBeInTheDocument();
    fireEvent.change(within(staffCard!).getByLabelText("New comment"), {
      target: { value: "@clinician Reviewed during today's consultation." },
    });
    fireEvent.click(within(staffCard!).getByRole("button", { name: "Add comment" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/entries/00000000-0000-0000-0000-00000000000d/comments",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          "X-Demo-User-ID": "00000000-0000-0000-0000-000000000005",
        }),
        body: JSON.stringify({
          content: "@clinician Reviewed during today's consultation.",
        }),
      }),
    );
    expect(
      await within(staffCard!).findByText("@clinician Reviewed during today's consultation."),
    ).toBeInTheDocument();
  });

  it("resolves an open care-team comment", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: "00000000-0000-0000-0000-00000000003c",
        entry_id: "00000000-0000-0000-0000-00000000000d",
        content: "@clinician Please review the persistent chest pressure before today's consult.",
        mentioned_role: "clinician",
        author: {
          id: "00000000-0000-0000-0000-000000000004",
          display_name: "Amanda Wong",
        },
        resolved: true,
        resolved_by: {
          id: "00000000-0000-0000-0000-000000000005",
          display_name: "Dr Priya Nair",
        },
        resolved_at: "2026-08-26T06:10:00Z",
        created_at: "2026-08-24T09:05:00Z",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<Home />);

    const staffCard = screen.getByRole("heading", { name: "Follow-up escalated" }).closest("article");
    expect(staffCard).not.toBeNull();
    fireEvent.click(within(staffCard!).getByRole("button", { name: "Resolve comment" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/comments/00000000-0000-0000-0000-00000000003c/resolve",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          "X-Demo-User-ID": "00000000-0000-0000-0000-000000000005",
        }),
      }),
    );
    expect(await within(staffCard!).findByText("Resolved by Dr Priya Nair")).toBeInTheDocument();
    expect(within(staffCard!).queryByRole("button", { name: "Resolve comment" })).not.toBeInTheDocument();
  });
});
