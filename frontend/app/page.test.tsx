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

    await waitFor(() =>
      expect(
        fetchMock.mock.calls.filter(([, options]) => options?.method === "POST"),
      ).toHaveLength(1),
    );
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
    let scribeCompleted = false;
    const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
      if (options?.method === "POST") {
        scribeCompleted = true;
        return {
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
        };
      }
      if (url.endsWith("/glance")) {
        return {
          ok: true,
          json: async () => ({
            patient: {
              id: "00000000-0000-0000-0000-000000000002",
              external_ref: "PAT-001",
              display_name: "Sarah Lim",
            },
            generated_at: "2026-08-26T10:00:00Z",
            critical: [],
            recent_changes: scribeCompleted
              ? [
                  {
                    id: "00000000-0000-0000-0000-000000000041",
                    title: "New worsening chest pressure",
                    category: "recent_change",
                    status: "suggested",
                    risk_level: "high",
                    risk_reason: "New high-risk symptom requires review",
                    source: {
                      entry_id: "00000000-0000-0000-0000-000000000071",
                      entry_type: "ai_doctor_consult_summary",
                      occurred_at: "2026-08-26T10:00:00Z",
                      provenance_type: "llm",
                      provenance_id: "00000000-0000-0000-0000-000000000081",
                      source_quote: "chest pressure felt stronger",
                      source_start: 31,
                      source_end: 59,
                    },
                    details: {
                      entity_name: "chest pressure",
                      value_text: "worsening",
                      value_number: null,
                      unit: null,
                      fact_review_status: "suggested",
                      task_priority: null,
                      task_status: null,
                      authoritative_value: null,
                      conflicting_value: null,
                    },
                  },
                ]
              : [],
            open_actions: [],
            conflicts: [],
          }),
        };
      }
      return {
        ok: true,
        json: async () =>
          scribeCompleted
            ? [
                {
                  id: "00000000-0000-0000-0000-000000000071",
                  patient_id: "00000000-0000-0000-0000-000000000002",
                  author_id: "00000000-0000-0000-0000-000000000005",
                  author_role: "clinician",
                  entry_type: "ai_doctor_consult_summary",
                  content: "Patient reports newly worsening chest pressure.",
                  occurred_at: "2026-08-26T10:00:00Z",
                  provenance_type: "llm",
                  provenance_id: "00000000-0000-0000-0000-000000000081",
                  current_version: 1,
                },
              ]
            : [],
      };
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

    await waitFor(() =>
      expect(
        fetchMock.mock.calls.filter(([, options]) => options?.method === "POST"),
      ).toHaveLength(1),
    );
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
    expect(await screen.findByText("New worsening chest pressure")).toBeInTheDocument();
    expect(screen.getByText("Added to the top of the timeline")).toBeInTheDocument();
  });

  it.each([
    ["staff", "nurse_patient", "Nurse–patient consultation"],
    ["patient", "ai_patient", "AI–patient session"],
  ])(
    "uses the role-authorized scribe interaction for %s",
    async (role, interactionType, interactionLabel) => {
      const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
        if (options?.method === "POST") {
          return {
            ok: true,
            json: async () => ({ summary: "Summary", facts: [], tasks: [] }),
          };
        }
        if (url.endsWith("/glance")) {
          return {
            ok: true,
            json: async () => ({
              patient: {
                id: "00000000-0000-0000-0000-000000000002",
                external_ref: "PAT-001",
                display_name: "Sarah Lim",
              },
              generated_at: "2026-08-26T10:00:00Z",
              critical: [],
              recent_changes: [],
              open_actions: [],
              conflicts: [],
            }),
          };
        }
        return { ok: true, json: async () => [] };
      });
      vi.stubGlobal("fetch", fetchMock);
      render(<Home />);

      fireEvent.change(screen.getByLabelText("Demo role"), {
        target: { value: role },
      });
      fireEvent.click(screen.getByRole("button", { name: "New AI Scribe" }));

      expect(screen.getByLabelText("Interaction type")).toHaveValue(interactionType);
      expect(screen.getByLabelText("Interaction type")).toBeDisabled();
      expect(screen.getByText(interactionLabel)).toBeInTheDocument();
      fireEvent.change(screen.getByLabelText("Transcript"), {
        target: { value: "Synthetic conversation" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Generate" }));

      await waitFor(() =>
        expect(fetchMock).toHaveBeenCalledWith(
          expect.stringMatching(/\/api\/v1\/patients\/.*\/scribe$/),
          expect.objectContaining({
            body: JSON.stringify({
              interaction_type: interactionType,
              raw_text: "Synthetic conversation",
            }),
          }),
        ),
      );
    },
  );

  it("hides AI Scribe from the admin role", () => {
    render(<Home />);

    fireEvent.change(screen.getByLabelText("Demo role"), {
      target: { value: "admin" },
    });

    expect(screen.queryByRole("button", { name: "New AI Scribe" })).not.toBeInTheDocument();
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

    await waitFor(() =>
      expect(
        fetchMock.mock.calls.filter(([, options]) => options?.method === "POST"),
      ).toHaveLength(1),
    );
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

    await waitFor(() =>
      expect(
        fetchMock.mock.calls.filter(([, options]) => options?.method === "POST"),
      ).toHaveLength(1),
    );
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

  it("lets a clinician resolve a medication conflict with a resolution note", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: "00000000-0000-0000-0000-000000000033",
        status: "resolved",
        resolution_note: "Medication dose verified as 20 mg.",
        resolved_by: {
          id: "00000000-0000-0000-0000-000000000005",
          display_name: "Dr Priya Nair",
        },
        resolved_at: "2026-08-26T06:30:00Z",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<Home />);

    const conflicts = screen.getByRole("region", { name: "Conflicts" });
    fireEvent.change(
      within(conflicts).getByLabelText(
        "Resolution note for Atorvastatin dose discrepancy",
      ),
      { target: { value: "Medication dose verified as 20 mg." } },
    );
    fireEvent.click(within(conflicts).getByRole("button", { name: "Resolve conflict" }));

    await waitFor(() =>
      expect(
        fetchMock.mock.calls.filter(([, options]) => options?.method === "POST"),
      ).toHaveLength(1),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/conflicts/00000000-0000-0000-0000-000000000033/resolve",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          "X-Demo-User-ID": "00000000-0000-0000-0000-000000000005",
        }),
        body: JSON.stringify({
          resolution_note: "Medication dose verified as 20 mg.",
        }),
      }),
    );
    await waitFor(() =>
      expect(
        within(conflicts).queryByText("Atorvastatin dose discrepancy"),
      ).not.toBeInTheDocument(),
    );
  });

  it("reloads role-scoped APIs and removes internal context for the patient", async () => {
    const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
      const userId = (options?.headers as Record<string, string> | undefined)?.[
        "X-Demo-User-ID"
      ];
      const isPatient = userId === "00000000-0000-0000-0000-000000000003";
      if (url.endsWith("/glance")) {
        return {
          ok: true,
          json: async () => ({
            patient: {
              id: "00000000-0000-0000-0000-000000000002",
              external_ref: "PAT-001",
              display_name: "Sarah Lim",
            },
            generated_at: "2026-08-26T10:00:00Z",
            critical: [],
            recent_changes: isPatient
              ? []
              : [
                  {
                    id: "00000000-0000-0000-0000-000000000041",
                    title: "Internal clinician suggestion",
                    category: "recent_change",
                    status: "suggested",
                    risk_level: "high",
                    risk_reason: "Internal review required",
                    source: {
                      entry_id: "00000000-0000-0000-0000-000000000013",
                      entry_type: "staff_note",
                      occurred_at: "2026-08-24T09:00:00Z",
                      provenance_type: "manual",
                      provenance_id: null,
                      source_quote: "Escalated to the clinician for review.",
                      source_start: null,
                      source_end: null,
                    },
                    details: {
                      entity_name: "chest pressure",
                      value_text: "persistent",
                      value_number: null,
                      unit: null,
                      fact_review_status: "suggested",
                      task_priority: null,
                      task_status: null,
                      authoritative_value: null,
                      conflicting_value: null,
                    },
                  },
                ],
            open_actions: [],
            conflicts: [],
          }),
        };
      }
      return {
        ok: true,
        json: async () =>
          isPatient
            ? []
            : [
                {
                  id: "00000000-0000-0000-0000-000000000013",
                  patient_id: "00000000-0000-0000-0000-000000000002",
                  author_id: "00000000-0000-0000-0000-000000000004",
                  author_role: "staff",
                  entry_type: "staff_note",
                  content: "Internal staff escalation.",
                  occurred_at: "2026-08-24T09:00:00Z",
                  provenance_type: "manual",
                  provenance_id: null,
                  current_version: 1,
                },
              ],
      };
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<Home />);

    expect(await screen.findByText("Internal clinician suggestion")).toBeInTheDocument();
    expect(screen.getByText("Internal staff escalation.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Demo role"), {
      target: { value: "patient" },
    });

    await waitFor(() =>
      expect(screen.queryByText("Internal clinician suggestion")).not.toBeInTheDocument(),
    );
    expect(screen.queryByText("Internal staff escalation.")).not.toBeInTheDocument();
    expect(screen.getByText("No timeline entries visible for this role.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/timeline$/),
      expect.objectContaining({
        headers: {
          "X-Demo-User-ID": "00000000-0000-0000-0000-000000000003",
        },
      }),
    );
  });
});
