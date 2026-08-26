import {
  sarahTimeline,
  type GlanceItem,
  type GlanceSection,
  type TimelineItem,
} from "./demo-data";


type ApiGlanceSource = {
  entry_id: string;
  entry_type: string;
  occurred_at: string;
  provenance_type: string;
  provenance_id: string | null;
  source_quote: string;
  source_start: number | null;
  source_end: number | null;
};

type ApiGlanceDetails = {
  entity_name: string | null;
  value_text: string | null;
  value_number: number | null;
  unit: string | null;
  fact_review_status: string | null;
  task_priority: string | null;
  task_status: string | null;
  authoritative_value: string | null;
  conflicting_value: string | null;
};

type ApiGlanceItem = {
  id: string;
  title: string;
  category: string;
  status: string;
  risk_level: string;
  risk_reason: string;
  source: ApiGlanceSource;
  details: ApiGlanceDetails;
};

type ApiCareState = {
  patient: { id: string; external_ref: string; display_name: string };
  generated_at: string;
  critical: ApiGlanceItem[];
  recent_changes: ApiGlanceItem[];
  open_actions: ApiGlanceItem[];
  conflicts: ApiGlanceItem[];
};

type ApiTimelineEntry = {
  id: string;
  patient_id: string;
  author_id: string | null;
  author_role: string;
  entry_type: string;
  content: string;
  occurred_at: string;
  provenance_type: string;
  provenance_id: string | null;
  current_version: number;
};

export type CareWorkspaceData = {
  sections: GlanceSection[];
  timeline: TimelineItem[];
};


export async function fetchCareWorkspace(
  patientId: string,
  userId: string,
): Promise<CareWorkspaceData> {
  const headers = { "X-Demo-User-ID": userId };
  const [careState, timeline] = await Promise.all([
    getJson<ApiCareState>(`/api/v1/patients/${patientId}/glance`, headers),
    getJson<ApiTimelineEntry[]>(`/api/v1/patients/${patientId}/timeline`, headers),
  ]);

  const sections = mapCareState(careState);
  const evidenceByEntry = new Map<string, string>();
  for (const item of [
    ...careState.critical,
    ...careState.recent_changes,
    ...careState.open_actions,
    ...careState.conflicts,
  ]) {
    if (!evidenceByEntry.has(item.source.entry_id)) {
      evidenceByEntry.set(item.source.entry_id, item.source.source_quote);
    }
  }
  return {
    sections,
    timeline: timeline.map((entry) => mapTimelineEntry(entry, evidenceByEntry)),
  };
}


async function getJson<T>(url: string, headers: Record<string, string>): Promise<T> {
  const response = await fetch(url, { headers });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? "The patient record could not be loaded.");
  }
  return (await response.json()) as T;
}


function mapCareState(state: ApiCareState): GlanceSection[] {
  return [
    section("critical", "Critical", "Persistent safety context", state.critical),
    section("recent", "Recent changes", "Needs clinical review", state.recent_changes),
    section("actions", "Open actions", "Prioritised follow-up", state.open_actions),
    section("conflicts", "Conflicts", "Reconciliation required", state.conflicts),
  ];
}


function section(
  id: GlanceSection["id"],
  title: string,
  eyebrow: string,
  items: ApiGlanceItem[],
): GlanceSection {
  return { id, title, eyebrow, items: items.map(mapGlanceItem) };
}


function mapGlanceItem(item: ApiGlanceItem): GlanceItem {
  const details = Array.from(
    new Set(
      [
        item.details.entity_name ? `Entity: ${item.details.entity_name}` : null,
        item.details.value_text ? `Value: ${item.details.value_text}` : null,
        item.details.value_number !== null
          ? `Value: ${item.details.value_number}${item.details.unit ? ` ${item.details.unit}` : ""}`
          : null,
        item.details.fact_review_status
          ? `Review: ${item.details.fact_review_status}`
          : null,
        item.details.task_priority ? `Priority: ${item.details.task_priority}` : null,
        item.details.task_status ? `Status: ${item.details.task_status}` : null,
        item.details.authoritative_value
          ? `Confirmed record: ${item.details.authoritative_value}`
          : null,
        item.details.conflicting_value
          ? `Reported: ${item.details.conflicting_value}`
          : null,
        `Risk: ${item.risk_level}`,
      ].filter((value): value is string => value !== null),
    ),
  );

  return {
    id: item.id,
    title: item.title,
    status: titleCase(item.status),
    riskReason: item.risk_reason,
    evidence: item.source.source_quote,
    details,
    sourceId: `entry-${item.source.entry_id}`,
    reviewable: item.status === "suggested",
  };
}


function mapTimelineEntry(
  entry: ApiTimelineEntry,
  evidenceByEntry: Map<string, string>,
): TimelineItem {
  const occurredAt = new Date(entry.occurred_at);
  const staticItem = sarahTimeline.find((item) => item.apiId === entry.id);
  return {
    id: `entry-${entry.id}`,
    apiId: entry.id,
    date: occurredAt.toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }),
    time: occurredAt.toLocaleTimeString("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
    }),
    label: labelFor(entry.entry_type),
    title: titleFor(entry.entry_type),
    content: entry.content,
    author: authorFor(entry.author_role, entry.entry_type),
    tone: toneFor(entry.entry_type),
    review: entry.entry_type.startsWith("ai_") ? "Pending review" : undefined,
    sourceEvidence: evidenceByEntry.get(entry.id),
    comments: staticItem?.comments,
  };
}


function labelFor(entryType: string): string {
  return {
    clinician_note: "Clinician note",
    staff_note: "Staff note",
    ai_patient_session_summary: "AI patient session",
    ai_doctor_consult_summary: "AI doctor consult summary",
    patient_instruction: "Patient instruction",
  }[entryType] ?? "Care note";
}


function titleFor(entryType: string): string {
  return {
    clinician_note: "Clinical context",
    staff_note: "Care team follow-up",
    ai_patient_session_summary: "AI patient session summary",
    ai_doctor_consult_summary: "AI consultation summary",
    patient_instruction: "Care instruction",
  }[entryType] ?? "Timeline entry";
}


function authorFor(authorRole: string, entryType: string): string {
  if (entryType.startsWith("ai_")) return "AI scribed from consultation";
  return titleCase(authorRole);
}


function toneFor(entryType: string): TimelineItem["tone"] {
  if (entryType === "staff_note") return "staff";
  if (entryType === "ai_patient_session_summary") return "ai-patient";
  if (entryType === "ai_doctor_consult_summary") return "ai-clinician";
  return "clinician";
}


function titleCase(value: string): string {
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
