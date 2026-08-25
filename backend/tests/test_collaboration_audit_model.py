from datetime import date

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import Session

from app.models.audit import (
    AuditEvent,
    ChangeReason,
    Comment,
    EntryVersion,
    FeedbackAction,
    ImportanceFeedback,
)
from app.models.base import Base
from app.models.identity import Clinic, Patient, User, UserRole
from app.models.timeline import AuthorRole, Entry, EntryType, ProvenanceType


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return Session(engine)


def make_entry() -> tuple[Clinic, Patient, User, Entry]:
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
    entry = Entry(
        patient=patient,
        author=clinician,
        author_role=AuthorRole.CLINICIAN,
        entry_type=EntryType.CLINICIAN_NOTE,
        content="Atorvastatin 20 mg confirmed.",
        provenance_type=ProvenanceType.MANUAL,
    )
    return clinic, patient, clinician, entry


def test_entry_versions_store_complete_append_only_snapshots() -> None:
    """Catches revision history that stores only diffs or loses its parent version."""
    with make_session() as session:
        _clinic, _patient, clinician, entry = make_entry()
        version_1 = EntryVersion(
            entry=entry,
            version_number=1,
            content="Atorvastatin 20 mg confirmed.",
            changed_by=clinician,
            change_reason=ChangeReason.CREATED,
            source_version=None,
            content_hash="a" * 64,
        )
        version_2 = EntryVersion(
            entry=entry,
            version_number=2,
            content="Atorvastatin 20 mg confirmed; review in four weeks.",
            changed_by=clinician,
            change_reason=ChangeReason.MANUAL_EDIT,
            source_version=1,
            content_hash="b" * 64,
        )
        session.add_all([version_1, version_2])
        session.commit()

        assert version_1.content == "Atorvastatin 20 mg confirmed."
        assert version_2.content.startswith("Atorvastatin 20 mg confirmed")
        assert version_2.source_version == version_1.version_number


def test_comments_support_threading_and_resolution() -> None:
    """Catches collaboration records that cannot preserve a reply thread."""
    with make_session() as session:
        _clinic, _patient, clinician, entry = make_entry()
        root = Comment(
            entry=entry,
            author=clinician,
            content="@clinician please verify the medication dose.",
        )
        reply = Comment(
            entry=entry,
            author=clinician,
            parent_comment=root,
            content="Verified against the April clinician note.",
            resolved=True,
            resolved_by=clinician,
        )
        session.add(reply)
        session.commit()

        assert reply.parent_comment_id == root.id
        assert reply.resolved is True
        assert reply.resolved_by_id == clinician.id


def test_learning_feedback_is_a_bounded_ranking_signal() -> None:
    """Catches adaptive feedback being stored as a clinical-risk mutation."""
    with make_session() as session:
        _clinic, patient, clinician, _entry = make_entry()
        feedback = ImportanceFeedback(
            patient=patient,
            actor=clinician,
            entity_key="symptom:chest pressure",
            action=FeedbackAction.ACCEPT,
            ranking_delta=0.25,
        )
        session.add(feedback)
        session.commit()

        assert feedback.ranking_delta == 0.25
        assert "risk_level" not in inspect(ImportanceFeedback).columns


def test_audit_event_stores_metadata_not_clinical_text() -> None:
    """Catches audit logging accidentally duplicating sensitive note content."""
    with make_session() as session:
        clinic, patient, clinician, entry = make_entry()
        session.add(entry)
        session.flush()
        event_record = AuditEvent(
            clinic=clinic,
            patient=patient,
            actor=clinician,
            action="entry.updated",
            resource_type="entry",
            resource_id=entry.id,
            event_metadata={"from_version": 1, "to_version": 2},
        )
        session.add(event_record)
        session.commit()

        columns = {column.key for column in inspect(AuditEvent).columns}
        assert event_record.event_metadata == {"from_version": 1, "to_version": 2}
        assert "content" not in columns
        assert "raw_transcript" not in columns
