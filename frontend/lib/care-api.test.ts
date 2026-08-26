import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchCareWorkspace } from "./care-api";


describe("role-aware care workspace API", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads Glance and Timeline with the same demo identity and maps provenance", async () => {
    const fetchMock = vi.fn(async (url: string) => {
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
            recent_changes: [
              {
                id: "00000000-0000-0000-0000-000000000041",
                title: "Worsening chest pressure",
                category: "recent_change",
                status: "suggested",
                risk_level: "high",
                risk_reason: "High-risk symptom needs review",
                source: {
                  entry_id: "00000000-0000-0000-0000-000000000012",
                  entry_type: "ai_patient_session_summary",
                  occurred_at: "2026-08-23T20:15:00Z",
                  provenance_type: "consult_session",
                  provenance_id: "00000000-0000-0000-0000-000000000020",
                  source_quote: "chest pressure felt stronger",
                  source_start: 10,
                  source_end: 38,
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
            ],
            open_actions: [],
            conflicts: [],
          }),
        };
      }
      return {
        ok: true,
        json: async () => [
          {
            id: "00000000-0000-0000-0000-000000000012",
            patient_id: "00000000-0000-0000-0000-000000000002",
            author_id: null,
            author_role: "system",
            entry_type: "ai_patient_session_summary",
            content: "Patient reports worsening chest pressure.",
            occurred_at: "2026-08-23T20:15:00Z",
            provenance_type: "consult_session",
            provenance_id: "00000000-0000-0000-0000-000000000020",
            current_version: 1,
          },
        ],
      };
    });
    vi.stubGlobal("fetch", fetchMock);

    const workspace = await fetchCareWorkspace(
      "00000000-0000-0000-0000-000000000002",
      "00000000-0000-0000-0000-000000000005",
    );

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/glance$/),
      expect.objectContaining({
        headers: {
          "X-Demo-User-ID": "00000000-0000-0000-0000-000000000005",
        },
      }),
    );
    expect(workspace.sections[1].items[0]).toMatchObject({
      id: "00000000-0000-0000-0000-000000000041",
      reviewable: true,
      sourceId: "entry-00000000-0000-0000-0000-000000000012",
      evidence: "chest pressure felt stronger",
    });
    expect(workspace.timeline[0]).toMatchObject({
      id: "entry-00000000-0000-0000-0000-000000000012",
      sourceEvidence: "chest pressure felt stronger",
      review: "Pending review",
    });
  });

  it("rejects a partial workspace response instead of mixing role scopes", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce({ ok: true, json: async () => ({ critical: [] }) })
        .mockResolvedValueOnce({ ok: false, json: async () => ({ detail: "Patient not found" }) }),
    );

    await expect(
      fetchCareWorkspace("patient-id", "other-clinic-user"),
    ).rejects.toThrow("Patient not found");
  });
});
