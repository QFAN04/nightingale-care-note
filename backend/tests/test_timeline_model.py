from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.base import Base
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


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as database_session:
        yield database_session


def make_patient_and_clinician() -> tuple[Patient, User]:
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
    return patient, clinician


def test_ai_summary_preserves_source_session_provenance(session: Session) -> None:
    """Catches an AI summary that cannot be traced to its source transcript."""
    patient, clinician = make_patient_and_clinician()
    occurred_at = datetime(2026, 8, 25, 9, 30, tzinfo=timezone.utc)
    consult = ConsultSession(
        patient=patient,
        interaction_type=InteractionType.DOCTOR_PATIENT,
        occurred_at=occurred_at,
        raw_transcript="Patient reports chest pressure.",
        redacted_transcript="Patient reports chest pressure.",
        created_by=clinician,
        processing_status=ProcessingStatus.COMPLETED,
    )
    entry = Entry(
        patient=patient,
        author=clinician,
        author_role=AuthorRole.SYSTEM,
        entry_type=EntryType.AI_DOCTOR_CONSULT_SUMMARY,
        content="Chest pressure discussed during consultation.",
        provenance_type=ProvenanceType.CONSULT_SESSION,
        consult_session=consult,
    )
    session.add(entry)
    session.commit()

    assert entry.provenance_id == consult.id
    assert entry.consult_session.raw_transcript == "Patient reports chest pressure."
    assert entry.patient_id == patient.id
    stored_occurred_at = consult.occurred_at.replace(tzinfo=timezone.utc)
    assert stored_occurred_at == occurred_at


def test_manual_entry_preserves_human_author(session: Session) -> None:
    """Catches a manual clinical record losing who authored it."""
    patient, clinician = make_patient_and_clinician()
    entry = Entry(
        patient=patient,
        author=clinician,
        author_role=AuthorRole.CLINICIAN,
        entry_type=EntryType.CLINICIAN_NOTE,
        content="Penicillin allergy confirmed.",
        provenance_type=ProvenanceType.MANUAL,
    )
    session.add(entry)
    session.commit()

    assert entry.author_id == clinician.id
    assert entry.provenance_id is None
    assert entry.current_version == 1


def test_entry_version_must_be_positive(session: Session) -> None:
    """Catches invalid optimistic-concurrency state entering the timeline."""
    patient, clinician = make_patient_and_clinician()
    session.add(
        Entry(
            patient=patient,
            author=clinician,
            author_role=AuthorRole.CLINICIAN,
            entry_type=EntryType.CLINICIAN_NOTE,
            content="Invalid version should be rejected.",
            current_version=0,
            provenance_type=ProvenanceType.MANUAL,
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()
