export type ScribeFact = {
  fact_type: string;
  entity_name: string;
  value_text: string | null;
  value_number: number | null;
  unit: string | null;
  risk_hint: "low" | "medium" | "high" | "critical";
  persistence_hint: "transient" | "persistent";
  source_quote: string;
  extraction_confidence: number;
};

export type ScribeResult = {
  summary: string;
  facts: ScribeFact[];
  tasks: Array<{
    description: string;
    priority: "low" | "medium" | "high";
    source_quote: string;
  }>;
};

export async function runScribe(
  patientId: string,
  interactionType: "doctor_patient",
  rawText: string,
  currentUserId: string,
): Promise<ScribeResult> {
  const response = await fetch(`/api/v1/patients/${patientId}/scribe`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Demo-User-ID": currentUserId,
    },
    body: JSON.stringify({ interaction_type: interactionType, raw_text: rawText }),
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? "AI Scribe could not complete this consultation.");
  }
  return (await response.json()) as ScribeResult;
}
