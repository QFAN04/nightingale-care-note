export type TimelineItem = {
  id: string;
  date: string;
  time: string;
  label: string;
  title: string;
  content: string;
  author: string;
  tone: "clinician" | "staff" | "ai-patient" | "ai-clinician";
  review?: "Confirmed" | "Pending review";
  sourceId?: string;
};

export const sarahLim = {
  externalRef: "PAT-001",
  name: "Sarah Lim",
  detail: "Female · 42 years",
  clinic: "Nightingale Central Clinic",
};

export const sarahTimeline: TimelineItem[] = [
  {
    id: "entry-aug-25",
    date: "25 Aug 2026",
    time: "09:30",
    label: "AI doctor consult summary",
    title: "Medication dose discrepancy",
    content:
      "Chest pressure remains present but is less intense than last night. Sarah reported Atorvastatin 10 mg, while the clinician-confirmed record states 20 mg. Medication reconciliation is required.",
    author: "AI scribed from Dr Priya Nair consultation",
    tone: "ai-clinician",
    review: "Pending review",
    sourceId: "consult-aug-25",
  },
  {
    id: "entry-aug-24",
    date: "24 Aug 2026",
    time: "09:00",
    label: "Staff note",
    title: "Follow-up escalated",
    content:
      "Chest pressure remains present after the patient AI session. Escalated to the clinician for review before today's consultation.",
    author: "Amanda Wong · Staff",
    tone: "staff",
  },
  {
    id: "entry-aug-23",
    date: "23 Aug 2026",
    time: "20:15",
    label: "AI patient session",
    title: "Worsening chest pressure",
    content:
      "Patient reports worsening chest pressure, newly present for three days and stronger last night. This is an AI-extracted report pending clinician review.",
    author: "AI scribed from patient session",
    tone: "ai-patient",
    review: "Pending review",
    sourceId: "session-aug-23",
  },
  {
    id: "entry-jul-12",
    date: "12 Jul 2026",
    time: "11:00",
    label: "Staff note",
    title: "Routine telephone follow-up",
    content:
      "Sarah reported no chest pain or chest pressure and no new medication concerns.",
    author: "Amanda Wong · Staff",
    tone: "staff",
  },
  {
    id: "entry-apr-15",
    date: "15 Apr 2026",
    time: "09:00",
    label: "Clinician note",
    title: "Medication and allergy context",
    content:
      "Penicillin allergy confirmed; previous reaction was urticaria. Atorvastatin 20 mg once daily remains the clinician-confirmed medication dose.",
    author: "Dr Priya Nair · Clinician",
    tone: "clinician",
    review: "Confirmed",
  },
];
