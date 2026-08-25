from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.models.audit import Comment
from app.models.base import Base
from app.models.clinical import Conflict, ConflictStatus, Task, TaskStatus
from app.models.timeline import ConsultSession, Entry, EntryType
from app.seed.sarah_lim import seed_sarah_lim


def test_sarah_story_covers_the_frozen_longitudinal_demo() -> None:
    """Catches seed drift between the demo, UI, and automated tests."""
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        story = seed_sarah_lim(session)

        entries = session.scalars(
            select(Entry).where(Entry.patient_id == story.patient.id).order_by(Entry.created_at)
        ).all()
        sessions = session.scalars(
            select(ConsultSession).where(ConsultSession.patient_id == story.patient.id)
        ).all()
        open_tasks = session.scalars(
            select(Task).where(
                Task.patient_id == story.patient.id,
                Task.status == TaskStatus.OPEN,
            )
        ).all()
        conflicts = session.scalars(
            select(Conflict).where(
                Conflict.patient_id == story.patient.id,
                Conflict.status == ConflictStatus.DETECTED,
            )
        ).all()
        comments = session.scalars(select(Comment)).all()

        assert story.patient.display_name == "Sarah Lim"
        assert {entry.created_at.month for entry in entries} == {4, 7, 8}
        assert {entry.entry_type for entry in entries} >= {
            EntryType.CLINICIAN_NOTE,
            EntryType.STAFF_NOTE,
            EntryType.AI_PATIENT_SESSION_SUMMARY,
            EntryType.AI_DOCTOR_CONSULT_SUMMARY,
        }
        assert any("Penicillin" in entry.content for entry in entries)
        assert any("Atorvastatin 20 mg" in entry.content for entry in entries)
        assert any("no chest" in entry.content.lower() for entry in entries)
        assert any("worsening chest pressure" in entry.content.lower() for entry in entries)
        assert len(sessions) == 2
        assert len(open_tasks) == 1
        assert len(conflicts) == 1
        assert len(comments) >= 1


def test_august_doctor_consult_keeps_phi_local_and_redacts_llm_text() -> None:
    """Catches the canonical demo transcript bypassing the PHI-before-LLM boundary."""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        story = seed_sarah_lim(session)
        doctor_session = story.august_doctor_session

        assert "Sarah Lim" in doctor_session.raw_transcript
        assert "91234567" in doctor_session.raw_transcript
        assert "S1234567A" in doctor_session.raw_transcript
        assert "Sarah Lim" not in doctor_session.redacted_transcript
        assert "91234567" not in doctor_session.redacted_transcript
        assert "S1234567A" not in doctor_session.redacted_transcript
        assert "[PATIENT_NAME]" in doctor_session.redacted_transcript
        assert "[PHONE]" in doctor_session.redacted_transcript
        assert "[ID]" in doctor_session.redacted_transcript
