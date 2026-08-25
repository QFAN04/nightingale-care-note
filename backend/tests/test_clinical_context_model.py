from datetime import date, datetime, timezone

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.clinical import (
    ClinicalFact,
    Conflict,
    ConflictStatus,
    ConflictType,
    FactType,
    Highlight,
    HighlightCategory,
    HighlightStatus,
    PersistenceType,
    ReviewStatus,
    RiskLevel,
    Task,
    TaskPriority,
    TaskStatus,
)
from app.models.identity import Clinic, Patient, User, UserRole
from app.models.timeline import (
    AuthorRole,
    ConsultSession,
    Entry,
    EntryType,
    InteractionType,
    ProcessingStatus,
    ProvenanceType,
)


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return Session(engine)


def make_source() -> tuple[Patient, User, ConsultSession, Entry]:
    clinic = Clinic(name="Nightingale Central Clinic")
    patient = Patient(
        clinic=clinic,
        external_ref="PAT-001",
        display_name="Sarah Lim",
        date_of_birth=date(1984, 5, 18),
        sex="female",
    )
    clinician = User(
        clinic=clinic,
        display_name="Dr Priya Nair",
        role=UserRole.CLINICIAN,
    )
    consult = ConsultSession(
        patient=patient,
        interaction_type=InteractionType.DOCTOR_PATIENT,
        occurred_at=datetime(2026, 8, 25, 9, 30, tzinfo=timezone.utc),
        raw_transcript="Patient: Last night the chest pressure felt stronger than before.",
        redacted_transcript="Patient: Last night the chest pressure felt stronger than before.",
        created_by=clinician,
        processing_status=ProcessingStatus.COMPLETED,
    )
    entry = Entry(
        patient=patient,
        author_role=AuthorRole.SYSTEM,
        entry_type=EntryType.AI_DOCTOR_CONSULT_SUMMARY,
        content="Chest pressure has worsened since last night.",
        provenance_type=ProvenanceType.CONSULT_SESSION,
        consult_session=consult,
    )
    return patient, clinician, consult, entry


def test_highlight_resolves_exact_source_chain() -> None:
    """Catches a Glance item that cannot prove where its claim came from."""
    with make_session() as session:
        patient, _clinician, consult, entry = make_source()
        fact = ClinicalFact(
            patient=patient,
            entry=entry,
            fact_type=FactType.SYMPTOM,
            entity_name="chest pressure",
            value_text="worsening",
            risk_level=RiskLevel.HIGH,
            persistence_type=PersistenceType.TRANSIENT,
            source_quote="Last night the chest pressure felt stronger than before.",
            source_start=9,
            source_end=66,
            extraction_confidence=0.92,
        )
        highlight = Highlight(
            patient=patient,
            clinical_fact=fact,
            text="Worsening chest pressure",
            category=HighlightCategory.RECENT_CHANGE,
            risk_level=RiskLevel.HIGH,
            risk_reason="High-risk symptom · recorded today",
            base_score=12,
            learned_score=0,
            status=HighlightStatus.SUGGESTED,
        )
        session.add(highlight)
        session.commit()

        assert highlight.clinical_fact.source_quote in consult.raw_transcript
        assert highlight.clinical_fact.entry.consult_session.id == consult.id
        assert highlight.clinical_fact.entry_id == entry.id


def test_fact_review_and_highlight_review_are_independent() -> None:
    """Catches fact truth review being confused with Glance prioritization review."""
    with make_session() as session:
        patient, clinician, _consult, entry = make_source()
        fact = ClinicalFact(
            patient=patient,
            entry=entry,
            fact_type=FactType.SYMPTOM,
            entity_name="chest pressure",
            value_text="worsening",
            risk_level=RiskLevel.HIGH,
            persistence_type=PersistenceType.TRANSIENT,
            source_quote="Last night the chest pressure felt stronger than before.",
            extraction_confidence=0.92,
            review_status=ReviewStatus.CONFIRMED,
            reviewed_by=clinician,
        )
        highlight = Highlight(
            patient=patient,
            clinical_fact=fact,
            text="Worsening chest pressure",
            category=HighlightCategory.RECENT_CHANGE,
            risk_level=RiskLevel.HIGH,
            risk_reason="High-risk symptom · recorded today",
            base_score=12,
            learned_score=0,
            status=HighlightStatus.SUGGESTED,
        )
        session.add(highlight)
        session.commit()

        assert fact.review_status is ReviewStatus.CONFIRMED
        assert fact.reviewed_by_id == clinician.id
        assert highlight.status is HighlightStatus.SUGGESTED


def test_open_task_and_detected_conflict_keep_structured_sources() -> None:
    """Catches actionable context losing the evidence used by Glance."""
    with make_session() as session:
        patient, clinician, _consult, entry = make_source()
        dose_10 = ClinicalFact(
            patient=patient,
            entry=entry,
            fact_type=FactType.MEDICATION,
            entity_name="atorvastatin",
            value_text="10 mg",
            risk_level=RiskLevel.MEDIUM,
            persistence_type=PersistenceType.PERSISTENT,
            source_quote="Atorvastatin 10 mg",
            extraction_confidence=0.9,
        )
        dose_20 = ClinicalFact(
            patient=patient,
            entry=entry,
            fact_type=FactType.MEDICATION,
            entity_name="atorvastatin",
            value_text="20 mg",
            risk_level=RiskLevel.MEDIUM,
            persistence_type=PersistenceType.PERSISTENT,
            source_quote="Atorvastatin 20 mg",
            extraction_confidence=1.0,
            review_status=ReviewStatus.CONFIRMED,
            reviewed_by=clinician,
        )
        task = Task(
            patient=patient,
            source_entry=entry,
            source_fact=dose_10,
            description="Clinician to reconcile atorvastatin dose",
            priority=TaskPriority.HIGH,
            status=TaskStatus.OPEN,
            assigned_role=UserRole.CLINICIAN,
        )
        conflict = Conflict(
            patient=patient,
            conflict_type=ConflictType.MEDICATION_DOSE,
            entity_name="atorvastatin",
            conflicting_fact=dose_10,
            authoritative_fact=dose_20,
            description="Patient reported 10 mg; clinician record states 20 mg.",
            status=ConflictStatus.DETECTED,
        )
        session.add_all([task, conflict])
        session.commit()

        assert task.source_fact_id == dose_10.id
        assert task.status is TaskStatus.OPEN
        assert conflict.conflicting_fact_id == dose_10.id
        assert conflict.authoritative_fact_id == dose_20.id
