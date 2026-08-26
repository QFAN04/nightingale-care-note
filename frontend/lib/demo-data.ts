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
  sourceEvidence?: string;
};

export type GlanceItem = {
  id: string;
  title: string;
  status: string;
  riskReason: string;
  evidence: string;
  details: string[];
  sourceId: string;
  reviewable?: boolean;
  acceptedBy?: string;
};

export type GlanceSection = {
  id: "critical" | "recent" | "actions" | "conflicts";
  title: string;
  eyebrow: string;
  items: GlanceItem[];
};

export const sarahLim = {
  externalRef: "PAT-001",
  name: "Sarah Lim",
  detail: "Female · 42 years",
  clinic: "Nightingale Central Clinic",
};

export const sarahGlance: GlanceSection[] = [
  {
    id: "critical",
    title: "Critical",
    eyebrow: "Persistent safety context",
    items: [
      {
        id: "glance-allergy",
        title: "Penicillin allergy",
        status: "Accepted",
        riskReason: "Clinician-confirmed critical allergy with persistent safety relevance.",
        evidence: "Penicillin allergy confirmed; previous reaction was urticaria.",
        details: ["Reaction: urticaria", "Review: confirmed"],
        sourceId: "entry-apr-15",
      },
    ],
  },
  {
    id: "recent",
    title: "Recent changes",
    eyebrow: "Needs clinical review",
    items: [
      {
        id: "00000000-0000-0000-0000-000000000029",
        title: "Worsening chest pressure",
        status: "Suggested",
        riskReason: "High-risk symptom reported recently; clinical follow-up remains unresolved.",
        evidence: "Last night the chest pressure felt stronger than before.",
        details: ["Risk: high", "Review: pending"],
        sourceId: "entry-aug-23",
        reviewable: true,
      },
    ],
  },
  {
    id: "actions",
    title: "Open actions",
    eyebrow: "Prioritised follow-up",
    items: [
      {
        id: "glance-review-task",
        title: "Clinician to review persistent chest pressure and document next steps",
        status: "High priority",
        riskReason: "Open high-priority action assigned for clinician follow-up.",
        evidence: "Chest pressure remains present. Escalated to the clinician for review.",
        details: ["Assigned: clinician", "Status: open"],
        sourceId: "entry-aug-24",
      },
    ],
  },
  {
    id: "conflicts",
    title: "Conflicts",
    eyebrow: "Reconciliation required",
    items: [
      {
        id: "glance-dose-conflict",
        title: "Atorvastatin dose discrepancy",
        status: "Detected",
        riskReason: "Patient-reported dose conflicts with the clinician-confirmed record.",
        evidence: "I thought I was taking Atorvastatin 10 mg.",
        details: ["Confirmed record: 20 mg once daily", "Reported: 10 mg"],
        sourceId: "entry-aug-25",
      },
    ],
  },
];

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
    sourceEvidence: "I thought I was taking Atorvastatin 10 mg.",
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
    sourceEvidence:
      "Chest pressure remains present after the patient AI session. Escalated to the clinician for review before today's consultation.",
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
    sourceEvidence: "Last night the chest pressure felt stronger than before.",
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
    sourceEvidence: "Penicillin allergy confirmed; previous reaction was urticaria.",
  },
];
