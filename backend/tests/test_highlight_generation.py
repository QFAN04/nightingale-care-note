from datetime import date, datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.glance.generation import generate_highlight_suggestions
from app.models.base import Base
from app.models.clinical import (
    ClinicalFact,
    Conflict,
    ConflictStatus,
    ConflictType,
    FactType,
    HighlightCategory,
    PersistenceType,
    RiskLevel,
    Task,
    TaskPriority,
    TaskStatus,
)
from app.models.identity import Clinic, Patient, User, UserRole
from app.models.timeline import AuthorRole, Entry, EntryType, ProvenanceType


NOW = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)


def make_context() -> tuple[Session, Patient, Entry, User]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    clinic = Clinic(name="Nightingale Test Clinic")
    patient = Patient(
        clinic=clinic,
        external_ref="TEST-HIGHLIGHT",
        display_name="Test Patient",
        date_of_birth=date(1980, 1, 1),
        sex="female",
    )
    clinician = User(
        clinic=clinic,
        display_name="Dr Test",
        role=UserRole.CLINICIAN,
    )
    ai_entry = Entry(
        patient=patient,
        author_role=AuthorRole.SYSTEM,
        entry_type=EntryType.AI_PATIENT_SESSION_SUMMARY,
        content="Synthetic AI entry",
        provenance_type=ProvenanceType.SYSTEM,
        created_at=NOW - timedelta(hours=12),
        updated_at=NOW - timedelta(hours=12),
    )
    db.add_all([clinic, patient, clinician, ai_entry])
    db.commit()
    return db, patient, ai_entry, clinician


def make_fact(
    patient: Patient,
    entry: Entry,
    *,
    entity: str,
    fact_type: FactType,
    risk: RiskLevel,
    created_at: datetime,
    persistence: PersistenceType = PersistenceType.TRANSIENT,
) -> ClinicalFact:
    return ClinicalFact(
        patient=patient,
        entry=entry,
        fact_type=fact_type,
        entity_name=entity,
        value_text="present",
        risk_level=risk,
        persistence_type=persistence,
        source_quote=f"{entity} present",
        extraction_confidence=0.9,
        created_at=created_at,
    )


def test_recent_high_risk_fact_generates_suggestion_but_old_low_risk_does_not() -> None:
    db, patient, entry, _clinician = make_context()
    high = make_fact(
        patient,
        entry,
        entity="chest pressure",
        fact_type=FactType.SYMPTOM,
        risk=RiskLevel.HIGH,
        created_at=NOW - timedelta(hours=12),
    )
    low = make_fact(
        patient,
        entry,
        entity="mild dizziness",
        fact_type=FactType.SYMPTOM,
        risk=RiskLevel.LOW,
        created_at=NOW - timedelta(days=90),
    )
    db.add_all([high, low])
    db.commit()

    generated = generate_highlight_suggestions(db, patient.id, now=NOW)

    assert [(item.clinical_fact_id, item.category) for item in generated] == [
        (high.id, HighlightCategory.RECENT_CHANGE)
    ]
    assert generated[0].status.value == "suggested"
    assert "high clinical risk" in generated[0].risk_reason
    db.close()


def test_open_task_and_detected_conflict_generate_actionable_categories() -> None:
    db, patient, entry, clinician = make_context()
    symptom = make_fact(
        patient,
        entry,
        entity="chest pressure",
        fact_type=FactType.SYMPTOM,
        risk=RiskLevel.HIGH,
        created_at=NOW - timedelta(hours=12),
    )
    reported_dose = make_fact(
        patient,
        entry,
        entity="atorvastatin",
        fact_type=FactType.MEDICATION,
        risk=RiskLevel.MEDIUM,
        created_at=NOW - timedelta(hours=12),
        persistence=PersistenceType.PERSISTENT,
    )
    clinician_entry = Entry(
        patient=patient,
        author=clinician,
        author_role=AuthorRole.CLINICIAN,
        entry_type=EntryType.CLINICIAN_NOTE,
        content="Atorvastatin 20 mg",
        provenance_type=ProvenanceType.MANUAL,
        created_at=NOW - timedelta(days=30),
        updated_at=NOW - timedelta(days=30),
    )
    confirmed_dose = make_fact(
        patient,
        clinician_entry,
        entity="atorvastatin",
        fact_type=FactType.MEDICATION,
        risk=RiskLevel.MEDIUM,
        created_at=NOW - timedelta(days=30),
        persistence=PersistenceType.PERSISTENT,
    )
    task = Task(
        patient=patient,
        source_entry=entry,
        source_fact=symptom,
        description="Clinician review required",
        priority=TaskPriority.HIGH,
        status=TaskStatus.OPEN,
        assigned_role=UserRole.CLINICIAN,
        created_at=NOW - timedelta(hours=6),
    )
    conflict = Conflict(
        patient=patient,
        conflict_type=ConflictType.MEDICATION_DOSE,
        entity_name="atorvastatin",
        conflicting_fact=reported_dose,
        authoritative_fact=confirmed_dose,
        description="Patient reported 10 mg; clinician record states 20 mg.",
        status=ConflictStatus.DETECTED,
        created_at=NOW - timedelta(hours=6),
    )
    db.add_all([symptom, reported_dose, clinician_entry, confirmed_dose, task, conflict])
    db.commit()

    generated = generate_highlight_suggestions(db, patient.id, now=NOW)
    categories = {item.category for item in generated}

    assert HighlightCategory.OPEN_ACTION in categories
    assert HighlightCategory.CONFLICT in categories
    assert any(item.text == conflict.description for item in generated)
    db.close()


def test_generation_is_idempotent_for_existing_fact_category() -> None:
    db, patient, entry, _clinician = make_context()
    fact = make_fact(
        patient,
        entry,
        entity="chest pressure",
        fact_type=FactType.SYMPTOM,
        risk=RiskLevel.HIGH,
        created_at=NOW,
    )
    db.add(fact)
    db.commit()

    first = generate_highlight_suggestions(db, patient.id, now=NOW)
    second = generate_highlight_suggestions(db, patient.id, now=NOW)

    assert len(first) == 1
    assert second == []
    db.close()
