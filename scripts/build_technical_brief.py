"""Build the three-page Nightingale technical brief PDF."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "nightingale-technical-brief.pdf"
PAGE_W, PAGE_H = A4

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#2F6F91")
TEAL = colors.HexColor("#2D8C87")
PALE = colors.HexColor("#EDF5F6")
ICE = colors.HexColor("#F5F8FA")
INK = colors.HexColor("#253443")
MUTED = colors.HexColor("#66788A")
LINE = colors.HexColor("#D6E0E6")
WHITE = colors.white
AMBER = colors.HexColor("#D99B2B")
RED = colors.HexColor("#B94B55")


BODY = ParagraphStyle(
    "Body",
    fontName="Helvetica",
    fontSize=8.6,
    leading=12,
    textColor=INK,
    alignment=TA_LEFT,
)
SMALL = ParagraphStyle(
    "Small",
    parent=BODY,
    fontSize=7.4,
    leading=9.8,
    textColor=MUTED,
)
CENTER = ParagraphStyle(
    "Center",
    parent=BODY,
    alignment=TA_CENTER,
    fontSize=7.8,
    leading=10,
)


def paragraph(
    canvas: Canvas,
    text: str,
    x: float,
    y_top: float,
    width: float,
    height: float,
    style: ParagraphStyle = BODY,
) -> float:
    item = Paragraph(text, style)
    used_w, used_h = item.wrap(width, height)
    item.drawOn(canvas, x, y_top - used_h)
    return used_h


def header(canvas: Canvas, page: int, kicker: str, title: str, subtitle: str) -> None:
    canvas.setFillColor(NAVY)
    canvas.rect(0, PAGE_H - 94, PAGE_W, 94, stroke=0, fill=1)
    canvas.setFillColor(colors.HexColor("#75D0C9"))
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(42, PAGE_H - 29, kicker.upper())
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 23)
    canvas.drawString(42, PAGE_H - 57, title)
    canvas.setFont("Helvetica", 8.5)
    canvas.setFillColor(colors.HexColor("#D9E8EF"))
    canvas.drawString(42, PAGE_H - 76, subtitle)
    canvas.setFillColor(colors.HexColor("#D9E8EF"))
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(PAGE_W - 42, PAGE_H - 29, f"TECHNICAL BRIEF  |  {page}/3")


def footer(canvas: Canvas) -> None:
    canvas.setStrokeColor(LINE)
    canvas.line(42, 34, PAGE_W - 42, 34)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 6.8)
    canvas.drawString(42, 22, "Nightingale Care Note - synthetic-data prototype - 26 Aug 2026")
    canvas.drawRightString(PAGE_W - 42, 22, "Not for clinical diagnosis or treatment")


def section_label(canvas: Canvas, text: str, x: float, y: float) -> None:
    canvas.setFillColor(BLUE)
    canvas.setFont("Helvetica-Bold", 8.2)
    canvas.drawString(x, y, text.upper())


def card(
    canvas: Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    body: str,
    *,
    accent=TEAL,
    fill=ICE,
    body_style: ParagraphStyle = BODY,
) -> None:
    canvas.setFillColor(fill)
    canvas.setStrokeColor(LINE)
    canvas.roundRect(x, y, width, height, 8, stroke=1, fill=1)
    canvas.setFillColor(accent)
    canvas.roundRect(x, y + height - 6, width, 6, 4, stroke=0, fill=1)
    canvas.setFillColor(NAVY)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(x + 12, y + height - 24, title)
    paragraph(canvas, body, x + 12, y + height - 34, width - 24, height - 44, body_style)


def arrow(canvas: Canvas, x1: float, y1: float, x2: float, y2: float) -> None:
    canvas.setStrokeColor(colors.HexColor("#9CB2C0"))
    canvas.setFillColor(colors.HexColor("#9CB2C0"))
    canvas.setLineWidth(1.3)
    canvas.line(x1, y1, x2, y2)
    canvas.line(x2, y2, x2 - 5, y2 + 3)
    canvas.line(x2, y2, x2 - 5, y2 - 3)


def flow_box(
    canvas: Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    detail: str,
    color,
) -> None:
    canvas.setFillColor(WHITE)
    canvas.setStrokeColor(color)
    canvas.setLineWidth(1.3)
    canvas.roundRect(x, y, width, height, 7, stroke=1, fill=1)
    canvas.setFillColor(color)
    canvas.setFont("Helvetica-Bold", 8.4)
    canvas.drawCentredString(x + width / 2, y + height - 17, title)
    paragraph(canvas, detail, x + 6, y + height - 24, width - 12, height - 28, CENTER)


def page_one(canvas: Canvas) -> None:
    header(
        canvas,
        1,
        "Problem / Product principle / Architecture",
        "Longitudinal care, without losing trust",
        "A local-first workflow that keeps source, authority and action visible.",
    )

    section_label(canvas, "Problem", 42, PAGE_H - 122)
    card(
        canvas,
        42,
        PAGE_H - 246,
        PAGE_W - 84,
        108,
        "The signal is buried in the record",
        "Longitudinal notes accumulate across consultations, calls and patient reports. "
        "High-risk context, recent changes, open work and contradictions are easy to miss. "
        "A generic AI summary may look concise while hiding provenance, review state or role boundaries.",
        accent=RED,
        fill=colors.HexColor("#FFF7F7"),
    )

    section_label(canvas, "Product principle", 42, PAGE_H - 275)
    principles = [
        ("WHAT MATTERS NOW", "Care Glance ranks deterministic clinical state."),
        ("WHERE IT CAME FROM", "Every highlight resolves to an exact source quote."),
        ("WHO VERIFIED IT", "Review, revision and action remain attributable."),
    ]
    gap = 10
    width = (PAGE_W - 84 - 2 * gap) / 3
    for index, (title, text) in enumerate(principles):
        card(
            canvas,
            42 + index * (width + gap),
            PAGE_H - 385,
            width,
            88,
            title,
            text,
            accent=(TEAL, BLUE, AMBER)[index],
            body_style=SMALL,
        )

    section_label(canvas, "Architecture", 42, PAGE_H - 418)
    canvas.setFillColor(PALE)
    canvas.setStrokeColor(LINE)
    canvas.roundRect(42, 86, PAGE_W - 84, 314, 10, stroke=1, fill=1)

    box_w = 91
    box_h = 58
    y_top = 292
    positions = [48, 158, 268, 378]
    items = [
        ("NEXT.JS UI", "Role-aware workspace", BLUE),
        ("FASTAPI", "Clinic-scoped RBAC", TEAL),
        ("POSTGRESQL", "Timeline + facts", NAVY),
        ("CARE GLANCE", "Rule-based read model", AMBER),
    ]
    for pos, item in zip(positions, items, strict=True):
        flow_box(canvas, pos, y_top, box_w, box_h, *item)
    for pos in positions[:-1]:
        arrow(canvas, pos + box_w + 3, y_top + box_h / 2, pos + box_w + 16, y_top + box_h / 2)

    flow_box(canvas, 142, 145, 120, 66, "PHI REDACTION", "Names, SG phones and ID-like values", RED)
    flow_box(canvas, 332, 145, 120, 66, "DEEPSEEK", "Replaceable JSON-mode provider", BLUE)
    arrow(canvas, 262, 178, 326, 178)
    canvas.setStrokeColor(colors.HexColor("#9CB2C0"))
    canvas.line(203, 211, 203, 247)
    canvas.line(203, 247, 203, y_top)
    canvas.line(392, 211, 392, 247)
    canvas.line(392, 247, 313, 247)

    paragraph(
        canvas,
        "<b>Boundary:</b> raw transcripts stay in the database. The provider receives only redacted text. "
        "Care Glance never invokes the LLM on read.",
        62,
        127,
        PAGE_W - 124,
        34,
        SMALL,
    )
    footer(canvas)


def page_two(canvas: Canvas) -> None:
    header(
        canvas,
        2,
        "Data model / Trust / AI pipeline / RBAC",
        "Evidence before inference",
        "The system separates source records, extracted facts, review state and action.",
    )

    section_label(canvas, "Data model", 42, PAGE_H - 122)
    card(
        canvas,
        42,
        PAGE_H - 388,
        245,
        246,
        "Longitudinal record",
        "<b>Clinic -> Patient -> ConsultSession -> Entry</b><br/><br/>"
        "Entry is the human-readable timeline unit. ClinicalFact carries structured value, risk, "
        "review status and an exact source span. Task and Conflict preserve actionable state. "
        "Highlight references one ClinicalFact. EntryVersion stores immutable full snapshots; "
        "revert appends a new version instead of erasing history.",
        accent=BLUE,
    )
    card(
        canvas,
        306,
        PAGE_H - 388,
        247,
        246,
        "Trust and provenance",
        "<b>Highlight -> ClinicalFact -> Entry -> ConsultSession</b><br/><br/>"
        "Every Glance item includes the exact source quote and occurrence time. AI suggestions remain "
        "suggested until a clinician accepts or rejects them. Audit events contain identifiers and "
        "state transitions - never full clinical text. Stale edits return 409 through optimistic concurrency.",
        accent=TEAL,
    )

    section_label(canvas, "AI pipeline", 42, PAGE_H - 421)
    pipeline_y = PAGE_H - 522
    steps = [
        ("1", "STORE", "raw locally"),
        ("2", "REDACT", "deterministic PHI"),
        ("3", "GENERATE", "DeepSeek JSON"),
        ("4", "VALIDATE", "schema + quote"),
        ("5", "COMMIT", "all-or-nothing"),
    ]
    step_w = 91
    for index, (number, title, detail) in enumerate(steps):
        x = 42 + index * 102
        canvas.setFillColor((BLUE, RED, TEAL, AMBER, NAVY)[index])
        canvas.circle(x + 10, pipeline_y + 34, 10, stroke=0, fill=1)
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.drawCentredString(x + 10, pipeline_y + 31, number)
        canvas.setFillColor(NAVY)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(x + 24, pipeline_y + 34, title)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 6.8)
        canvas.drawString(x + 24, pipeline_y + 22, detail)
        if index < len(steps) - 1:
            arrow(canvas, x + 88, pipeline_y + 34, x + 98, pipeline_y + 34)

    section_label(canvas, "Role-based access", 42, PAGE_H - 560)
    roles = [
        ("PATIENT", "Own scope; accepted Glance; AI-patient scribe", BLUE),
        ("STAFF", "Clinic timeline; staff notes; internal comments", TEAL),
        ("CLINICIAN", "Review, conflict resolution, clinician notes", AMBER),
        ("ADMIN", "Read-only in v1", NAVY),
    ]
    paragraph(
        canvas,
        "Cross-clinic resources return 404. UI hiding is not authorization. All 13 public Supabase tables use RLS with no client policy in v1: deny by default.",
        42,
        252,
        PAGE_W - 84,
        30,
        SMALL,
    )
    role_w = (PAGE_W - 84 - 3 * 8) / 4
    for index, (title, detail, color) in enumerate(roles):
        card(
            canvas,
            42 + index * (role_w + 8),
            72,
            role_w,
            130,
            title,
            detail,
            accent=color,
            body_style=SMALL,
        )
    footer(canvas)


def metric(canvas: Canvas, x: float, y: float, label: str, value: str, color) -> None:
    canvas.setFillColor(WHITE)
    canvas.setStrokeColor(LINE)
    canvas.roundRect(x, y, 113, 64, 7, stroke=1, fill=1)
    canvas.setFillColor(color)
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawCentredString(x + 56.5, y + 32, value)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica-Bold", 6.7)
    canvas.drawCentredString(x + 56.5, y + 15, label)


def page_three(canvas: Canvas) -> None:
    header(
        canvas,
        3,
        "Importance / Data decay / Performance / Trade-offs",
        "Bounded learning, deterministic risk",
        "Adapt ranking carefully; never let feedback rewrite clinical truth.",
    )

    section_label(canvas, "Importance and self-learning", 42, PAGE_H - 122)
    card(
        canvas,
        42,
        PAGE_H - 300,
        PAGE_W - 84,
        158,
        "Explainable score composition",
        "<b>final score = risk + recency + entity + open task + source authority + persistent critical + learning</b><br/><br/>"
        "The LLM never decides final ranking. A persistent critical allergy remains visible regardless of age. "
        "The clinician interface presents readable reasons, not raw scores.<br/><br/>"
        "<b>Learning bonus = clamp(accept_count x 0.25 - reject_count x 0.20, 0, 3)</b><br/>"
        "Feedback transfers only across similar entities inside the same clinic and never changes risk labels.",
        accent=TEAL,
        fill=PALE,
    )

    section_label(canvas, "Explainable data decay", 42, PAGE_H - 331)
    decay = [
        ("NEVER DECAY", "Allergies and clinician-confirmed critical facts", RED),
        ("FULL FIDELITY", "Recent facts plus persistent or medium/high-risk context", BLUE),
        ("CANDIDATE ONLY", "Old, low-risk, transient context; no deletion in v1", AMBER),
    ]
    gap = 10
    width = (PAGE_W - 84 - 2 * gap) / 3
    for index, (title, detail, color) in enumerate(decay):
        card(
            canvas,
            42 + index * (width + gap),
            PAGE_H - 440,
            width,
            88,
            title,
            detail,
            accent=color,
            body_style=SMALL,
        )

    section_label(canvas, "Performance evidence", 42, PAGE_H - 472)
    canvas.setFillColor(ICE)
    canvas.setStrokeColor(LINE)
    canvas.roundRect(42, 205, PAGE_W - 84, 130, 8, stroke=1, fill=1)
    metrics = [
        ("P50 LOCAL WARM PATH", "4.35 ms", BLUE),
        ("P95 LOCAL WARM PATH", "4.87 ms", TEAL),
        ("MAX", "5.23 ms", AMBER),
        ("TARGET", "<= 300 ms", NAVY),
    ]
    for index, item in enumerate(metrics):
        metric(canvas, 53 + index * 122, 248, *item)
    paragraph(
        canvas,
        "20 warmups + 200 measured requests using FastAPI TestClient, local SQLite and fixed synthetic data. This is a regression baseline, not a public-network Supabase SLA.",
        56,
        239,
        PAGE_W - 112,
        28,
        SMALL,
    )

    section_label(canvas, "Trade-offs", 42, 181)
    tradeoffs = (
        "<b>Prototype identity:</b> X-Demo-User-ID demonstrates server-side policy but is not production authentication. &nbsp;&nbsp; "
        "<b>Revision:</b> full snapshots favor simple, reliable diff and append-only revert. &nbsp;&nbsp; "
        "<b>Conflict scope:</b> v1 detects only same-medication, different-dose discrepancies. &nbsp;&nbsp; "
        "<b>RLS:</b> deny-by-default supports a backend-only boundary; client policies require a separate design. &nbsp;&nbsp; "
        "<b>Scope:</b> no voice capture, real patient data or automated treatment advice."
    )
    card(
        canvas,
        42,
        62,
        PAGE_W - 84,
        100,
        "Purposeful constraints for a 72-hour build",
        tradeoffs,
        accent=NAVY,
        body_style=SMALL,
    )
    footer(canvas)


def build() -> Path:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(str(OUTPUT), pagesize=A4, pageCompression=1)
    canvas.setTitle("Nightingale Care Note - Technical Brief")
    canvas.setAuthor("Nightingale 72HR Build")
    page_one(canvas)
    canvas.showPage()
    page_two(canvas)
    canvas.showPage()
    page_three(canvas)
    canvas.save()
    return OUTPUT


if __name__ == "__main__":
    print(build())
